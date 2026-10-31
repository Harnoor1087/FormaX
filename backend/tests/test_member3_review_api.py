from fastapi.testclient import TestClient
from io import BytesIO
from pptx import Presentation

from app.main import app
from app.schemas.context import ExtractedContext
from app.storage.generation_store import GenerationStore
from app.api import routes
from app.config import settings


def test_generation_review_api_persists_edit_approval_and_export(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OPERATOR_API_TOKEN", "test-operator-token-" + ("o" * 40))
    monkeypatch.setattr(settings, "REVIEWER_API_TOKEN", "test-reviewer-token-" + ("r" * 40))
    store = GenerationStore(str(tmp_path / "api.sqlite3"))
    monkeypatch.setattr(routes, "generation_store", store)
    monkeypatch.setattr(
        routes.analyzer,
        "analyze",
        lambda _text: ExtractedContext(
            topic="Bridge closure after flooding",
            domain="Infrastructure",
            key_facts=["The bridge closed after flooding on Monday."],
            entities=["North Bridge"],
            urgency="high",
            constraints=[],
            missing_information=[],
        ),
    )
    client = TestClient(
        app,
        headers={"Authorization": "Bearer " + settings.REVIEWER_API_TOKEN},
    )
    response = client.post(
        "/api/generate",
        json={
            "source_text": "Bridge closure after flooding. The bridge closed after flooding on Monday.",
            "output_types": ["advisory"],
        },
    )

    assert response.status_code == 200
    generated = response.json()
    output = generated["outputs"][0]
    output_id = output["output_id"]
    generation_id = generated["generation_id"]
    assert output["validation"]["schema_valid"]
    assert output["validation"]["consistency_valid"]

    invalid_edit = client.patch(
        f"/api/v1/outputs/{output_id}",
        json={
            "title": "Unrelated title",
            "summary": "Revised summary.",
            "key_points": ["Unsupported claim."],
            "body": "No analyzed topic is included here.",
        },
    )
    assert invalid_edit.status_code == 200
    assert invalid_edit.json()["review_status"] == "draft"
    assert not invalid_edit.json()["validation"]["consistency_valid"]
    assert client.post(f"/api/v1/outputs/{output_id}/approve").status_code == 409

    valid_edit = client.patch(
        f"/api/v1/outputs/{output_id}",
        json={
            "title": output["title"],
            "summary": output["summary"],
            "key_points": output["key_points"],
            "body": output["body"],
        },
    )
    assert valid_edit.status_code == 200
    approved = client.post(f"/api/v1/outputs/{output_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    exported = client.post(f"/api/v1/outputs/{output_id}/export")
    assert exported.status_code == 200
    assert exported.json()["export_count"] == 1

    history = client.get("/api/v1/generations").json()["generations"]
    assert any(item["generation_id"] == generation_id for item in history)
    details = client.get(f"/api/v1/generations/{generation_id}")
    assert details.status_code == 200
    assert details.json()["outputs"][0]["review_status"] == "approved"
    assert [event["action"] for event in details.json()["events"]] == [
        "generated",
        "edited",
        "edited",
        "approved",
        "exported",
    ]


def test_approved_presentation_exports_as_powerpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OPERATOR_API_TOKEN", "test-operator-token-" + ("o" * 40))
    monkeypatch.setattr(settings, "REVIEWER_API_TOKEN", "test-reviewer-token-" + ("r" * 40))
    monkeypatch.setattr(routes, "generation_store", GenerationStore(str(tmp_path / "pptx.sqlite3")))
    monkeypatch.setattr(
        routes.analyzer,
        "analyze",
        lambda _text: ExtractedContext(
            topic="Bridge closure after flooding",
            domain="Infrastructure",
            key_facts=["The bridge closed after flooding on Monday."],
            entities=["North Bridge"],
            urgency="high",
            constraints=[],
            missing_information=[],
        ),
    )
    client = TestClient(
        app,
        headers={"Authorization": "Bearer " + settings.REVIEWER_API_TOKEN},
    )
    generated = client.post(
        "/api/generate",
        json={
            "source_text": "The North Bridge closed after flooding on Monday.",
            "output_types": ["presentation"],
        },
    )
    assert generated.status_code == 200
    output = generated.json()["outputs"][0]
    output_id = output["output_id"]

    not_approved = client.post(f"/api/v1/outputs/{output_id}/presentation.pptx")
    assert not_approved.status_code == 409

    approved = client.post(f"/api/v1/outputs/{output_id}/approve")
    assert approved.status_code == 200
    response = client.post(f"/api/v1/outputs/{output_id}/presentation.pptx")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    deck = Presentation(BytesIO(response.content))
    assert len(deck.slides) == 4
    slide_text = "\n".join(
        shape.text
        for slide in deck.slides
        for shape in slide.shapes
        if shape.has_text_frame
    )
    assert "Bridge closure after flooding" in slide_text
    assert "KEY FINDINGS & VERIFIED DATA" in slide_text
