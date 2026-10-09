import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.ai.model_client import ModelClient

@pytest.fixture
def client():
    return TestClient(app)

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
