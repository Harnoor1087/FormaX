from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem

def generate_linkedin_post(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates a professional LinkedIn post with narrative hook, bullet points, and hashtags.
    """
    title = f"Insight Briefing: {ctx.topic}"
    summary = f"Professional leadership overview on {ctx.topic} tailored for {ctx.parameters.audience}."
    
    key_points = ctx.key_facts[:4]

    # Hashtags derived from domain and topic
    domain_tag = ctx.domain.replace(" ", "").replace("&", "")
    hashtags = f"#{domain_tag} #FormaXAI"

    body_lines = [
        f"Operational Update: {ctx.topic}",
        "",
        f"Here are the source-based facts related to {ctx.topic}:",
        "",
    ]

    for pt in key_points:
        body_lines.append(f"📌 {pt}")

    body_lines.extend([
        "",
        "💡 Key Takeaway:",
        f"Review these findings in the context of applicable procedures. Assessed urgency: {ctx.urgency}.",
        "",
        "Confirm any response decisions with the responsible authority.",
        "",
        hashtags
    ])

    return GenerateOutputItem(
        output_type="linkedin_post",
        title=title,
        summary=summary,
        key_points=key_points,
        body="\n".join(body_lines),
    )

def generate_twitter_thread(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates a structured, numbered Twitter / X thread (Synopsis Section 1.1).
    """
    facts = ctx.key_facts[:3]
    total_tweets = len(facts) + 2
    title = f"X/Twitter Thread: {ctx.topic}"
    summary = f"A {total_tweets}-part Twitter/X thread communicating {ctx.urgency} developments."

    thread_parts = [
        f"1/{total_tweets} 🧵 OPERATIONAL UPDATE: {ctx.topic}\n\nVerified source facts follow. 👇",
    ]

    for i, fact in enumerate(facts, 2):
        thread_parts.append(
            f"{i}/{total_tweets} Key Fact:\n{fact}"
        )

    thread_parts.append(
        f"{total_tweets}/{total_tweets} Summary:\nReview the findings and confirm any response with the responsible authority."
        f"\n\nFollow official channels for verified updates. #Update #{ctx.domain.replace(' ', '')}"
    )

    return GenerateOutputItem(
        output_type="twitter_thread",
        title=title,
        summary=summary,
        key_points=facts,
        body="\n\n---\n\n".join(thread_parts),
    )
