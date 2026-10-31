from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem

def generate_infographic(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates structured infographic content specification (Synopsis Section 1.1 & 4).
    """
    title = f"Infographic Blueprint: {ctx.topic}"
    summary = f"Visual storytelling specification and layout schema on {ctx.topic}."
    
    key_points = ctx.key_facts[:4]

    sections = [
        "[HEADER BANNER]",
        f"Primary Headline: {ctx.topic}",
        f"Subheading: Source-based overview | Domain: {ctx.domain}",
        f"Urgency Badge: {ctx.urgency.upper()}",
        "",
        "[KEY STAT & CALLOUT CARDS]",
    ]

    for i, pt in enumerate(key_points, 1):
        sections.append(f"Card {i}: {pt}")

    sections.extend([
        "",
        "[PROCESS / TIMELINE FLOW]",
        "Step 1: Identify the subject described in the source",
        f"Step 2: Present the analyzed findings ({ctx.urgency} urgency)",
        "Step 3: Direct viewers to applicable official guidance",
        "",
        "[FOOTER ATTRIBUTION]",
        f"Audience: {ctx.parameters.audience} | Factual callouts are limited to the analyzed source"
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
    title = f"Video Package: {ctx.topic}"
    summary = (
        f"Complete video production package for {ctx.topic}: "
        f"includes 4-scene storyboard, voiceover narration, subtitles, and camera directions."
    )
    
    key_points = ctx.key_facts[:4]

    scenes = [
        "============================================================",
        "SCENE 1: THE OPENING HOOK (Duration: 0:00 - 0:15)",
        "------------------------------------------------------------",
        f"• Visual Recommendation: Use topic-relevant imagery for {ctx.domain}; avoid visuals that imply unverified events.",
        f"• Storyboard: Display the topic heading: {ctx.topic}.",
        f"• Narration (Voiceover): 'Important operational update regarding {ctx.topic}. Here is what you need to know.'",
        f"• Subtitles (SRT): 'Important operational update regarding {ctx.topic}.'",
        "",
        "SCENE 2: CORE FACTS & EVIDENCE (Duration: 0:15 - 0:45)",
        "------------------------------------------------------------",
        "• Visual Recommendation: Show the verified source facts using neutral, relevant imagery.",
        "• Storyboard: Graphic cards animate on screen displaying key findings.",
        f"• Narration (Voiceover): 'Verified sources confirm: {key_points[0] if key_points else 'No verified key fact was extracted.'}'",
        f"• Subtitles (SRT): '{key_points[0] if key_points else 'No verified key fact was extracted.'}'",
        "",
        "SCENE 3: IMPACT & PROTOCOLS (Duration: 0:45 - 1:15)",
        "------------------------------------------------------------",
        f"• Visual Recommendation: Display the assessed urgency ({ctx.urgency}) without implying unreported impacts.",
        f"• Storyboard: Summarize the analyzed findings for {ctx.parameters.audience}.",
        "• Narration (Voiceover): 'Review the verified findings and consult the responsible authority for guidance.'",
        "• Subtitles (SRT): 'Review the verified findings and consult the responsible authority for guidance.'",
        "",
        "SCENE 4: CLOSING & CALL TO ACTION (Duration: 1:15 - 1:30)",
        "------------------------------------------------------------",
        "• Visual Recommendation: Use a neutral closing card; do not invent contact information.",
        "• Storyboard: End with a reminder to consult the relevant official source.",
        "• Narration (Voiceover): 'Consult the relevant official source for verified updates.'",
        "• Subtitles (SRT): 'Consult the relevant official source for verified updates.'",
        "============================================================"
    ]

    return GenerateOutputItem(
        output_type="video_package",
        title=title,
        summary=summary,
        key_points=key_points,
        body="\n".join(scenes),
    )
