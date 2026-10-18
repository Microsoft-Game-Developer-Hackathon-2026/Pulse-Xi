import copy
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.simulator import generate
from app.storage import connect, imported_match
from app.data_hub import quality
from app.database_backup import copy_database

TOKEN='lifecycle-test-token-at-least-32-characters'
HEADERS={'Authorization':f'Bearer {TOKEN}'}
client=TestClient(app,base_url='http://127.0.0.1',client=('127.0.0.1',50000))


@pytest.fixture
def dataset(tmp_path,monkeypatch):
    monkeypatch.setenv('PULSE_DB_PATH',str(tmp_path/'library.sqlite'))
    monkeypatch.setenv('PULSE_IMPORT_TOKEN',TOKEN)
    monkeypatch.setenv('PULSE_ENABLE_LOCAL_DATA_ADMIN','1')
    match,events=generate('comeback')
    match=match.model_copy(update={'match_id':'lifecycle-match'})
    events=[e.model_copy(update={'match_id':match.match_id}) for e in events[:15]]
    package={'schema_version':'pulse-xi-match-package/1','match':match.model_dump(mode='json'),
             'events':[e.model_dump(mode='json',by_alias=True) for e in events], 'provenance':{'source':'original synthetic research'}}
    assert client.post('/api/data-hub/import',json=package,headers=HEADERS).status_code==200
    return package


def entry():
    return next(m for m in client.get('/api/data-hub').json()['matches'] if m['match']['match_id']=='lifecycle-match')


def action(kind, current=None):
    item=current or entry()
    return {'action':kind,'confirm_match_id':item['match']['match_id'],
            'generation':item['lifecycle']['generation'],'revision':item['lifecycle']['revision']}


def mutate(body,mid='lifecycle-match',headers=None):
    return client.post(f'/api/data-hub/matches/{mid}/lifecycle',json=body,headers=HEADERS if headers is None else headers)


def test_archive_restore_keeps_source_and_revisions(dataset):
    before=imported_match('lifecycle-match')
    stale=action('delete')
    assert mutate(action('archive')).json()['status']=='archived'
    assert entry()['lifecycle']['archived']
    assert all(m['match_id']!='lifecycle-match' for m in client.get('/api/matches').json())
    assert client.get('/api/matches/lifecycle-match/events').json()==dataset['events']
    assert imported_match('lifecycle-match')==before
    assert client.post('/api/data-hub/import',json=dataset,headers=HEADERS).json()['inserted']==0
    assert entry()['lifecycle']['archived']
    assert mutate(stale).status_code==409
    assert mutate(action('restore')).json()['status']=='active'
    assert not entry()['lifecycle']['archived']
    assert any(m['match_id']=='lifecycle-match' for m in client.get('/api/matches').json())
    assert client.get('/api/matches/lifecycle-match/package').json()['provenance']['source']=='original synthetic research'


def test_delete_recovery_checksum_and_incarnation_guard(dataset):
    old=action('delete')
    package=client.get('/api/matches/lifecycle-match/package').json()
    assert package['integrity']['algorithm']=='sha256'
    deleted=mutate(old)
    assert deleted.status_code==200
    assert imported_match('lifecycle-match') is None
    assert client.get('/api/matches/lifecycle-match').status_code==404
    assert client.post('/api/data-hub/import',json=dataset,headers=HEADERS).status_code==409
    assert client.post('/api/matches/ingest',json={k:dataset[k] for k in ('match','events')},headers=HEADERS).status_code==409
    preview=client.post('/api/data-hub/preview',json=package,headers=HEADERS).json()
    assert preview['status']=='deleted'
    broken=copy.deepcopy(package);broken['events'][1]['outcome']='tampered'
    assert client.post('/api/data-hub/recover',json=broken,headers={**HEADERS,'X-Pulse-Deletion-ID':preview['deletion_id']}).status_code==422
    assert imported_match('lifecycle-match') is None
    restored=client.post('/api/data-hub/recover',json=package,headers={**HEADERS,'X-Pulse-Deletion-ID':preview['deletion_id']})
    assert restored.status_code==200,restored.text
    assert client.get('/api/matches/lifecycle-match/events').json()==dataset['events']
    assert mutate(old).status_code==409
    second=mutate(action('delete')).json()
    assert second['deletion_id']!=preview['deletion_id']
    assert client.post('/api/data-hub/recover',json=package,headers={**HEADERS,'X-Pulse-Deletion-ID':preview['deletion_id']}).status_code==409
    with connect() as db:
        for table in ('matches','events','package_metadata','match_lifecycle'):
            assert db.execute(f'SELECT COUNT(*) FROM {table} WHERE match_id=?',('lifecycle-match',)).fetchone()[0]==0
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


@pytest.mark.parametrize('failure',['no-token','wrong-token','disabled','remote','forwarded','public-host'])
def test_admin_fail_closed(dataset,monkeypatch,failure):
    body=action('archive');headers=HEADERS.copy();target=client
    if failure=='no-token':headers={}
    if failure=='wrong-token':headers={'Authorization':'Bearer wrong'}
    if failure=='disabled':monkeypatch.delenv('PULSE_ENABLE_LOCAL_DATA_ADMIN')
    if failure=='remote':target=TestClient(app,base_url='http://127.0.0.1',client=('203.0.113.8',50000))
    if failure=='forwarded':headers['X-Forwarded-For']='127.0.0.1'
    if failure=='public-host':headers['Host']='public.example'
    response=target.post('/api/data-hub/matches/lifecycle-match/lifecycle',json=body,headers=headers)
    assert response.status_code==403
    assert not entry()['lifecycle']['archived']


def test_wrong_confirmation_unknown_and_fixture_protection(dataset):
    body=action('delete');body['confirm_match_id']='other'
    assert mutate(body).status_code==422
    for mid in ('unknown','comeback-1107','custom-99'):
        body=action('delete');body['confirm_match_id']=mid
        assert mutate(body,mid).status_code==404
    assert imported_match('lifecycle-match') is not None


def test_interrupted_delete_rolls_back_all_children(dataset):
    body=action('delete')
    with connect() as db:
        db.execute("CREATE TRIGGER interrupt BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'test interruption'); END")
    with pytest.raises(sqlite3.IntegrityError,match='test interruption'):
        mutate(body)
    assert imported_match('lifecycle-match') is not None
    assert entry()['provenance']['source']=='original synthetic research'
    with connect() as db:
        assert not db.execute('SELECT 1 FROM deleted_matches').fetchone()
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_concurrent_import_cannot_resurrect_deleted_source(dataset):
    body=action('delete');barrier=Barrier(2)
    def deleting():barrier.wait();return mutate(body)
    def importing():barrier.wait();return client.post('/api/data-hub/import',json=dataset,headers=HEADERS)
    with ThreadPoolExecutor(max_workers=2) as pool:
        delete=pool.submit(deleting);incoming=pool.submit(importing)
        assert delete.result().status_code==200
        assert incoming.result().status_code in (200,409)
    assert imported_match('lifecycle-match') is None


def test_backup_restore_new_database_integrity_and_no_overwrite(dataset,tmp_path,monkeypatch):
    source=tmp_path/'library.sqlite';backup=tmp_path/'backup.sqlite';recovered=tmp_path/'recovered.sqlite'
    mutate(action('archive'))
    stale_confirmation=action('delete')
    report=copy_database(source,backup)
    assert report['matches']==1 and report['events']==15
    with pytest.raises(FileExistsError):copy_database(source,backup)
    with pytest.raises(ValueError,match='checksum'):copy_database(backup,recovered,'0'*64)
    assert not recovered.exists()
    copy_database(backup,recovered,report['sha256'])
    monkeypatch.setenv('PULSE_DB_PATH',str(recovered))
    assert entry()['lifecycle']['archived']
    assert client.get('/api/matches/lifecycle-match/events').json()==dataset['events']
    assert entry()['provenance']['source']=='original synthetic research'
    assert mutate(stale_confirmation).status_code==409
    damaged=tmp_path/'bad.sqlite';damaged.write_bytes(b'not sqlite')
    with pytest.raises(sqlite3.DatabaseError):copy_database(damaged,tmp_path/'bad-restored.sqlite')
    assert not (tmp_path/'bad-restored.sqlite').exists()


def test_sql_quality_aggregates_equal_existing_calculations(dataset):
    match,events=imported_match('lifecycle-match')
    assert entry()['quality']==quality(match,events)
    with connect() as db:
        db.execute('DELETE FROM events WHERE match_id=?',('lifecycle-match',))
    assert entry()['quality']==quality(match,[])


def test_library_does_not_deserialize_event_payloads(dataset,monkeypatch):
    from app.models import MatchEvent
    def unexpected(*args,**kwargs):
        raise AssertionError('library must aggregate without loading all event models')
    monkeypatch.setattr(MatchEvent,'model_validate_json',unexpected)
    assert entry()['quality']['event_count']==len(dataset['events'])


def test_v1_migration_preserves_payload_and_initializes_lifecycle(tmp_path,monkeypatch):
    path=tmp_path/'v1.sqlite';monkeypatch.setenv('PULSE_DB_PATH',str(path))
    match,events=generate('comeback');match=match.model_copy(update={'match_id':'old-import'})
    event=events[0].model_copy(update={'match_id':match.match_id})
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE matches(match_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        db.execute('CREATE TABLE events(match_id TEXT REFERENCES matches(match_id),event_id TEXT,sequence INTEGER,match_second INTEGER,payload TEXT,PRIMARY KEY(match_id,event_id),UNIQUE(match_id,sequence))')
        db.execute('INSERT INTO matches VALUES (?,?)',(match.match_id,match.model_dump_json()))
        db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(match.match_id,event.event_id,event.sequence,event.match_second,event.model_dump_json(by_alias=True)))
        db.execute('PRAGMA user_version=1')
    with connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==2
        assert db.execute('SELECT payload FROM events').fetchone()[0]==event.model_dump_json(by_alias=True)
        assert db.execute('SELECT revision,archived FROM match_lifecycle').fetchone()==(1,0)
    assert imported_match('old-import')==(match,[event])


def test_real_cli_backup_and_restore_in_new_process(dataset,tmp_path):
    command=Path(__file__).resolve().parents[2]/'scripts'/'database-admin.py'
    backup=tmp_path/'cli-backup.sqlite';recovered=tmp_path/'cli-recovered.sqlite'
    result=subprocess.run([sys.executable,str(command),'backup','--destination',str(backup)],capture_output=True,text=True,check=True)
    report=json.loads(result.stdout)
    restore=subprocess.run([sys.executable,str(command),'restore','--source',str(backup),'--destination',str(recovered),'--sha256',report['sha256']],capture_output=True,text=True,check=True)
    assert json.loads(restore.stdout)['events']==len(dataset['events'])
    denied=subprocess.run([sys.executable,str(command),'restore','--source',str(backup),'--destination',str(recovered),'--sha256',report['sha256']],capture_output=True,text=True)
    assert denied.returncode!=0
    with sqlite3.connect(recovered) as db:
        assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]


def test_v2_requires_checksum_and_accepts_unchanged_roundtrip(dataset):
    package=client.get('/api/matches/lifecycle-match/package').json()
    assert package['schema_version']=='pulse-xi-match-package/2'
    assert client.post('/api/data-hub/preview',json=package,headers=HEADERS).status_code==200
    package.pop('integrity')
    assert client.post('/api/data-hub/preview',json=package,headers=HEADERS).status_code==422
    package['schema_version']='pulse-xi-match-package/1'
    assert client.post('/api/data-hub/preview',json=package,headers=HEADERS).status_code==200


def test_backup_cli_refuses_ambiguous_relative_server_path(tmp_path,monkeypatch):
    monkeypatch.setenv('PULSE_DB_PATH','relative.sqlite')
    command=Path(__file__).resolve().parents[2]/'scripts'/'database-admin.py'
    target=tmp_path/'wrong-backup.sqlite'
    result=subprocess.run([sys.executable,str(command),'backup','--destination',str(target)],capture_output=True,text=True)
    assert result.returncode!=0 and 'ambiguous' in result.stderr
    assert not target.exists()


def test_recovery_preserves_entire_existing_body_size_budget(dataset):
    source=client.get('/api/matches/lifecycle-match/package').content
    deleted=mutate(action('delete')).json()
    # Whitespace is valid JSON and keeps the same checksum. The deletion ID is
    # a header, so recovery has no JSON wrapper overhead at the 2 MB boundary.
    raw=source+b' '*(2_000_000-len(source))
    result=client.post('/api/data-hub/recover',content=raw,headers={**HEADERS,'Content-Type':'application/json','X-Pulse-Deletion-ID':deleted['deletion_id']})
    assert result.status_code==200,result.text
    assert client.get('/api/matches/lifecycle-match/events').json()==dataset['events']


def test_local_windows_loop_factory_uses_selector(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from app import local_event_loop
    monkeypatch.setattr(local_event_loop,'sys',SimpleNamespace(platform='win32'))
    loop=local_event_loop.create_loop()
    try:
        assert isinstance(loop,asyncio.SelectorEventLoop)
    finally:
        loop.close()
