from app.schemas.response import GenerateOutputItem, OutputValidation
from app.storage.generation_store import GenerationStore


def test_generation_storage_review_and_export_lifecycle(tmp_path):
    store = GenerationStore(str(tmp_path / "test.sqlite3"))
    context = {
        "source_text": "The bridge closed after flooding on Monday.",
        "topic": "Bridge closure after flooding",
        "domain": "Infrastructure",
        "key_facts": ["The bridge closed after flooding on Monday."],
        "entities": ["North Bridge"],
        "urgency": "high",
        "constraints": [],
        "missing_information": [],
        "parameters": {
            "audience": "government officials",
            "tone": "formal",
            "language": "English",
            "objective": "inform",
            "detail_level": "medium",
        },
    }
    from app.schemas.context import StructuredContext

    output = GenerateOutputItem(
        output_type="advisory",
        title="Advisory: Bridge closure after flooding",
        summary="A bridge closure advisory.",
        key_points=["The bridge closed after flooding on Monday."],
        body="Bridge closure after flooding is the subject of this advisory.",
        generation_mode="template_fallback",
        validation=OutputValidation(schema_valid=True, consistency_valid=True),
    )
    generation_id, saved_outputs = store.create_generation(
        "req_test123",
        StructuredContext.model_validate(context),
        OutputValidation(schema_valid=True, consistency_valid=True),
        [output],
    )

    saved = saved_outputs[0]
    assert saved.output_id
    assert saved.review_status == "draft"
    assert store.get_generation(generation_id)["outputs"][0]["title"] == output.title
    assert store.get_generation(generation_id)["outputs"][0]["generation_mode"] == "template_fallback"
    assert store.get_generation(generation_id)["generation_mode"] == "template"
    assert store.record_export(saved.output_id) is None

    updated = store.update_output(
        saved.output_id,
        output.model_copy(update={"title": "Revised bridge advisory"}),
        OutputValidation(schema_valid=True, consistency_valid=True),
    )
    assert updated["review_status"] == "draft"
    assert updated["approved_at"] is None

    approved = store.approve_output(saved.output_id)
    assert approved["review_status"] == "approved"
    exported = store.record_export(saved.output_id)
    assert exported["export_count"] == 1
    assert store.list_generations()[0]["approved_count"] == 1
