import os
import json
import re
from dotenv import load_dotenv
import openrouter  # Import OpenRouter
from backend.app.flags import FLAGS
from backend.app.weights import FLAG_WEIGHTS

load_dotenv()

# Fetch the OpenRouter API Key from the environment
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise ValueError("Missing OPENROUTER_API_KEY in .env")

# Initialize the OpenRouter API configuration using the OpenRouter class
openrouter.api_key = API_KEY  # Set API key directly in OpenRouter

def _extract_json(text: str) -> dict:
    """
    Extracts the first valid JSON block, ignoring extra metadata like `thought_signature`.
    """
    try:
        # Search for valid JSON block within the text (look for { ... })
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            # Return the first valid JSON block found
            return json.loads(m.group(0))
        else:
            raise ValueError(f"No valid JSON found in the response: {text[:400]}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode JSON response: {str(e)}")


def calculate_scores(findings: dict) -> dict:
    """
    Calculates the overall score and category scores based on flag weights.
    """
    category_scores = {category: 0 for category in FLAGS.keys()}  # Initialize category scores
    overall_score = 0
    total_weight = 0

    for finding in findings:
        flag = finding['flag']
        status = finding['status']
        confidence = finding['confidence']

        # Retrieve the flag weight from FLAG_WEIGHTS (default to 0 if flag not found)
        weight = FLAG_WEIGHTS.get(flag, 0)

        # Score logic
        if status == "true":
            overall_score += weight
        elif status == "unknown":
            overall_score += weight * 0.5  # Less weight for unknown flags

        # Update category scores
        category = FLAGS.get(finding['category'], {}).get('category', 'unknown')
        if category not in category_scores:
            category_scores[category] = 0
        category_scores[category] += weight * confidence

        total_weight += weight

    # Normalize the overall score
    overall_score = (overall_score / total_weight) * 100 if total_weight else 0
    return {"overall_score": overall_score, "category_scores": category_scores}


def clean_response(text: str) -> str:
    """
    This function removes non-JSON parts (such as `thought_signature`) from the response.
    """
    # Example regex to remove unwanted text (you may need to adapt this to the actual structure)
    response_clean = re.sub(r'"thought_signature":\s*"[^"]+"', '', text)  # Remove `thought_signature`
    return response_clean


def call_llm_extract(policy_text: str) -> dict:
    model = os.getenv("OPENROUTER_MODEL", "openrouter-1")

    # Construct the prompt that explicitly asks OpenRouter to return only valid JSON
    prompt = f"""
    You are analyzing a privacy policy. Your task is to return **only valid JSON** with the exact structure specified below. Do **not** include any markdown, backticks, explanations, or non-JSON content such as metadata or thought signatures. Only return the JSON object in the following format:

    {{
        "flag": "<flag_id>",         # The unique identifier for the flag
        "label": "<flag_label>",     # A human-readable label for the flag
        "category": "<category_name>", # The category this flag belongs to (e.g., data_collection, legal)
        "status": "true"|"false"|"unknown", # The status of the flag
        "confidence": <confidence_score>,   # A number between 0 and 1 indicating the confidence level
        "evidence_quote": "<text_from_policy>" # The specific excerpt from the policy supporting this flag
    }}

    - **Do not add any extra text**. Only return **valid JSON**. No explanations or additional parts.
    - For **flags not found** in the policy text, return the flag with `"status": "unknown"`, `"confidence": 0.5`, and an empty `"evidence_quote"`.
    - **Do not return any metadata** or extra information like "thought_signature."

    The flags are as follows:
    {json.dumps(FLAGS, indent=2)}  # List of all flags and their corresponding labels

    Policy text:
    {policy_text}
    """

    try:
        # Use the OpenRouter class to interact with the API
        openrouter_instance = openrouter.OpenRouter(api_key=API_KEY)  # Initialize OpenRouter instance
        response = openrouter_instance.completion.create(  # Corrected method
            model=model,
            prompt=prompt,
            max_tokens=1500  # Adjust the number of tokens as needed
        )

        # Log the raw response to check for unexpected text
        print("Raw Response from OpenRouter:", response)

        # Clean the response to remove non-JSON parts (like 'thought_signature')
        response_clean = clean_response(response['choices'][0]['message']['content'])

        # Extract the response JSON
        findings = _extract_json(response_clean)

        # Ensure 'findings' is part of the response
        if 'findings' not in findings:
            print(f"API Response (Missing findings): {response['choices'][0]['message']['content']}")
            raise ValueError("'findings' not found in the API response.")

        # Calculate scores based on the findings
        scores = calculate_scores(findings)

        # Include the scores with the findings
        return {**findings, **scores}

    except Exception as e:
        print("Error during analysis:", str(e))  # Print the error for debugging
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
        for flag, flag_data in flags.items():
            # Check if the flag is present, if not, initialize it
            flag_data_in_response = next((item for item in response["findings"] if item["flag"] == flag), None)
            if flag_data_in_response is None:
                # Flag not found, initialize with defaults
                flag_data_in_response = {
                    "flag": flag,
                    "label": flag_data["label"],  # Use the label from the updated FLAGS.py
                    "category": category,
                    "status": "unknown",
                    "confidence": 0.5,
                    "evidence_quote": ""
                }
            normalized_response["findings"].append(flag_data_in_response)

    return normalized_response
