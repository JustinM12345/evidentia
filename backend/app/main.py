import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware

# Direct import from your llm.py
from llm import call_llm_extract

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
        raise HTTPException(status_code=400, detail="Error: Scraper API Key missing.")

    print(f"🍰 Calling Yellowcake for: {target_url}", flush=True)
    
    headers = {
        "x-api-key": YELLOWCAKE_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": target_url,
        "prompt": "Extract the full Privacy Policy text"
    }

    try:
        response = requests.post(YELLOWCAKE_URL, json=payload, headers=headers, timeout=30)
        print(f"✅ Yellowcake Status: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            data = response.json()
            text = data.get("text") or data.get("content") or data.get("data") or ""
            
            # PROTECT AGAINST BLOCKS: If the text is too short, it's a failed scrape
            if len(str(text).strip()) < 200:
                print(f"⚠️ Scraping failed: Text too short ({len(str(text))} chars)", flush=True)
                raise HTTPException(status_code=400, detail="Error: SITE_PROTECTED")
            
            print(f"📄 Extracted {len(text)} chars from URL.", flush=True)
            return str(text)
        else:
            raise HTTPException(status_code=400, detail="Error: SITE_PROTECTED")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Yellowcake Error: {str(e)}", flush=True)
        raise HTTPException(status_code=400, detail="Error: SITE_PROTECTED")

# --- HELPER: ROBUST URL DETECTOR ---
def process_input(input_text: str) -> str:
    clean_input = input_text.strip()
    
    # 1. Check if it looks like a URL (starts with http/https)
    is_url = clean_input.lower().startswith(("http://", "https://"))
    
    if is_url:
        print("🚀 DETECTED URL -> Fetching content...", flush=True)
        return fetch_from_yellowcake(clean_input)
    
    # Otherwise, it's pasted text
    print("📝 DETECTED TEXT -> Analyzing directly.", flush=True)
    return input_text

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    final_text = process_input(req.text)
    llm_result = call_llm_extract(final_text)
    return llm_result

@app.post("/api/compare")
def compare(req: CompareRequest) -> Dict[str, Any]:
    print("\n--- NEW COMPARISON REQUEST ---", flush=True)
    processed_A = process_input(req.textA)
    processed_B = process_input(req.textB)

    # Analyze separately to avoid schema complexity errors
    reportA = call_llm_extract(processed_A)
    reportB = call_llm_extract(processed_B)
    
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
    
    return {
        "reportA": reportA,
        "reportB": reportB,
        "comparison": {
            "verdict": "Policy B is Safer" if scoreA > scoreB else "Policy A is Safer" if scoreB > scoreA else "Tie",
            "winner": "B" if scoreA > scoreB else "A" if scoreB > scoreA else "Tie",
            "score_diff": round(abs(scoreA - scoreB), 2),
            "common_risks": common_risks,
            "unique_to_A": unique_to_A,
            "unique_to_B": unique_to_B
        }
    }