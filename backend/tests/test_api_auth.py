from app.config import settings

TEST_OPERATOR_TOKEN = "test-operator-token-" + ("o" * 40)
TEST_REVIEWER_TOKEN = "test-reviewer-token-" + ("r" * 40)


def test_auth_me_reports_operator_and_reviewer_roles(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json() == {"role": "reviewer"}

    operator = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {TEST_OPERATOR_TOKEN}"},
    )
    assert operator.status_code == 200
    assert operator.json() == {"role": "operator"}


def test_api_requires_a_valid_token(client):
    assert client.get("/api/v1/generations", headers={"Authorization": ""}).status_code == 401
    assert client.get(
        "/api/v1/generations",
        headers={"Authorization": "Bearer invalid-token"},
    ).status_code == 401


def test_only_reviewers_can_edit_approve_and_export(client, monkeypatch):
    monkeypatch.setattr(settings, "OPERATOR_API_TOKEN", TEST_OPERATOR_TOKEN)
    monkeypatch.setattr(settings, "REVIEWER_API_TOKEN", TEST_REVIEWER_TOKEN)
    operator_headers = {"Authorization": f"Bearer {TEST_OPERATOR_TOKEN}"}

    response = client.post(
        "/api/generate",
        headers=operator_headers,
        json={"source_text": "A public road will close for maintenance.", "output_types": ["advisory"]},
    )
    assert response.status_code == 200
    output_id = response.json()["outputs"][0]["output_id"]

    assert client.get("/api/v1/generations", headers=operator_headers).status_code == 200
    assert client.post(
        f"/api/v1/outputs/{output_id}/approve",
        headers=operator_headers,
    ).status_code == 403


def test_history_api_returns_not_configured_when_tokens_are_missing(client, monkeypatch):
    monkeypatch.setattr(settings, "OPERATOR_API_TOKEN", "")
    monkeypatch.setattr(settings, "REVIEWER_API_TOKEN", "")

    response = client.get("/api/v1/generations")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
