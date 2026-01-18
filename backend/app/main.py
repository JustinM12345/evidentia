import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware

# Direct import from your llm.py
from llm import call_llm_extract, call_llm_compare_side_by_side

app = FastAPI(title="Evidentia API")

# --- CORS SETTINGS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- YELLOWCAKE CONFIG ---
YELLOWCAKE_API_KEY = os.getenv("YELLOWCAKE_API_KEY") 
YELLOWCAKE_URL = "https://api.yellowcake.dev/v1/extract" 

class AnalyzeRequest(BaseModel):
    text: str
    url: Optional[str] = None

class CompareRequest(BaseModel):
    textA: str
    textB: str
    urlA: Optional[str] = None
    urlB: Optional[str] = None

@app.get("/api/health")
def health():
    return {"ok": True}

# --- HELPER: YELLOWCAKE FETCHER ---
def fetch_from_yellowcake(target_url: str) -> str:
    # ... (keep your existing header/payload setup) ...

    try:
        response = requests.post(YELLOWCAKE_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Yellowcake can return content in different fields depending on the site
            text = data.get("text") or data.get("content") or data.get("data") or ""
            
            # CRITICAL: Check for minimum length. 
            # Most policies are 2000+ chars. Anything under 500 is likely a "Blocked" page.
            if len(str(text).strip()) < 500:
                print(f"⚠️ Scraping failed: Text too short ({len(str(text))} chars)", flush=True)
                raise HTTPException(
                    status_code=422, # Unprocessable Entity
                    detail="The website blocked our scraper. Please copy and paste the text manually."
                )
            
            return str(text)
        else:
            # If we get a 403, 429, or 500 from Yellowcake
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Scraper error (Status {response.status_code}). Try manual copy-paste."
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")

# --- HELPER: ROBUST URL DETECTOR ---
def process_input(input_text: str) -> str:
    clean_input = input_text.strip()
    is_url = clean_input.lower().startswith(("http://", "https://"))
    has_spaces = " " in clean_input

    if is_url and not has_spaces:
        print("🚀 DETECTED URL -> Fetching content...", flush=True)
        result = fetch_from_yellowcake(clean_input)
        
        # NEW: Check if the result is an error message from our fetcher

        return result
    
    return input_text

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    final_text = process_input(req.text)
    
    llm_result = call_llm_extract(final_text)
    
    passed_url = req.text if req.text.startswith("http") else req.url
    llm_result["meta"] = {"url": passed_url}
    
    return llm_result

@app.post("/api/compare")
def compare(req: CompareRequest) -> Dict[str, Any]:
    print("\n--- NEW COMPARISON REQUEST ---", flush=True)
    processed_A = process_input(req.textA)
    processed_B = process_input(req.textB)
    
    comparison_result = call_llm_compare_side_by_side(processed_A, processed_B)
    
    reportA = comparison_result["reportA"]
    reportB = comparison_result["reportB"]
    
    findingsA = {f["flag"]: f for f in reportA["findings"]}
    findingsB = {f["flag"]: f for f in reportB["findings"]}
    
    common_risks = []
    unique_to_A = []
    unique_to_B = []

    all_flags = set(findingsA.keys()).union(set(findingsB.keys()))

    for flag_id in all_flags:
        fA = findingsA.get(flag_id)
        fB = findingsB.get(flag_id)

        is_risk_A = fA and fA["status"] == "true"
        is_risk_B = fB and fB["status"] == "true"

        if is_risk_A and is_risk_B:
            common_risks.append(fA) 
        elif is_risk_A and not is_risk_B:
            unique_to_A.append(fA)
        elif is_risk_B and not is_risk_A:
            unique_to_B.append(fB)

    scoreA = reportA["overall_score"]
    scoreB = reportB["overall_score"]
    
    verdict = "Tie"
    winner = "Tie"
    if scoreA > scoreB:
        verdict = "Policy B is Safer"
        winner = "B"
    elif scoreB > scoreA:
        verdict = "Policy A is Safer"
        winner = "A"

    return {
        "reportA": reportA,
        "reportB": reportB,
        "comparison": {
            "verdict": verdict,
            "winner": winner,
            "score_diff": round(abs(scoreA - scoreB), 2),
            "common_risks": common_risks,
            "unique_to_A": unique_to_A,
            "unique_to_B": unique_to_B
        }
    }