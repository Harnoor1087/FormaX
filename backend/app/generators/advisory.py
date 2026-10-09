from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem

def generate_advisory(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates a formal, structured institutional advisory (Synopsis Section 1.2 & 4).
    """
    urgency_tag = ctx.urgency.upper()
    title = f"SECURITY & OPERATIONAL ADVISORY: {ctx.topic[:70]}"
    
    summary = (
        f"Official operational advisory issued for {ctx.parameters.audience}. "
        f"Urgency assessment is {urgency_tag}. Immediate compliance and situational review recommended."
    )
    
    key_points = ctx.key_facts[:5] if ctx.key_facts else [
        "Situational facts extracted directly from verified source."
    ]

    body_sections = [
        f"ADVISORY CLASSIFICATION: {urgency_tag} | DOMAIN: {ctx.domain.upper()}",
        f"TARGET AUDIENCE: {ctx.parameters.audience.upper()} | LANGUAGE: {ctx.parameters.language}",
        "",
        "1. EXECUTIVE DIRECTIVE & CONTEXT",
        f"This advisory conveys verified information concerning {ctx.topic}. "
        f"Stakeholders must review the directives outlined below in accordance with operational protocol.",
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
        "- Verify perimeter status and notify internal coordination units.",
        "- Disseminate relevant warnings to impacted operations without delay.",
        "- Maintain continuous log monitoring and report anomalies through designated channels.",
        "",
        "5. SOURCE GROUNDING NOTICE",
        "All claims in this communication are strictly grounded in verified source content. "
        "Any unverified extrapolations have been omitted in compliance with FormaX AI governance standards."
    ])

    return GenerateOutputItem(
        output_type="advisory",
        title=title,
        summary=summary,
        key_points=key_points,
        body="\n".join(body_sections),
    )
