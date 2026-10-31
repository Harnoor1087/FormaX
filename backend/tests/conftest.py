import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.ai.model_client import ModelClient
from app.ai.content_generator import content_generator
from app.storage.generation_store import GenerationStore
from app.api import routes
from app.config import settings

TEST_OPERATOR_TOKEN = "test-operator-token-" + ("o" * 40)
TEST_REVIEWER_TOKEN = "test-reviewer-token-" + ("r" * 40)


@pytest.fixture(autouse=True)
def disable_external_gemini(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(content_generator.model_client, "api_key", "")
    monkeypatch.setattr(routes.analyzer.model_client, "api_key", "")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OPERATOR_API_TOKEN", TEST_OPERATOR_TOKEN)
    monkeypatch.setattr(settings, "REVIEWER_API_TOKEN", TEST_REVIEWER_TOKEN)
    monkeypatch.setattr(routes, "generation_store", GenerationStore(str(tmp_path / "test.sqlite3")))
    test_client = TestClient(app)
    test_client.headers.update({"Authorization": f"Bearer {TEST_REVIEWER_TOKEN}"})
    return test_client

@pytest.fixture
def mock_model():
    client = ModelClient()
    client.set_mock_response({
        "topic": "Severe Weather Warning",
        "domain": "Disaster Management",
        "key_facts": [
            "Heavy rainfall expected across coastal areas",
            "Wind speeds up to 85 km/h recorded",
            "Emergency teams deployed on standby"
        ],
        "entities": ["National Weather Bureau", "Emergency Services"],
        "urgency": "high",
        "constraints": ["Keep warning instructions factual"],
        "missing_information": []
    })
    return client
