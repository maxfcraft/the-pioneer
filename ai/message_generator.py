"""
Uses Claude to generate human-sounding, city-personalized messages.
The goal: sound like a local Auburn student, not a bot.
"""

import anthropic
import os
from typing import Optional


client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

WHOP_LINK = os.getenv("WHOP_LINK", "https://whop.com/joined/auburnblueprint/")


def generate_group_post(city: str, state: str, high_schools: list[str], group_name: str) -> str:
    """Generate a personalized group post for a specific city's Auburn group."""
    schools_str = ", ".join(high_schools[:3])  # Use top 3 schools to keep it natural

    prompt = f"""You are Max, a freshman at Auburn University. You're posting in a Facebook group called "{group_name}" which is full of parents and students from {city}, {state} who are going to Auburn.

Write a casual, friendly Facebook group post (NOT a sales pitch) that:
1. Opens with something local/specific to {city} (mention 1-2 of these high schools if relevant: {schools_str})
2. Talks about how confusing Auburn was at first — Camp War Eagle, building a schedule, housing, Tiger Transit, football tickets
3. Mentions you put together a guide/resource that helped you figure it all out
4. Drops the link naturally: {WHOP_LINK}
5. Ends warmly, War Eagle style

Rules:
- Max 200 words
- Sound like a real 18-year-old, not a marketer
- No bullet points or lists — just natural paragraphs
- Don't say "I'm selling" — say "I put this together" or "I made this"
- Must feel LOCAL to {city}, not generic
- No emojis except War Eagle at the end is fine

Write the post now:"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_dm_response(incoming_message: str, stage: int = 1) -> str:
    """
    Generate a DM response to someone who replied to a post.
    stage 1 = first reply (warm, helpful)
    stage 2 = follow-up if no purchase (nudge with value)
    stage 3 = final follow-up (urgency/social proof)
    """
    stages = {
        1: f"""Someone messaged you on Facebook after seeing your Auburn Blueprint post. Their message: "{incoming_message}"

You are Max, an Auburn freshman. Reply warmly and helpfully.
- Answer their question briefly if they asked one
- Tell them the guide covers exactly what they're worried about
- Drop the link: {WHOP_LINK}
- Keep it under 80 words, conversational, no lists
- End with War Eagle or something friendly""",

        2: f"""Someone messaged you earlier about your Auburn Blueprint but hasn't bought yet. Their last message: "{incoming_message}"

Follow up naturally. Mention:
- One specific thing they'll learn (Camp War Eagle prep, or building a schedule, or housing)
- It's only $50 one-time, no subscription
- Link: {WHOP_LINK}
- Under 70 words, casual tone""",

        3: f"""Final follow-up to someone who showed interest in Auburn Blueprint. Their message was: "{incoming_message}"

Create light urgency — mention other Auburn students are already using it, they're heading into Camp War Eagle soon and want to be prepared. Link: {WHOP_LINK}. Under 60 words.""",
    }

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": stages.get(stage, stages[1])}],
    )
    return message.content[0].text.strip()


def generate_marketplace_description() -> str:
    """Generate a fresh marketplace listing description."""
    prompt = f"""Write a Facebook Marketplace listing for "The Auburn Blueprint" — a $50 course/guide for incoming Auburn University freshmen and their parents.

Cover:
- Camp War Eagle guide
- Building the perfect schedule (Tiger Scheduler + Rate My Professor)
- Tiger Transit / transportation
- On-campus and off-campus housing
- Football tickets

Link: {WHOP_LINK}

Rules:
- Sound like a real student wrote it, not corporate
- Under 200 words
- No bullet lists — flowing paragraphs
- Include "War Eagle" naturally
- Make parents feel this is exactly what they've been looking for"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
