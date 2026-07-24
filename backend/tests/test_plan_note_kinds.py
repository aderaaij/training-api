"""Plan-note kind validation on POST /api/plan-notes.

"feedback" notes were originally only written ORM-side by the plan-completion
flow, so the request schema's kind pattern never listed it — while the MCP's
append_plan_note advertised it as valid, making the API 422 on a kind the
tool contract promised. The schema now derives its pattern from NOTE_KINDS,
which includes "feedback".
"""


def make_note(client, **overrides):
    body = {"kind": "observation", "summary": "Prefers morning runs."}
    body.update(overrides)
    return client.post("/api/plan-notes", json=body)


def test_all_kinds_accepted(client_a):
    from app.schemas.plan_note import NOTE_KINDS

    for kind in NOTE_KINDS:
        r = make_note(client_a, kind=kind, summary=f"{kind} note")
        assert r.status_code == 201, f"kind={kind}: {r.text}"
        assert r.json()["kind"] == kind


def test_unknown_kind_rejected(client_a):
    assert make_note(client_a, kind="musing").status_code == 422


def test_summary_over_280_chars_rejected(client_a):
    r = make_note(client_a, summary="x" * 281)
    assert r.status_code == 422
    assert "280" in r.text  # the limit must be visible to the caller
