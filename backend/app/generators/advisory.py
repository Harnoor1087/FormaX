from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem

def generate_advisory(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates a formal, structured institutional advisory (Synopsis Section 1.2 & 4).
    """
    urgency_tag = ctx.urgency.upper()
    title = f"OPERATIONAL ADVISORY: {ctx.topic}"
    
    summary = (
        f"Source-based operational advisory for {ctx.parameters.audience}. "
        f"Urgency assessment: {urgency_tag}. Review the verified findings and applicable procedures."
    )
    
    key_points = ctx.key_facts[:5]

    body_sections = [
        f"ADVISORY CLASSIFICATION: {urgency_tag} | DOMAIN: {ctx.domain.upper()}",
        f"TARGET AUDIENCE: {ctx.parameters.audience.upper()} | LANGUAGE: {ctx.parameters.language}",
        "",
        "1. EXECUTIVE DIRECTIVE & CONTEXT",
        f"This advisory conveys verified information concerning {ctx.topic}. "
        "Use the verified findings below as the basis for review; this draft does not replace direction "
        "from the responsible authority.",
        "",
        "2. VERIFIED FACTUAL FINDINGS",
    ]

    for i, fact in enumerate(key_points, 1):
        body_sections.append(f"  2.{i} {fact}")

    if ctx.entities:
        body_sections.extend([
            "",
            "3. IDENTIFIED ENTITIES & SCOPE",
            f"Key entities and stakeholders referenced: {', '.join(ctx.entities[:6])}."
        ])

    body_sections.extend([
        "",
        "4. REQUIRED ACTIONS & MITIGATION",
        "- Confirm any response decisions with the responsible authority.",
        "- Follow the procedures applicable to the situation described in the source.",
        "- Share updates through approved channels if further communication is required.",
        "",
        "5. SOURCE GROUNDING NOTICE",
        "The factual findings above are limited to the analyzed source. The procedural suggestions are "
        "general editorial prompts and are not findings from the source."
    ])

    return GenerateOutputItem(
        output_type="advisory",
        title=title,
        summary=summary,
        key_points=key_points,
        body="\n".join(body_sections),
    )
