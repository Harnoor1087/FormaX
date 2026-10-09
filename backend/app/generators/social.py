from ..schemas.context import StructuredContext
from ..schemas.response import GenerateOutputItem

def generate_linkedin_post(ctx: StructuredContext) -> GenerateOutputItem:
    """
    Generates a professional LinkedIn post with narrative hook, bullet points, and hashtags.
    """
    title = f"Insight Briefing: {ctx.topic[:70]}"
    summary = f"Professional leadership overview on {ctx.topic} tailored for {ctx.parameters.audience}."
    
    key_points = ctx.key_facts[:4] if ctx.key_facts else ["Key developments noted in source."]

    # Hashtags derived from domain and topic
    domain_tag = ctx.domain.replace(" ", "").replace("&", "")
    hashtags = f"#{domain_tag} #Operations #Strategy #FormaXAI"

    body_lines = [
        f"🚨 Operational Update: {ctx.topic}",
        "",
        f"As leaders and teams navigate evolving developments in {ctx.domain.lower()}, here are the core facts you need to know today:",
        "",
    ]

    for pt in key_points:
        body_lines.append(f"📌 {pt}")

    body_lines.extend([
        "",
        "💡 Key Takeaway:",
        f"Maintaining clear alignment and factual consistency across all channels is critical when handling {ctx.urgency}-priority situations.",
        "",
        "What are your teams implementing to stay ahead of these challenges? Join the discussion below.",
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
    title = f"X/Twitter Thread: {ctx.topic[:60]}"
    summary = f"A {len(ctx.key_facts) + 2}-part Twitter/X thread communicating {ctx.urgency} developments."
    
    facts = ctx.key_facts[:3] if ctx.key_facts else ["Key operational fact."]
    total_tweets = len(facts) + 2

    thread_parts = [
        f"1/{total_tweets} 🧵 CRITICAL UPDATE: {ctx.topic}\n\nHere is what you need to know based on verified source documentation. 👇",
    ]

    for i, fact in enumerate(facts, 2):
        thread_parts.append(
            f"{i}/{total_tweets} Key Fact:\n{fact}"
        )

    action_text = "Ensure verified protocols are activated." if ctx.urgency in ["high", "critical"] else "Review details via standard channels."
    thread_parts.append(
        f"{total_tweets}/{total_tweets} Summary:\n{action_text}\n\nStay tuned for official updates. #Update #{ctx.domain.replace(' ', '')}"
    )

    return GenerateOutputItem(
        output_type="twitter_thread",
        title=title,
        summary=summary,
        key_points=facts,
        body="\n\n---\n\n".join(thread_parts),
    )
