import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types # Import types for explicit checking
from backend.app.flags import FLAGS
from backend.app.weights import FLAG_WEIGHTS

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY) in .env")

client = genai.Client(api_key=API_KEY)


def _extract_json(text: str) -> dict:
    """
    Extracts the first valid JSON block.
    """
    try:
        # Search for valid JSON block (looking for the outermost curly braces)
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        else:
            # Fallback: sometimes LLMs return just the list [ ... ]
            m_list = re.search(r"\[.*\]", text, flags=re.DOTALL)
            if m_list:
                return {"findings": json.loads(m_list.group(0))}
            
            raise ValueError(f"No valid JSON found in response: {text[:200]}...")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode JSON response: {str(e)}")


def calculate_scores(findings: list) -> dict:
    """
    Calculates the overall score and category scores based on flag weights.
    """
    category_scores = {category: 0 for category in FLAGS.keys()}
    overall_score = 0
    total_weight = 0

    for finding in findings:
        flag = finding.get('flag')
        status = finding.get('status')
        confidence = finding.get('confidence', 0)
        category_key = finding.get('category') # This should match keys in FLAGS

        # 1. Get weight
        weight = FLAG_WEIGHTS.get(flag, 0)

        # 2. Update Scores
        if status == "true":
            overall_score += weight
            # Only add to category score if we can map it back to a valid category
            if category_key in category_scores:
                category_scores[category_key] += weight * confidence
            
            total_weight += weight

        elif status == "unknown":
            overall_score += weight * 0.5
            total_weight += weight

    # Normalize
    final_score = (overall_score / total_weight) * 100 if total_weight > 0 else 0
    
    return {
        "overall_score": round(final_score, 2), 
        "category_scores": category_scores
    }


def clean_response(response_text):
    # Remove markdown code blocks if present
    cleaned = response_text.replace("```json", "").replace("```", "")
    # Remove thought signatures
    cleaned = re.sub(r'"thought_signature":\s*"[^"]+"', '', cleaned)
    return cleaned


def call_llm_extract(policy_text: str) -> dict:
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash") 

    # UPDATED PROMPT: Explicitly asking for a list wrapped in a "findings" key
    prompt = f"""
    You are an expert legal AI. Analyze the following privacy policy text.
    Identify relevant data collection, sharing, rights, and risk flags based on the text.

    Return a JSON object with a single key "findings" which contains a list of objects.
    
    The JSON structure must be exactly this:
    {{
        "findings": [
            {{
                "flag": "<exact_flag_id_from_known_list>",         
                "label": "<human_readable_label>",     
                "category": "<category_name>", 
                "status": "true" | "false" | "unknown", 
                "confidence": <float between 0 and 1>,   
                "evidence_quote": "<short quote verifying the finding>"
            }},
            ...
        ]
    }}

    IMPORTANT: 
    - Only output valid JSON. 
    - Do not include markdown formatting.
    - If a flag is not explicitly mentioned, mark status as "unknown" or "false".
    
    Policy Text:
    {policy_text[:30000]} 
    """

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )

        # Robust extraction of text
        if hasattr(response, 'text'):
            raw_text = response.text
        else:
            # Fallback for different SDK versions/response types
            print(f"Debug - Response Type: {type(response)}")
            raw_text = str(response)

        if not raw_text:
            raise ValueError("Empty response from Gemini.")

        cleaned_text = clean_response(raw_text)
        print("Cleaned Response Snippet:", cleaned_text[:200]) # Debug log

        # Parse JSON
        parsed_json = _extract_json(cleaned_text)

        # Normalization: Ensure we have a list of findings
        findings_list = parsed_json.get("findings", [])
        if not findings_list and isinstance(parsed_json, list):
            findings_list = parsed_json # specific fallback if AI returned just a list

        # Calculate scores
        scores = calculate_scores(findings_list)

        # Return combined dict
        return {
            "findings": findings_list,
            **scores
        }

    except Exception as e:
        print(f"Error in call_llm_extract: {str(e)}")
        # Return a safe empty structure so the frontend doesn't crash completely
        return {
            "findings": [],
            "overall_score": 0,
            "category_scores": {},
            "error": str(e)
        }