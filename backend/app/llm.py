import os, json, re, hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import types
from flags import FLAGS
from weights import FLAG_WEIGHTS

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
RESULT_CACHE = {}

def get_flat_flags():
    flat = {}
    for category in FLAGS.values():
        flat.update(category)
    return flat

FLAT_FLAGS = get_flat_flags()
ALL_FLAG_KEYS = list(FLAT_FLAGS.keys())

DEFINITIONS = {
    "uses_cookies": "Mentions 'cookies', 'pixels', 'web beacons'.",
    "collects_location": "Mentions 'GPS', 'lat/long', 'physical address'.",
    "collects_ip_address": "Explicitly mentions collecting 'IP address'.",
    "collects_device_info": "Mentions 'device ID', 'MAC address', 'browser type'.",
    "shares_for_advertising": "Mentions sharing with 'ad partners', 'marketing partners'.",
    "uses_targeted_ads": "Mentions 'interest-based ads', 'profiling'.",
    "uses_cross_site_tracking": "Mentions 'tracking across other websites', 'third-party cookies'.",
    "sells_user_data": "Explicitly mentions 'selling' data.",
    "shares_with_data_brokers": "Mentions 'data brokers', 'aggregators'.",
    "indefinite_data_retention": "Says data is kept 'indefinitely' or 'as long as necessary'.",
    "waives_rights": "Mentions 'class action waiver', 'jury trial waiver'.",
    "collects_children_data": "Mentions collecting data from children under 13/16.",
}

def calculate_scores(findings: list) -> dict:
    overall_score = 0
    for finding in findings:
        if finding['status'] == "true":
            overall_score += FLAG_WEIGHTS.get(finding['flag'], 0)
    final_score = min((overall_score / 75) * 100, 100)
    return {"overall_score": round(final_score, 2)}

def convert_map_to_list(data_map, source_text):
    clean_findings = []
    for flag_id, result in data_map.items():
        if result.get("present"):
            clean_findings.append({
                "flag": flag_id,
                "label": FLAT_FLAGS.get(flag_id, flag_id),
                "status": "true",
                "evidence_quote": result.get("evidence", "")
            })
    return clean_findings

def clean_noise(text: str) -> str:
    return "\n".join([line for line in text.split('\n') if len(line.strip()) > 40])

def call_llm_extract(policy_text: str) -> dict:
    clean_text = clean_noise(policy_text)
    text_hash = hashlib.md5(clean_text.encode('utf-8')).hexdigest()
    if text_hash in RESULT_CACHE: return RESULT_CACHE[text_hash]
    return _internal_analyze_strict(clean_text, text_hash)

def _internal_analyze_strict(policy_text, cache_key=None):
    model = "gemini-2.0-flash"
    properties = {fid: {"type": "object", "properties": {"present": {"type": "boolean"}, "evidence": {"type": "string"}}, "required": ["present"]} for fid in ALL_FLAG_KEYS}
    config = types.GenerateContentConfig(temperature=0.0, top_k=1, response_mime_type="application/json", response_schema={"type": "object", "properties": properties, "required": ALL_FLAG_KEYS})
    prompt = f"Analyze legal text. Definitions: {json.dumps(DEFINITIONS)}\n\nText:\n{policy_text[:70000]}"
    try:
        resp = client.models.generate_content(model=model, contents=prompt, config=config)
        data = json.loads(resp.text)
        findings = convert_map_to_list(data, policy_text)
        result = {"findings": findings, **calculate_scores(findings)}
        if cache_key: RESULT_CACHE[cache_key] = result
        return result
    except: return {"findings": [], "overall_score": 0}

def call_llm_compare_side_by_side(text_a: str, text_b: str) -> dict:
    clean_a, clean_b = clean_noise(text_a), clean_noise(text_b)
    combined_hash = hashlib.md5((clean_a + clean_b).encode('utf-8')).hexdigest()
    if combined_hash in RESULT_CACHE: return RESULT_CACHE[combined_hash]
    
    single_schema = {fid: {"type": "object", "properties": {"present": {"type": "boolean"}, "evidence": {"type": "string"}}, "required": ["present"]} for fid in ALL_FLAG_KEYS}
    config = types.GenerateContentConfig(temperature=0.0, top_k=1, response_mime_type="application/json", response_schema={"type": "object", "properties": {"policy_A": {"type": "object", "properties": single_schema, "required": ALL_FLAG_KEYS}, "policy_B": {"type": "object", "properties": single_schema, "required": ALL_FLAG_KEYS}}, "required": ["policy_A", "policy_B"]})
    prompt = f"Compare policies. Definitions: {json.dumps(DEFINITIONS)}\n\nA:\n{clean_a[:35000]}\n\nB:\n{clean_b[:35000]}"
    try:
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config=config)
        data = json.loads(resp.text)
        report_a = {"findings": convert_map_to_list(data["policy_A"], clean_a), **calculate_scores(convert_map_to_list(data["policy_A"], clean_a))}
        report_b = {"findings": convert_map_to_list(data["policy_B"], clean_b), **calculate_scores(convert_map_to_list(data["policy_B"], clean_b))}
        result = {"reportA": report_a, "reportB": report_b}
        RESULT_CACHE[combined_hash] = result
        return result
    except: return {"reportA": {"findings": [], "overall_score": 0}, "reportB": {"findings": [], "overall_score": 0}}