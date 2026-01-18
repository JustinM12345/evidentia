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
    if not YELLOWCAKE_API_KEY:
        print("⚠️ Warning: No Yellowcake API Key found.", flush=True)
        return "Error: Yellowcake API Key missing."

    print(f"🍰 Calling Yellowcake for: {target_url}", flush=True)
    
    headers = {
        "x-api-key": YELLOWCAKE_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": target_url,
        "prompt": "Extract the full Terms of Service or Privacy Policy text. Ignore navigation."
    }

    try:
        response = requests.post(YELLOWCAKE_URL, json=payload, headers=headers, timeout=30)
        print(f"✅ Yellowcake Status: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            data = response.json()
            text = data.get("text") or data.get("content") or data.get("data") or ""
            
            # --- NEW LENGTH VALIDATION ---
            if len(str(text).strip()) < 200:
                print(f"⚠️ Scraping failed: Text too short ({len(str(text))} chars)", flush=True)
                # We raise this exception so the frontend catches it immediately
                raise HTTPException(
                    status_code=400, 
                    detail="Error: Program was blocked when reading terms and conditions OR provided policy was less than 200 characters."
                )
            
            print(f"📄 Extracted {len(text)} chars from URL.", flush=True)
            return str(text)
        else:
            # Handle non-200 status codes (like 403 or 429)
            raise HTTPException(
                status_code=400, 
                detail=f"Error: Program was blocked (Status {response.status_code}) when reading terms and conditions."
            )
            
    except HTTPException as he:
        # Re-raise HTTPExceptions so they reach the client
        raise he
    except Exception as e:
        print(f"❌ Yellowcake Error: {str(e)}", flush=True)
        raise HTTPException(status_code=400, detail=f"Error connecting to scraper: {str(e)}")
    
# --- HELPER: ROBUST URL DETECTOR ---
def process_input(input_text: str) -> str:
    # 1. Clean the input first (removes accidental spaces/newlines)
    clean_input = input_text.strip()
    
    # 2. Check if it's a URL (Ignore the spaces check, just check the start)
    is_url = clean_input.lower().startswith(("http://", "https://"))

    if is_url:
        print(f"🚀 URL detected: {clean_input}", flush=True)
        try:
            return fetch_from_yellowcake(clean_input)
        except Exception as e:
            # If scraper fails, we raise the error for the frontend
            raise HTTPException(status_code=400, detail=str(e))
    
    # 3. If it's not a URL, it's text
    print("📝 Analyzing as raw text", flush=True)
    return clean_input

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