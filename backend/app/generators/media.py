from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem

def generate_infographic(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates structured infographic content specification (Synopsis Section 1.1 & 4).
    """
    title = f"Infographic Blueprint: {ctx.topic[:60]}"
    summary = f"Visual storytelling specification and layout schema on {ctx.topic}."
    
    key_points = ctx.key_facts[:4] if ctx.key_facts else ["Key visual metric extracted from source."]

    sections = [
        "[HEADER BANNER]",
        f"Primary Headline: {ctx.topic}",
        f"Subheading: Official Data Breakdown | Domain: {ctx.domain}",
        f"Urgency Badge: {ctx.urgency.upper()}",
        "",
        "[KEY STAT & CALLOUT CARDS]",
    ]

    for i, pt in enumerate(key_points, 1):
        sections.append(f"Card {i}: {pt}")

    sections.extend([
        "",
        "[PROCESS / TIMELINE FLOW]",
        "Step 1: Event Identification & Source Ingestion",
        f"Step 2: Analysis of Critical Factors ({ctx.urgency} priority)",
        "Step 3: Response Deployment & Actionable Protocols",
        "",
        "[FOOTER ATTRIBUTION]",
        f"Audience: {ctx.parameters.audience} | Source: FormaX AI Verified Data Pipeline"
    ])

    return GenerateOutputItem(
        output_type="infographic",
        title=title,
        summary=summary,
        key_points=key_points,
        body="\n".join(sections),
    )

def generate_video_package(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates a full video production package (Synopsis Section 1.1 & 1.2):
    Script, storyboard, scene descriptions, narration, subtitles, and visual recommendations.
    """
    title = f"Video Package: {ctx.topic[:60]}"
    summary = (
        f"Complete video production package for {ctx.topic}: "
        f"includes 4-scene storyboard, voiceover narration, subtitles, and camera directions."
    )
    
    key_points = ctx.key_facts[:4] if ctx.key_facts else ["Primary scene event."]

    scenes = [
        "============================================================",
        "SCENE 1: THE OPENING HOOK (Duration: 0:00 - 0:15)",
        "------------------------------------------------------------",
        f"• Visual Recommendation: Wide establishing shot representing {ctx.domain.lower()} operations. Overlay warning graphics.",
        f"• Storyboard: Camera zooms in on digital map displaying {ctx.topic[:40]}.",
        f"• Narration (Voiceover): 'Important operational update regarding {ctx.topic}. Here is what you need to know.'",
        f"• Subtitles (SRT): 'Important operational update regarding {ctx.topic}.'",
        "",
        "SCENE 2: CORE FACTS & EVIDENCE (Duration: 0:15 - 0:45)",
        "------------------------------------------------------------",
        "• Visual Recommendation: Split screen showing verified bullet points and relevant iconography.",
        "• Storyboard: Graphic cards animate on screen displaying key findings.",
        f"• Narration (Voiceover): 'Verified sources confirm: {key_points[0] if key_points else 'Key situation detected.'}'",
        f"• Subtitles (SRT): '{key_points[0] if key_points else 'Key situation detected.'}'",
        "",
        "SCENE 3: IMPACT & PROTOCOLS (Duration: 0:45 - 1:15)",
        "------------------------------------------------------------",
        f"• Visual Recommendation: Dynamic infographic callouts emphasizing {ctx.urgency} urgency.",
        f"• Storyboard: Highlight directives tailored for {ctx.parameters.audience}.",
        f"• Narration (Voiceover): 'All personnel and leadership must coordinate according to designated protocol.'",
        "• Subtitles (SRT): 'All personnel must coordinate according to designated protocol.'",
        "",
        "SCENE 4: CLOSING & CALL TO ACTION (Duration: 1:15 - 1:30)",
        "------------------------------------------------------------",
        "• Visual Recommendation: Clean FormaX AI credential badge and institutional contact slate.",
        "• Storyboard: Fade to brand card with verified link prompt.",
        "• Narration (Voiceover): 'Stay grounded in verified facts. Check internal portals for real-time updates.'",
        "• Subtitles (SRT): 'Stay grounded in verified facts. Check internal portals for updates.'",
        "============================================================"
    ]

    return GenerateOutputItem(
        output_type="video_package",
        title=title,
        summary=summary,
        key_points=key_points,
        body="\n".join(scenes),
    )
