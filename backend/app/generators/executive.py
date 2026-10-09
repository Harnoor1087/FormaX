from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem

def generate_executive_summary(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates a high-level briefing for executive leadership (Synopsis Section 1.2).
    """
    title = f"Executive Briefing: {ctx.topic[:70]}"
    summary = (
        f"Concise strategic summary on {ctx.topic} prepared for {ctx.parameters.audience} "
        f"with assessed urgency of {ctx.urgency.upper()}."
    )
    
    key_points = ctx.key_facts[:4] if ctx.key_facts else ["Executive fact extracted from source."]

    body_lines = [
        f"EXECUTIVE SUMMARY | DOMAIN: {ctx.domain.upper()}",
        "=" * 50,
        "",
        "1. STRATEGIC CONTEXT",
        f"This briefing consolidates primary verified intelligence regarding {ctx.topic}. "
        f"Target audience: {ctx.parameters.audience}. Tone: {ctx.parameters.tone}.",
        "",
        "2. CORE FINDINGS & EVIDENCE",
    ]

    for pt in key_points:
        body_lines.append(f"• {pt}")

    body_lines.extend([
        "",
        "3. RISK & IMPACT ASSESSMENT",
        f"Urgency is classified as {ctx.urgency.upper()}. "
        f"Operational constraints mandate strict adherence to source facts without speculative projection.",
        "",
        "4. DECISION RECOMMENDATIONS",
        "- Authorize immediate tactical briefing for field and coordination teams.",
        "- Allocate targeted monitoring resources to key entities identified in report.",
        "- Maintain scheduled communication cadence pending further developments."
    ])

    return GenerateOutputItem(
        output_type="executive_summary",
        title=title,
        summary=summary,
        key_points=key_points,
        body="\n".join(body_lines),
    )

def generate_presentation(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates structured slide presentation content (Synopsis Section 1.1).
    """
    title = f"Presentation Deck: {ctx.topic[:60]}"
    summary = f"4-slide structured executive presentation deck on {ctx.topic}."
    
    key_points = ctx.key_facts[:4] if ctx.key_facts else ["Key slide points."]

    slides = [
        f"[SLIDE 1: TITLE & EXECUTIVE AGENDA]\n"
        f"Title: {ctx.topic}\n"
        f"Subtitle: Strategic Briefing for {ctx.parameters.audience.title()}\n"
        f"Domain: {ctx.domain} | Urgency: {ctx.urgency.upper()}",

        f"[SLIDE 2: BACKGROUND & SITUATIONAL OVERVIEW]\n"
        f"• Overview of core context and origin of developments.\n"
        f"• Impacted Domain: {ctx.domain}\n"
        f"• Identified Entities: {', '.join(ctx.entities[:4]) if ctx.entities else 'Referenced in source documentation.'}",

        f"[SLIDE 3: KEY FINDINGS & VERIFIED DATA]\n" +
        "\n".join([f"• {f}" for f in key_points]),

        f"[SLIDE 4: STRATEGIC RECOMMENDATIONS & NEXT STEPS]\n"
        f"• Direct action items tailored for {ctx.parameters.audience}.\n"
        f"• Prioritize immediate response protocols according to {ctx.urgency.upper()} urgency.\n"
        f"• Establish review feedback loop."
    ]

    return GenerateOutputItem(
        output_type="presentation",
        title=title,
        summary=summary,
        key_points=key_points,
        body="\n\n" + ("=" * 40) + "\n\n".join(slides),
    )
