import os
import json
import re
from dotenv import load_dotenv
from google import genai
# Keep your working imports
from backend.app.flags import FLAGS
from backend.app.weights import FLAG_WEIGHTS

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY) in .env")

client = genai.Client(api_key=API_KEY)

# 1. PRE-CALCULATE THE MAX SCORE (Sum of all possible bad weights)
# This fixes the "50% score" bug. Now, 0 findings = 0/100 score.
TOTAL_POSSIBLE_SCORE = sum(FLAG_WEIGHTS.values())

def get_valid_flags():
    valid_ids = []
    for category, flags in FLAGS.items():
        valid_ids.extend(flags.keys())
    return valid_ids

VALID_FLAG_IDS = get_valid_flags()


def _extract_json(text: str) -> dict:
    try:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m: return json.loads(m.group(0))
        m_list = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if m_list: return {"findings": json.loads(m_list.group(0))}
        raise ValueError("No valid JSON found")
    except Exception as e:
        raise ValueError(f"JSON Decode Error: {str(e)}")


def calculate_scores(findings: list) -> dict:
    category_scores = {category: 0 for category in FLAGS.keys()}
    overall_score = 0
    
    # We no longer track "total_weight" of findings. 
    # We compare against the TOTAL_POSSIBLE_SCORE of the entire system.

    for finding in findings:
        flag = finding.get('flag')
        status = finding.get('status')
        confidence = finding.get('confidence', 0)
        category_key = finding.get('category')

        if flag not in FLAG_WEIGHTS:
            continue

        weight = FLAG_WEIGHTS.get(flag, 0)

        # 2. SCORING LOGIC UPDATE
        if status == "true":
            # Full penalty for confirmed risks
            score_impact = weight * confidence
            overall_score += score_impact
            if category_key in category_scores:
                category_scores[category_key] += score_impact
                
        elif status == "unknown":
            # Reduced penalty (25%) for ambiguous text, instead of 50%
            # If it's not mentioned at all, the AI won't return it (status=false), so 0 penalty.
            score_impact = weight * 0.25
            overall_score += score_impact

    # 3. NORMALIZE SCORE
    # This prevents the score from spiking just because one small thing was found.
    # Score is now: (Risk Found / Total Possible Risk) * 100
    if TOTAL_POSSIBLE_SCORE > 0:
        final_score = (overall_score / TOTAL_POSSIBLE_SCORE) * 100
    else:
        final_score = 0
    
    return {
        "overall_score": round(final_score, 2), 
        "category_scores": category_scores
    }


def call_llm_extract(policy_text: str) -> dict:
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash") 

    # 4. PROMPT UPDATE: "Silence = Safe"
    prompt = f"""
    You are an expert legal AI. Analyze the following privacy policy text.
    
    Your Goal: Identify CONFIRMED risks from the valid list below.
    
    STRICT RULES:
    1. ONLY use flag IDs from this list: {json.dumps(VALID_FLAG_IDS)}
    2. If a flag is NOT explicitly mentioned in the text, assume it is FALSE.
    3. DO NOT return "false" flags in the JSON list. Only return "true" or "unknown".
    4. Only use "unknown" if the text is genuinely ambiguous or contradictory. If it's just missing, it is FALSE.

    Return a JSON object:
    {{
        "findings": [
            {{
                "flag": "<valid_id>",         
                "label": "<human_readable_label>",     
                "category": "<category_key>", 
                "status": "true" | "unknown", 
                "confidence": <float 0-1>,   
                "evidence_quote": "<quote>"
            }}
        ]
    }}
    
    Policy Text:
    {policy_text[:30000]} 
    """

    try:
        response = client.models.generate_content(model=model, contents=prompt)
        
        raw_text = response.text if hasattr(response, 'text') else str(response)
        cleaned_text = raw_text.replace("```json", "").replace("```", "")
        
        parsed_json = _extract_json(cleaned_text)
        findings_list = parsed_json.get("findings", [])
        
        if not findings_list and isinstance(parsed_json, list):
            findings_list = parsed_json

        scores = calculate_scores(findings_list)

        return {
            "findings": findings_list,
            **scores
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"findings": [], "overall_score": 0, "category_scores": {}, "error": str(e)}