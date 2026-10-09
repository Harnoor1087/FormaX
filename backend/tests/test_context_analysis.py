from app.ai.context_analyzer import ContextAnalyzer
from app.schemas.context import ExtractedContext

def test_context_analysis_schema_conformance(mock_model):
    analyzer = ContextAnalyzer(model_client=mock_model)
    source = "Heavy rainfall reported along coastal belt with high winds."
    
    extracted: ExtractedContext = analyzer.analyze(source)
    assert extracted.topic == "Severe Weather Warning"
    assert extracted.domain == "Disaster Management"
    assert len(extracted.key_facts) == 3
    assert "National Weather Bureau" in extracted.entities
    assert extracted.urgency == "high"

def test_context_analysis_heuristic_fallback():
    # Test heuristic fallback with no API key and no mock
    analyzer = ContextAnalyzer()
    source = (
        "Critical cybersecurity incident reported at State Data Center. "
        "A severe zero-day vulnerability in web portal was identified by the CERT team on August 14. "
        "Engineers have deployed emergency firewall rules."
    )
    extracted: ExtractedContext = analyzer.analyze(source)
    
    assert extracted.domain == "Cybersecurity"
    assert extracted.urgency in ["high", "critical"]
    assert len(extracted.key_facts) > 0
