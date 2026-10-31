from types import SimpleNamespace

import pytest

from app.ai.content_generator import content_generator
from app.api import routes
from app.config import settings
from app.schemas.context import ExtractedContext


class ProviderError(Exception):
    def __init__(self, code):
        super().__init__("simulated provider response")
        self.code = code


def _create_approved_video_package(client, monkeypatch):
    monkeypatch.setattr(content_generator.model_client, "api_key", "")
    monkeypatch.setattr(
        routes.analyzer,
        "analyze",
        lambda _text: ExtractedContext(
            topic="Bridge closure after flooding",
            domain="Infrastructure",
            key_facts=["The bridge closed on Monday after flooding."],
            entities=["North Bridge"],
            urgency="high",
            constraints=[],
            missing_information=[],
        ),
    )
    response = client.post(
        "/api/generate",
        json={
            "source_text": (
                "The city announced a pedestrian bridge closure after flooding. "
                "The bridge closed on Monday while engineers inspect the structure."
            ),
            "output_types": ["video_package"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    output = payload["outputs"][0]
    assert output["validation"]["schema_valid"]
    assert output["validation"]["consistency_valid"]
    approved = client.post(f"/api/v1/outputs/{output['output_id']}/approve")
    assert approved.status_code == 200
    return output, payload["generation_id"]


def test_approved_video_package_renders_and_downloads_mp4(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(settings, "VIDEO_OUTPUT_DIR", str(tmp_path / "videos"))
    monkeypatch.setattr(
        routes.veo_video_generator,
        "start",
        lambda prompt: "operations/video-123",
    )

    def complete_operation(_operation_name):
        return SimpleNamespace(
            done=True,
            error=None,
            response=SimpleNamespace(
                generated_videos=[SimpleNamespace(video="remote/video-123")]
            ),
        )

    def download_video(_generated_video, destination):
        destination.write_bytes(b"test-mp4-data")

    monkeypatch.setattr(routes.veo_video_generator, "get_operation", complete_operation)
    monkeypatch.setattr(routes.veo_video_generator, "download", download_video)
    output, generation_id = _create_approved_video_package(client, monkeypatch)

    started = client.post(f"/api/v1/outputs/{output['output_id']}/video")
    assert started.status_code == 202
    job = started.json()
    assert job["status"] == "processing"
    assert "operation" not in job
    assert "file_path" not in job

    completed = client.get(f"/api/v1/video-jobs/{job['video_job_id']}")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["download_url"].endswith("/download")

    downloaded = client.get(completed.json()["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "video/mp4"
    assert downloaded.content == b"test-mp4-data"
    assert client.post(f"/api/v1/outputs/{output['output_id']}/video").status_code == 409

    generation = client.get(
        f"/api/v1/generations/{generation_id}"
    ).json()
    actions = [event["action"] for event in generation["events"]]
    assert "video_generation_started" in actions
    assert "video_generated" in actions
    assert "video_downloaded" in actions


def test_video_render_requires_api_key(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    output, _generation_id = _create_approved_video_package(client, monkeypatch)

    response = client.post(f"/api/v1/outputs/{output['output_id']}/video")

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_video_quota_error_is_reported_to_reviewer(client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")

    def quota_exhausted(_prompt):
        raise ProviderError(429)

    monkeypatch.setattr(routes.veo_video_generator, "start", quota_exhausted)
    output, _generation_id = _create_approved_video_package(client, monkeypatch)

    response = client.post(f"/api/v1/outputs/{output['output_id']}/video")

    assert response.status_code == 429
    assert "quota is exhausted" in response.json()["detail"]
    assert "simulated provider response" not in response.json()["detail"]
    job = client.get(f"/api/v1/outputs/{output['output_id']}/video").json()["job"]
    assert job["status"] == "failed"
    assert "quota is exhausted" in job["error"]


@pytest.mark.parametrize("status_code", [429, 503])
def test_generate_compat_marks_template_fallback_when_gemini_is_unavailable(
    client, monkeypatch, status_code
):
    monkeypatch.setattr(content_generator.model_client, "api_key", "configured-for-test")
    monkeypatch.setattr(
        routes.analyzer,
        "analyze",
        lambda _text: ExtractedContext(
            topic="Routing explanation",
            domain="Software",
            key_facts=["A router sends requests to matching handlers."],
            entities=[],
            urgency="low",
            constraints=[],
            missing_information=[],
        ),
    )

    def temporarily_unavailable(*_args, **_kwargs):
        error = RuntimeError(f"Gemini provider error (HTTP {status_code}).")
        error.__cause__ = ProviderError(status_code)
        raise error

    monkeypatch.setattr(
        content_generator.model_client,
        "generate_json",
        temporarily_unavailable,
    )
    response = client.post(
        "/api/generate",
        json={
            "source_text": "A router sends requests to matching handlers.",
            "output_types": ["video_package"],
        },
    )

    assert response.status_code == 200
    generated = response.json()
    assert generated["generation_mode"] == "template_fallback"
    output = generated["outputs"][0]
    assert output["generation_mode"] == "template_fallback"
    assert output["validation"]["schema_valid"]
    assert output["validation"]["consistency_valid"]
    assert "Template fallback" not in output["body"]
    saved = client.get(f"/api/v1/generations/{generated['generation_id']}").json()
    assert saved["generation_mode"] == "template_fallback"
    assert saved["outputs"][0]["generation_mode"] == "template_fallback"


def test_editing_approved_video_brief_stales_render_and_allows_new_one(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")
    starts = iter(["operations/video-1", "operations/video-2"])
    monkeypatch.setattr(
        routes.veo_video_generator,
        "start",
        lambda _prompt: next(starts),
    )
    output, _generation_id = _create_approved_video_package(client, monkeypatch)

    first_job = client.post(f"/api/v1/outputs/{output['output_id']}/video").json()
    update = client.patch(
        f"/api/v1/outputs/{output['output_id']}",
        json={
            "title": output["title"],
            "summary": output["summary"] + " Revised.",
            "key_points": output["key_points"],
            "body": output["body"],
        },
    )
    assert update.status_code == 200
    stale = client.get(f"/api/v1/video-jobs/{first_job['video_job_id']}")
    assert stale.status_code == 200
    assert stale.json()["status"] == "stale"

    assert client.post(f"/api/v1/outputs/{output['output_id']}/approve").status_code == 200
    second_job = client.post(f"/api/v1/outputs/{output['output_id']}/video")
    assert second_job.status_code == 202
    assert second_job.json()["video_job_id"] != first_job["video_job_id"]
