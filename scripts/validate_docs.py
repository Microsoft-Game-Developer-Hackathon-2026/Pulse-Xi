"""Check local Markdown links, referenced repository paths and typed API examples."""
from __future__ import annotations

import json
import re
import sys
from typing import get_type_hints
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)]+)\)')
HEADING = re.compile(r'^#{1,6}\s+(.+?)\s*#*\s*$')
CODE_SPAN = re.compile(r'`([^`]+)`')
REPO_PATH = re.compile(r'^(?:README\.md|(?:backend|frontend|docs|scripts|assets|licenses|data|\.github)/)[^\s`]*')
# Paths that are intentionally created by the application and therefore absent
# from a clean source checkout.
RUNTIME_PATHS = {'backend/data/pulse_xi.sqlite', 'frontend/dist'}
IGNORED_DIRECTORY_NAMES = {
    '.git', '.pytest_cache', '.venv', '.venv-audit', '.codex-progress',
    'node_modules', 'test-results', 'playwright-report', 'coverage', 'htmlcov',
}


def anchor_slug(heading: str) -> str:
    value = re.sub(r'[`*_~]', '', heading).lower()
    value = re.sub(r'[^\w\- ]', '', value, flags=re.UNICODE)
    return re.sub(r'\s+', '-', value.strip())


def anchors(text: str) -> set[str]:
    result: set[str] = set()
    counts: dict[str, int] = {}
    for line in text.splitlines():
        match = HEADING.match(line)
        if not match:
            continue
        base = anchor_slug(match.group(1))
        count = counts.get(base, 0)
        counts[base] = count + 1
        result.add(base if count == 0 else f'{base}-{count}')
    return result


def contains_credential(value: object) -> bool:
    if isinstance(value, dict):
        return any(re.search(r'(?:token|password|secret|credential)', str(key), re.I)
                   or contains_credential(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_credential(item) for item in value)
    return False


def validate_markdown(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    markdown_files = sorted(root.rglob('*.md'))
    markdown_files = [p for p in markdown_files
                      if not IGNORED_DIRECTORY_NAMES.intersection(p.relative_to(root).parts)]
    for path in markdown_files:
        text = path.read_text(encoding='utf-8-sig')
        rel = path.relative_to(root)
        for number, line in enumerate(text.splitlines(), 1):
            for match in MARKDOWN_LINK.finditer(line):
                target = match.group(1).strip().strip('<>')
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path and not parsed.fragment:
                    continue
                destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
                if not destination.is_relative_to(root.resolve()):
                    errors.append(f'{rel}:{number}: link escapes the repository: {target}')
                    continue
                if not destination.exists():
                    errors.append(f'{rel}:{number}: missing local link target: {target}')
                    continue
                if parsed.fragment and destination.suffix.lower() == '.md':
                    target_text = destination.read_text(encoding='utf-8-sig')
                    if unquote(parsed.fragment) not in anchors(target_text):
                        errors.append(f'{rel}:{number}: missing Markdown anchor: {target}')
            for match in CODE_SPAN.finditer(line):
                candidate = match.group(1)
                if not REPO_PATH.match(candidate):
                    continue
                if '{' in candidate or '}' in candidate:
                    continue  # documented shell globs, not a literal source path
                candidate = candidate.split()[0].split('::', 1)[0].rstrip('.,:;')
                if 'node_modules' in Path(candidate).parts:
                    continue  # generated install tree; its absence is expected in a clean clone
                if any(candidate == runtime_path or candidate.startswith(runtime_path + '/')
                       for runtime_path in RUNTIME_PATHS):
                    continue  # runtime database, documented as generated state
                if not (root / candidate).exists():
                    errors.append(f'{rel}:{number}: missing repository path: {candidate}')
    return errors


def validate_api_examples(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    manifest_path = root / 'docs/examples/api/examples.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        return [f'docs/examples/api/examples.json: invalid manifest: {exc}']

    sys.path.insert(0, str(root / 'backend'))
    from fastapi.routing import APIRoute
    from app.main import app

    routes = {(method, route.path): route for route in app.routes if isinstance(route, APIRoute)
              for method in (route.methods or set())}
    for example in manifest.get('examples', []):
        label = f"{example.get('method')} {example.get('path')}"
        route = routes.get((example.get('method'), example.get('path')))
        if route is None:
            errors.append(f'{label}: route is not registered in FastAPI')
            continue
        try:
            request_path = manifest_path.parent / example['request']
            response_path = manifest_path.parent / example['response']
            for file_path in (request_path, response_path):
                if not file_path.resolve().is_relative_to(root.resolve()):
                    raise ValueError('example path escapes repository')
            request_data = json.loads(request_path.read_text(encoding='utf-8'))
            response_data = json.loads(response_path.read_text(encoding='utf-8').rstrip())
            for file_path, data in ((request_path, request_data), (response_path, response_data)):
                if not isinstance(data, dict):
                    raise ValueError(f'{file_path.name} must contain a JSON object')
                if contains_credential(data):
                    raise ValueError(f'{file_path.name} contains a credential-like field')
            if route.body_field is None or route.response_model is None:
                raise ValueError('example route must declare request and response models')
            request_model = next(iter(get_type_hints(route.endpoint).values()))
            request = request_model.model_validate(request_data)
            route.response_model.model_validate(response_data)
            if example.get('execute'):
                actual = route.endpoint(request)
                route.response_model.model_validate(actual)
                if actual.model_dump(mode='json') != response_data:
                    raise ValueError('documented response differs from actual deterministic route output')
        except Exception as exc:  # keep all failures actionable in the CI output
            errors.append(f'{label}: {exc}')
    return errors


def main() -> int:
    errors = validate_markdown() + validate_api_examples()
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Documentation links, repository references and typed API examples are valid.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
