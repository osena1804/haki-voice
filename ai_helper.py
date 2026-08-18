import os
import json
from dotenv import load_dotenv
load_dotenv()
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def load_statutes(country_code="kenya"):
    with open(f"statutes/{country_code}.json", "r") as f:
        return json.load(f)

def get_ai_guidance(category, user_issue, country_code="kenya"):
    statutes = load_statutes(country_code)
    statute_info = statutes.get(category)

    if not statute_info:
        return None

    prompt = f"""You are a legal information assistant for HakiVoice, a service helping people understand their basic legal rights in Kenya.

Relevant law: {statute_info['law']}
Relevant excerpt: {statute_info['excerpt']}

A user described their situation as: "{user_issue}"

Write a short, plain-language SMS (maximum 300 characters) explaining what this specific law means for their situation. Be clear and practical. Do NOT give definitive legal conclusions or tell them they will win or lose - only explain their general rights and suggest they consult a legal aid worker for their specific case. End with: "This is general guidance, not legal advice."
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"AI guidance failed: {e}")
        return None