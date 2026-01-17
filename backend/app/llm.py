import os
import json
import re
from dotenv import load_dotenv
from google import genai
from backend.app.flags import FLAGS
from backend.app.weights import FLAG_WEIGHTS

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

def calculate_scores(findings: dict) -> dict:
    """
    Calculates the overall score and category scores based on flag weights.
    """
    category_scores = {}
    overall_score = 0
    total_weight = 0

    for flag, finding in findings.items():
        weight = FLAG_WEIGHTS.get(flag, 0)  # Default to 0 if flag not found
        status = finding['status']
        confidence = finding['confidence']

        # Score logic
        if status == "true":
            overall_score += weight
        elif status == "unknown":
            overall_score += weight * 0.5  # Less weight for unknown flags

        # Update category scores
        category = FLAGS.get(flag, {}).get('category', 'unknown')
        if category not in category_scores:
            category_scores[category] = 0
        category_scores[category] += weight * confidence

        total_weight += weight

    # Normalize the overall score
    overall_score = (overall_score / total_weight) * 100 if total_weight else 0
    return {"overall_score": overall_score, "category_scores": category_scores}

def call_llm_extract(policy_text: str) -> dict:
    model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    # Construct the prompt that explicitly asks Gemini to return one finding per flag
    prompt = f"""
    You are analyzing a privacy policy. For each of the following flags, return a JSON object that matches this format exactly:

    {{
        "flag": "<flag_id>",          # the unique identifier for the flag
        "label": "<flag_label>",      # a human-readable label for the flag
        "category": "<category_name>", # the category this flag belongs to (e.g., data_collection, legal)
        "status": "true"|"false"|"unknown",  # the status of the flag
        "confidence": <confidence_score>,   # a number between 0 and 1 indicating the confidence level
        "evidence_quote": "<text_from_policy>" # the specific excerpt from the policy supporting this flag
    }}

    Make sure the following rules are strictly followed:
    1. Return **only** valid JSON, **no markdown**, **no extra explanation** or comments.
    2. Include **all flags** even if the model doesn't mention them explicitly. For flags not found in the policy text, return `"status": "unknown"`, `"confidence": 0.5`, and an empty `evidence_quote`.
    3. Ensure that each flag has the exact format specified above.
    4. Always return flags in this exact structure, maintaining the order given in the list of flags.

    The flags are as follows:
    {json.dumps(FLAGS, indent=2)}  # List of all flags and their corresponding labels

    Policy text:
    {policy_text}
    """


    try:
        # Call Gemini with the constructed prompt
        resp = client.models.generate_content(
            model=model,
            contents=prompt
        )

        # Extract the response JSON
        findings = _extract_json(resp.text)

        # Calculate scores based on the findings
        scores = calculate_scores(findings)

        # Include the scores with the findings
        return {**findings, **scores}

    except Exception as e:
        return {"error": str(e)}  # In case of any failure, return error details

def normalize_flags(response: dict) -> dict:
    """
    Ensures all flags are included in the response and each flag has the correct format.
    """
    normalized_response = {
        "overall_score": response.get("overall_score", 0),
        "category_scores": response.get("category_scores", {}),
        "findings": []
    }

    for category, flags in FLAGS.items():
        for flag, label in flags.items():
            # Check if the flag is present, if not, initialize it
            flag_data = next((item for item in response["findings"] if item["flag"] == flag), None)
            if flag_data is None:
                flag_data = {
                    "flag": flag,
                    "label": label,
                    "category": category,
                    "status": "unknown",
                    "confidence": 0.5,
                    "evidence_quote": ""
                }
            normalized_response["findings"].append(flag_data)

    return normalized_response
