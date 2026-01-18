import os
import json
import re
import hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Direct imports
from flags import FLAGS
from weights import FLAG_WEIGHTS

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("Warning: Missing GEMINI_API_KEY")

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None

MAX_RISK_BASELINE = 75 

# --- LAYER 1: MEMORY CACHE ---
# Stores results so identical requests are instant and 100% consistent.
RESULT_CACHE = {}

def get_flat_flags():
    """Flatten the FLAGS dict into a single map of ID -> Label"""
    flat = {}
    for category, items in FLAGS.items():
        for k, v in items.items():
            flat[k] = v
    return flat

FLAT_FLAGS = get_flat_flags()
ALL_FLAG_KEYS = list(FLAT_FLAGS.keys())

# --- DEFINITIONS & NEGATIVE CONSTRAINTS ---
DEFINITIONS = {
    "uses_cookies": "Mentions 'cookies', 'pixels', 'web beacons'. IGNORE: 'cookie-cutter' or food.",
    "collects_location": "Mentions 'GPS', 'lat/long', 'physical address'. IGNORE: 'IP address' (that is separate).",
    "collects_ip_address": "Explicitly mentions collecting 'IP address'.",
    "collects_device_info": "Mentions 'device ID', 'MAC address', 'browser type'.",
    "shares_for_advertising": "Mentions sharing with 'ad partners', 'marketing partners'. IGNORE: Internal marketing.",
    "uses_targeted_ads": "Mentions 'interest-based ads', 'profiling'. IGNORE: Contextual ads.",
    "uses_cross_site_tracking": "Mentions 'tracking across other websites', 'third-party cookies'.",
    "sells_user_data": "Explicitly mentions 'selling' data. IF TEXT SAYS 'WE DO NOT SELL', THIS IS FALSE.",
    "shares_with_data_brokers": "Mentions 'data brokers', 'aggregators'.",
    "indefinite_data_retention": "Says data is kept 'indefinitely' or 'as long as necessary' with NO specific timeframe.",
    "waives_rights": "Mentions 'class action waiver', 'jury trial waiver'. IGNORE: General 'legal rights'.",
    "collects_children_data": "Mentions collecting data from children under 13/16. IF TEXT SAYS 'WE DO NOT knowingly collect', THIS IS FALSE.",
}

# --- LAYER 2: REGEX GUARDRAILS ---
# If these keywords are NOT present, the flag is FORCED to False.
GUARDRAILS = {
    "sells_user_data": [r"sell", r"sold", r"rent", r"monetary", r"consideration", r"exchange"],
    "collects_biometrics": [r"biometric", r"face", r"facial", r"fingerprint", r"voice", r"retina", r"iris"],
    "shares_health_data": [r"health", r"medical", r"treatment", r"doctor", r"hospital", r"patient"],
    "waives_rights": [r"class action", r"jury", r"arbitration", r"waive", r"dispute"],
    "shares_with_data_brokers": [r"broker", r"aggregator", r"syndicate", r"cooperative"],
    "uses_cross_site_tracking": [r"track", r"cross-site", r"third-party cookie", r"pixel", r"beacon", r"replay"],
}

def passes_guardrails(flag_id, text):
    if flag_id not in GUARDRAILS: return True 
    keywords = GUARDRAILS[flag_id]
    text_lower = text.lower()
    for word in keywords:
        if re.search(word, text_lower): return True
    return False

def get_category_for_flag(flag_id):
    for cat, items in FLAGS.items():
        if flag_id in items: return cat
    return "general"

def calculate_scores(findings: list) -> dict:
    category_scores = {category: 0 for category in FLAGS.keys()}
    overall_score = 0
    for finding in findings:
        flag = finding.get('flag')
        status = finding.get('status')
        confidence = finding.get('confidence', 1.0) 
        category_key = finding.get('category')

        if flag not in FLAG_WEIGHTS: continue
        weight = FLAG_WEIGHTS.get(flag, 0)

        if status == "true":
            score_impact = weight * confidence
            overall_score += score_impact
            if category_key and category_key in category_scores:
                category_scores[category_key] += score_impact

    raw_score = (overall_score / MAX_RISK_BASELINE) * 100
    final_score = min(raw_score, 100)
    return {"overall_score": round(final_score, 2), "category_scores": category_scores}

def convert_map_to_list(data_map, source_text):
    clean_findings = []
    for flag_id, result in data_map.items():
        if flag_id not in FLAT_FLAGS: continue

        is_present = result.get("present", False)
        quote = result.get("evidence", "")

        # Strict Evidence Check
        if is_present:
            if not quote or len(quote) < 10 or len(quote.split()) < 3:
                is_present = False

        # Guardrail Check
        if is_present and not passes_guardrails(flag_id, source_text):
            is_present = False

        if is_present:
            clean_findings.append({
                "flag": flag_id,
                "label": FLAT_FLAGS[flag_id],
                "category": get_category_for_flag(flag_id),
                "status": "true",
                "confidence": 1.0,
                "evidence_quote": quote
            })
    return clean_findings

# --- LAYER 3: NOISE CLEANER ---
# Removes junk so the AI (and Guardrails) don't get confused by footers.
def clean_noise(text: str) -> str:
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Remove navigation/menu lines
        if len(stripped) < 40 and ("Home" in stripped or "About" in stripped or "Contact" in stripped or "Login" in stripped):
            continue
        # Remove copyright/footer junk
        if "rights reserved" in stripped.lower() or "copyright" in stripped.lower() or "©" in stripped:
            continue
        if not stripped:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


# --- SINGLE ANALYSIS ---
def call_llm_extract(policy_text: str) -> dict:
    if not client: return {"error": "API Key missing"}
    
    clean_text = clean_noise(policy_text)

    # Cache Check
    # text_hash = hashlib.md5(clean_text.encode('utf-8')).hexdigest()
    # if text_hash in RESULT_CACHE:
    #     print("✅ Cache Hit (Single)")
    #     return RESULT_CACHE[text_hash]

    return _internal_analyze_strict(clean_text, text_hash)

def _internal_analyze_strict(policy_text, cache_key=None):
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash") 
    
    properties = {}
    for flag_id in ALL_FLAG_KEYS:
        properties[flag_id] = {
            "type": "object",
            "properties": {"present": {"type": "boolean"}, "evidence": {"type": "string"}},
            "required": ["present"]
        }

    config = types.GenerateContentConfig(
        temperature=0.0,
        top_k=1, # DETERMINISTIC
        response_mime_type="application/json",
        response_schema={
            "type": "object", 
            "properties": properties, 
            "required": ALL_FLAG_KEYS 
        }
    )
    
    prompt = f"""
    Analyze the LEGAL TEXT below. 
    IGNORE any website navigation, footers, or marketing text. Focus ONLY on the privacy policy clauses.
    
    Definitions: {json.dumps(DEFINITIONS)}
    
    Text: 
    {policy_text[:70000]}
    """
    
    try:
        resp = client.models.generate_content(model=model, contents=prompt, config=config)
        data = json.loads(resp.text)
        findings = convert_map_to_list(data, policy_text)
        result = {"findings": findings, **calculate_scores(findings)}
        if cache_key: RESULT_CACHE[cache_key] = result
        return result
    except Exception as e:
        return {"findings": [], "overall_score": 0, "category_scores": {}, "error": str(e)}


# --- SINGLE PASS COMPARISON ---
def call_llm_compare_side_by_side(text_a: str, text_b: str) -> dict:
    if not client: return {"error": "API Key missing"}

    clean_a = clean_noise(text_a)
    clean_b = clean_noise(text_b)

    # # 1. Cache Check (Combined Hash)
    # combined_hash = hashlib.md5((clean_a + clean_b).encode('utf-8')).hexdigest()
    # if combined_hash in RESULT_CACHE:
    #     print("✅ Cache Hit (Comparison)")
    #     return RESULT_CACHE[combined_hash]

    # 2. Setup AI
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash") 

    single_policy_schema = {}
    for flag_id in ALL_FLAG_KEYS:
        single_policy_schema[flag_id] = {
            "type": "object",
            "properties": {
                "present": {"type": "boolean"}, 
                "evidence": {"type": "string"}
            },
            "required": ["present"]
        }

    comparison_schema = {
        "type": "object",
        "properties": {
            "policy_A": {
                "type": "object", 
                "properties": single_policy_schema, 
                "required": ALL_FLAG_KEYS
            },
            "policy_B": {
                "type": "object", 
                "properties": single_policy_schema, 
                "required": ALL_FLAG_KEYS
            }
        },
        "required": ["policy_A", "policy_B"]
    }

    config = types.GenerateContentConfig(
        temperature=0.0,
        top_k=1, # DETERMINISTIC
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=comparison_schema
    )

    prompt = f"""
    You are an impartial legal judge. Compare these two privacy policies side-by-side.
    
    INSTRUCTIONS:
    1. IGNORE website noise (headers, footers, navigation menus).
    2. Focus ONLY on the legal clauses.
    3. Consistency is CRITICAL. If A and B contain similar text, their flags MUST match.
    
    DEFINITIONS:
    {json.dumps(DEFINITIONS, indent=2)}

    ----- POLICY A START -----
    {clean_a[:40000]}
    ----- POLICY A END -----

    ----- POLICY B START -----
    {clean_b[:40000]}
    ----- POLICY B END -----
    """

    try:
        response = client.models.generate_content(
            model=model, 
            contents=prompt,
            config=config
        )
        
        data = json.loads(response.text)
        
        raw_a = data.get("policy_A", {})
        raw_b = data.get("policy_B", {})

        findings_a = convert_map_to_list(raw_a, clean_a)
        findings_b = convert_map_to_list(raw_b, clean_b)

        report_a = {"findings": findings_a, **calculate_scores(findings_a)}
        report_b = {"findings": findings_b, **calculate_scores(findings_b)}

        result = {
            "reportA": report_a,
            "reportB": report_b
        }

        RESULT_CACHE[combined_hash] = result
        return result

    except Exception as e:
        print(f"Comparison Error: {str(e)}")
        return {
            "reportA": {"findings": [], "overall_score": 0, "category_scores": {}},
            "reportB": {"findings": [], "overall_score": 0, "category_scores": {}},
            "error": str(e)
        }