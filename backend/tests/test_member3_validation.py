from app.schemas.response import GenerateOutputItem
from app.generators.validation import validate_outputs
from app.routing.format_router import default_router
from app.schemas.context import GenerationParameters, StructuredContext
from app.schemas.request import OutputType


def test_registered_generators_pass_source_consistency_checks():
    context = StructuredContext(
        source_text="The bridge closed after flooding on Monday.",
        topic="Bridge closure after flooding",
        domain="Infrastructure",
        key_facts=["The bridge closed after flooding on Monday."],
        entities=["North Bridge"],
        urgency="high",
        constraints=[],
        parameters=GenerationParameters(
            audience="government officials",
            tone="formal",
            language="English",
            objective="inform",
            detail_level="medium",
        ),
    )

    outputs = default_router.route(
        context,
        [
            OutputType.ADVISORY,
            OutputType.LINKEDIN_POST,
            OutputType.TWITTER_THREAD,
            OutputType.EXECUTIVE_SUMMARY,
            OutputType.PRESENTATION,
            OutputType.INFOGRAPHIC,
            OutputType.VIDEO_PACKAGE,
        ],
    )
    result = validate_outputs(context, outputs)

    assert result.schema_valid
    assert result.consistency_valid
    assert result.issues == []
    for output in outputs:
        assert "verify perimeter status" not in output.body.casefold()
        assert "tactical briefing" not in output.body.casefold()
        assert "digital map" not in output.body.casefold()

    thread_context = context.model_copy(update={"key_facts": context.key_facts * 4})
    thread = default_router.route(thread_context, [OutputType.TWITTER_THREAD])[0]
    assert thread.summary.startswith("A 5-part")
    assert "5/5 Summary:" in thread.body


def test_validator_flags_unsupported_facts_and_missing_shared_topic():
    context = StructuredContext(
        source_text="A bridge closed.",
        topic="Bridge closure",
        domain="Infrastructure",
        key_facts=["The bridge closed."],
        entities=[],
        urgency="medium",
        constraints=[],
        parameters=GenerationParameters(
            audience="general public",
            tone="neutral",
            language="English",
            objective="inform",
            detail_level="brief",
        ),
    )
    output = default_router.route(context, [OutputType.ADVISORY])[0].model_copy(
        update={
            "title": "Unrelated title",
            "body": (
                "VERIFIED FACTUAL FINDINGS\n"
                "REQUIRED ACTIONS & MITIGATION\n"
                "SOURCE LIMITATIONS"
            ),
            "key_points": ["The bridge reopened."],
        }
    )

    result = validate_outputs(context, [output])

    assert result.schema_valid
    assert not result.consistency_valid
    assert len(result.issues) == 2


def test_gemini_formats_pass_with_equivalent_headings_and_topic_wording():
    context = StructuredContext(
        source_text=(
            "The City Library will close on Monday, October 12, for roof repairs. "
            "The Central Branch expects to reopen on Wednesday, October 14. "
            "Visitors can use the East Branch during the closure. "
            "No other service changes were announced."
        ),
        topic="Temporary closure of the City Library Central Branch for roof repairs",
        domain="Public Services",
        key_facts=[
            "The City Library Central Branch will close on Monday, October 12, for roof repairs.",
            "The Central Branch expects to reopen on Wednesday, October 14.",
            "Visitors can use the East Branch during the closure period.",
            "No other service changes were announced.",
        ],
        entities=["City Library", "Central Branch", "East Branch"],
        urgency="low",
        constraints=[],
        parameters=GenerationParameters(
            audience="general public",
            tone="formal",
            language="English",
            objective="inform",
            detail_level="medium",
        ),
    )
    drafts = [
        (
            "advisory",
            "Public Advisory: Temporary Closure of City Library Central Branch",
            "### Context\nTemporary City Library closure for roof repairs.\n"
            "### Verified Findings\nThe City Library Central Branch will close Monday.\n"
            "### Appropriate Next Steps\nVisitors may use the East Branch.\n"
            "### Source Limitations\nReopening is expected, not guaranteed.",
        ),
        (
            "linkedin_post",
            "Notice: Temporary Closure of City Library Central Branch",
            "The City Library Central Branch will temporarily close Monday for roof repairs.\n"
            "Visitors may use the East Branch. #CityLibrary #PublicNotice",
        ),
        (
            "twitter_thread",
            "Service Notice: City Library Central Branch Temporary Closure",
            "1/3 The City Library Central Branch will close Monday for roof repairs.\n"
            "2/3 Reopening is expected Wednesday. #CityLibrary\n"
            "3/3 Visitors can use the East Branch.",
        ),
        (
            "executive_summary",
            "Executive Summary: Temporary Closure of City Library Central Branch",
            "Context: City Library Central Branch closure for roof repairs.\n"
            "Key Findings:\nThe library closes Monday and expects to reopen Wednesday.\n"
            "Stated Urgency and Limitations:\nThe reopening date is expected.\n"
            "Decision Considerations:\nVisitors can use the East Branch.",
        ),
        (
            "presentation",
            "Temporary Closure of City Library Central Branch",
            "Slide 1: Temporary closure of City Library Central Branch for roof repairs.\n"
            "Slide 2: The closure starts Monday.\n"
            "Slide 3: Visitors may use the East Branch.\n"
            "Slide 4: Reopening is expected Wednesday.",
        ),
        (
            "infographic",
            "Infographic Brief: Temporary Closure of City Library Central Branch",
            "# Visual Brief\n## Headline\nCity Library Central Branch closure for roof repairs.\n"
            "## Fact Callouts\nClosure Monday; reopening expected Wednesday.\n"
            "## Timeline Flow\nVisitors can use the East Branch.",
        ),
        (
            "video_package",
            "Video Production Brief: City Library Central Branch Temporary Closure",
            "OBJECTIVE: Inform the public about the City Library Central Branch closure for roof repairs.\n"
            "SCENE 1\nVISUAL / STORYBOARD: Show the library sign.\n"
            "NARRATION (VOICEOVER): The library closes Monday.\nSUBTITLES: Closure begins Monday.\n"
            "SCENE 2\nVISUAL / STORYBOARD: Show a date card.\n"
            "NARRATION: Reopening is expected Wednesday.\nSUBTITLES: Expected reopening Wednesday.",
        ),
    ]
    outputs = [
        GenerateOutputItem(
            output_type=output_type,
            title=title,
            summary="City Library Central Branch service update.",
            key_points=context.key_facts[:2],
            body=body,
        )
        for output_type, title, body in drafts
    ]

    result = validate_outputs(context, outputs)

    assert result.schema_valid, result.issues
    assert result.consistency_valid, result.issues


def test_validator_accepts_paraphrased_source_key_points():
    context = StructuredContext(
        source_text=(
            "Visitors can use the East Branch during the closure period."
        ),
        topic="East Branch access during closure",
        domain="Public Services",
        key_facts=["Visitors can use the East Branch during the closure period."],
        entities=["East Branch"],
        urgency="low",
        constraints=[],
        parameters=GenerationParameters(
            audience="general public",
            tone="formal",
            language="English",
            objective="inform",
            detail_level="medium",
        ),
    )
    output = default_router.route(context, [OutputType.ADVISORY])[0].model_copy(
        update={"key_points": ["Visitors may use the East Branch during the closure."]}
    )

    result = validate_outputs(context, [output])

    assert result.schema_valid, result.issues
    assert result.consistency_valid, result.issues


def test_video_package_accepts_bracketed_scenes_and_facts_from_long_source():
    context = StructuredContext(
        source_text=(
            "A short opening fact. The original record continues with several details. "
            "The fire revealed a new passion, fear, which the narrator had just discovered. "
            "The record later describes the narrator's response."
        ),
        topic="Narrator discovers fear after fire",
        domain="Literature",
        key_facts=["A short opening fact."],
        entities=[],
        urgency="low",
        constraints=[],
        parameters=GenerationParameters(
            audience="general public",
            tone="formal",
            language="English",
            objective="inform",
            detail_level="medium",
        ),
    )
    output = GenerateOutputItem(
        output_type="video_package",
        title="Narrator discovers fear after fire",
        summary="A source-based video script package.",
        key_points=["The narrator discovered fear after the fire revealed a new passion."],
        body=(
            "[Scene 1: Opening]\n"
            "Visual / Storyboard: Show the source title.\n"
            "Narration: The record begins.\n"
            "Subtitles: Opening record.\n"
            "[Scene 2: Verified detail]\n"
            "Visual / Storyboard: Show the documented detail.\n"
            "Narration: The fire revealed a new passion, fear.\n"
            "Subtitles: The narrator discovered fear."
        ),
    )

    result = validate_outputs(context, [output])

    assert result.schema_valid, result.issues
    assert result.consistency_valid, result.issues


def test_video_package_accepts_paraphrased_topic_and_long_compound_key_point():
    context = StructuredContext(
        source_text=(
            "The opening record contains an initial observation. The narrator explores the "
            "new garden and names its animals, including a dodo. Later the narrator rubs dry "
            "sticks together and produces fire, smoke, and flames. These events are recorded "
            "across multiple sections of the original diary."
        ),
        topic="Fictional diary of Eve exploring Eden with Adam",
        domain="Literature",
        key_facts=["The diary begins with an initial observation."],
        entities=["Eve", "Adam"],
        urgency="low",
        constraints=[],
        parameters=GenerationParameters(
            audience="general public",
            tone="formal",
            language="English",
            objective="inform",
            detail_level="medium",
        ),
    )
    output = GenerateOutputItem(
        output_type="video_package",
        title="Eve and Adam's Eden Diary",
        summary="A source-based overview of the diary's events.",
        key_points=[
            "Eve names animals including the dodo, then makes fire, smoke, and flames by rubbing dry sticks."
        ],
        body=(
            "SCENE 1: The diary\n"
            "Visual / Storyboard: Show Eve and Adam's diary in Eden.\n"
            "Narration: The diary records Eve exploring the garden with Adam.\n"
            "Subtitles: Eve and Adam in Eden.\n"
            "SCENE 2: Discoveries\n"
            "Visual / Storyboard: Show the recorded discoveries.\n"
            "Narration: Eve names animals and creates fire.\n"
            "Subtitles: A diary of discoveries."
        ),
    )

    result = validate_outputs(context, [output])

    assert result.schema_valid, result.issues
    assert result.consistency_valid, result.issues


def test_video_package_matches_supported_details_across_distant_source_sections():
    context = StructuredContext(
        source_text=(
            "The narrator feels like an experiment in the newly created world. "
            + ("Several unrelated observations are recorded in the diary. " * 35)
            + "She learned a lesson and made an axiom from her own head."
        ),
        topic="Eve's diary and early observations",
        domain="Literature",
        key_facts=["The diary describes early observations."],
        entities=["Eve"],
        urgency="low",
        constraints=[],
        parameters=GenerationParameters(
            audience="general public",
            tone="formal",
            language="English",
            objective="inform",
            detail_level="medium",
        ),
    )
    output = GenerateOutputItem(
        output_type="video_package",
        title="Eve's diary and early observations",
        summary="A source-based diary overview.",
        key_points=[
            "The narrator conceives of herself as an experiment and establishes axioms based on physical interactions with her environment."
        ],
        body=(
            "SCENE 1: Diary\n"
            "Visual / Storyboard: Show the diary.\n"
            "Narration: Eve records her observations.\n"
            "Subtitles: Diary observations.\n"
            "SCENE 2: Reflection\n"
            "Visual / Storyboard: Show the recorded reflection.\n"
            "Narration: The narrator reflects on the experiment and her axiom.\n"
            "Subtitles: A recorded reflection."
        ),
    )

    result = validate_outputs(context, [output])

    assert result.schema_valid, result.issues
    assert result.consistency_valid, result.issues


def test_video_package_still_rejects_key_points_not_in_source():
    context = StructuredContext(
        source_text="The library will close for repairs on Monday.",
        topic="Library closure for repairs",
        domain="Public Services",
        key_facts=["The library will close for repairs on Monday."],
        entities=[],
        urgency="low",
        constraints=[],
        parameters=GenerationParameters(
            audience="general public",
            tone="formal",
            language="English",
            objective="inform",
            detail_level="medium",
        ),
    )
    output = default_router.route(context, [OutputType.VIDEO_PACKAGE])[0].model_copy(
        update={"key_points": ["A volcanic eruption displaced thousands of residents."]}
    )

    result = validate_outputs(context, [output])

    assert result.schema_valid
    assert not result.consistency_valid
    assert any("key point" in issue for issue in result.issues)


def test_validator_accepts_localized_hindi_and_punjabi_advisories():
    localized = [
        (
            "Hindi",
            "सिटी लाइब्रेरी सोमवार, 12 अक्टूबर को मरम्मत के लिए बंद रहेगी।",
            "संदर्भ\nसिटी लाइब्रेरी की अस्थायी बंदी।\n"
            "सत्यापित निष्कर्ष\nसिटी लाइब्रेरी सोमवार, 12 अक्टूबर को बंद रहेगी।\n"
            "उचित आगामी कदम\nआगंतुक ईस्ट शाखा की सेवाओं का उपयोग कर सकते हैं।\n"
            "स्रोत सीमाएँ\nपुनः खुलने का समय उपलब्ध नहीं है।",
        ),
        (
            "Punjabi",
            "ਸਿਟੀ ਲਾਇਬ੍ਰੇਰੀ ਸੋਮਵਾਰ, 12 ਅਕਤੂਬਰ ਨੂੰ ਮੁਰੰਮਤ ਲਈ ਬੰਦ ਰਹੇਗੀ।",
            "ਸੰਦਰਭ\nਸਿਟੀ ਲਾਇਬ੍ਰੇਰੀ ਦੀ ਅਸਥਾਈ ਬੰਦਸ਼।\n"
            "ਪੁਸ਼ਟੀ ਕੀਤੇ ਤੱਥ\nਸਿਟੀ ਲਾਇਬ੍ਰੇਰੀ ਸੋਮਵਾਰ, 12 ਅਕਤੂਬਰ ਨੂੰ ਬੰਦ ਰਹੇਗੀ।\n"
            "ਅਗਲੇ ਕਦਮ\nਮੁਲਾਕਾਤੀ ਈਸਟ ਸ਼ਾਖਾ ਦੀਆਂ ਸੇਵਾਵਾਂ ਵਰਤ ਸਕਦੇ ਹਨ।\n"
            "ਸਰੋਤ ਦੀਆਂ ਸੀਮਾਵਾਂ\nਮੁੜ ਖੁੱਲ੍ਹਣ ਦਾ ਸਮਾਂ ਉਪਲਬਧ ਨਹੀਂ ਹੈ।",
        ),
    ]
    source_facts = [
        "The City Library will close on Monday, October 12, for roof repairs.",
        "The Central Branch expects to reopen on Wednesday, October 14.",
        "Visitors can use the East Branch during the closure.",
    ]

    for language, key_point, body in localized:
        context = StructuredContext(
            source_text=" ".join(source_facts),
            topic="City Library temporary closure for roof repairs",
            domain="Public Services",
            key_facts=source_facts,
            entities=["City Library", "Central Branch", "East Branch"],
            urgency="low",
            constraints=[],
            parameters=GenerationParameters(
                audience="general public",
                tone="formal",
                language=language,
                objective="inform",
                detail_level="medium",
            ),
        )
        output = GenerateOutputItem(
            output_type="advisory",
            title=key_point,
            summary=key_point,
            key_points=[key_point],
            body=body,
        )

        result = validate_outputs(context, [output])
        assert result.schema_valid, result.issues
        assert result.consistency_valid, result.issues

        unsupported = output.model_copy(
            update={"key_points": [key_point.replace("12", "99")]}
        )
        rejected = validate_outputs(context, [unsupported])
        assert not rejected.consistency_valid
        assert any("key point" in issue for issue in rejected.issues)
