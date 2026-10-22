import pytest

from app.evidence import recap_for
from app.simulator import generate


@pytest.mark.parametrize("persona", ["casual", "analyst", "favorite_team", "favorite_player", "broadcaster"])
def test_recap_locales_preserve_evidence_and_translate_persona_copy(persona):
    match, events = generate("comeback")
    responses = {
        locale: recap_for(match, events, locale, persona, 5400)
        for locale in ("en", "es", "hi")
    }
    baseline = responses["en"]
    for response in responses.values():
        assert response["provider"] == "verified_rule_based_templates"
        assert response["persona"] == persona
        assert response["locale"] in {"en", "es", "hi"}
        assert [
            (moment["insight_id"], moment["match_second"], moment["supporting_event_ids"])
            for moment in response["moments"]
        ] == [
            (moment["insight_id"], moment["match_second"], moment["supporting_event_ids"])
            for moment in baseline["moments"]
        ]

    spanish_text = " ".join([responses["es"]["lead"], *(m["text"] for m in responses["es"]["moments"])])
    hindi_text = " ".join([responses["hi"]["lead"], *(m["text"] for m in responses["hi"]["moments"])])
    if persona == "analyst":
        assert "eventos de origen" in spanish_text
        assert "स्रोत इवेंट" in hindi_text
    if persona == "broadcaster":
        assert "MARCÓ" in spanish_text
        assert "ने गोल किया" in hindi_text
