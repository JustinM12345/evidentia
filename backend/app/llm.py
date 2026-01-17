import os
import json
import re
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY) in .env")

client = genai.Client(api_key=API_KEY)

def _extract_json(text: str) -> dict:
    """
    Gemini sometimes wraps JSON in extra text. This pulls the first {...} block.
    """
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No JSON found in model response: {text[:400]}")
    return json.loads(m.group(0))

def call_llm_extract(policy_text: str) -> dict:
    model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    prompt = f"""
Return ONLY valid JSON (no markdown, no backticks) with this shape:
{{
  "overall_score": number,
  "category_scores": {{}},
  "findings": [
    {{
      "flag": string,
      "label": string,
      "category": string,
      "status": "true"|"false"|"unknown",
      "confidence": number,
      "evidence_quote": string
    }}
  ]
}}

Policy text:
{policy_text}
""".strip()

    resp = client.models.generate_content(
        model=model,
        contents=prompt
    )

    return _extract_json(resp.text)
