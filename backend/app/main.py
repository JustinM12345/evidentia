import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware
from llm import call_llm_extract, call_llm_compare_side_by_side

app = FastAPI(title="Evidentia API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def fetch_from_yellowcake(target_url: str) -> str:
    if not YELLOWCAKE_API_KEY:
        return "Error: Yellowcake API Key missing."

    # Improved headers to mimic a real browser
    headers = {
        "x-api-key": YELLOWCAKE_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    payload = {
        "url": target_url,
        "render_js": True,
        "wait": 3000,
        "prompt": "Extract the full Terms of Service or Privacy Policy text."
    }

    try:
        response = requests.post(YELLOWCAKE_URL, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            text = data.get("text") or data.get("content") or data.get("data") or ""
            
            # Guardrail to detect if we were served a blank/blocked page
            if len(str(text).strip()) < 500:
                raise HTTPException(status_code=400, detail="Error: Website blocked the reader. Please copy-paste manually.")
            
            return str(text)
        else:
            raise HTTPException(status_code=400, detail=f"Scraper error: Status {response.status_code}")
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        return f"Error connecting: {str(e)}"

def process_input(input_text: str) -> str:
    clean_input = input_text.strip()
    is_url = clean_input.lower().startswith(("http://", "https://"))
    has_spaces = " " in clean_input

    if is_url and not has_spaces:
        return fetch_from_yellowcake(clean_input)
    return input_text

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    final_text = process_input(req.text)
    llm_result = call_llm_extract(final_text)
    llm_result["meta"] = {"url": req.text if req.text.startswith("http") else req.url}
    return llm_result

@app.post("/api/compare")
def compare(req: CompareRequest) -> Dict[str, Any]:
    processed_A = process_input(req.textA)
    processed_B = process_input(req.textB)
    
    comparison_result = call_llm_compare_side_by_side(processed_A, processed_B)
    
    reportA = comparison_result["reportA"]
    reportB = comparison_result["reportB"]
    
    findingsA = {f["flag"]: f for f in reportA["findings"]}
    findingsB = {f["flag"]: f for f in reportB["findings"]}
    
    common_risks, unique_to_A, unique_to_B = [], [], []
    all_flags = set(findingsA.keys()).union(set(findingsB.keys()))

    for flag_id in all_flags:
        fA, fB = findingsA.get(flag_id), findingsB.get(flag_id)
        if fA and fA["status"] == "true" and fB and fB["status"] == "true":
            common_risks.append(fA) 
        elif fA and fA["status"] == "true":
            unique_to_A.append(fA)
        elif fB and fB["status"] == "true":
            unique_to_B.append(fB)

    scoreA, scoreB = reportA["overall_score"], reportB["overall_score"]
    verdict = "Policy B is Safer" if scoreA > scoreB else ("Policy A is Safer" if scoreB > scoreA else "Tie")
    
    return {
        "reportA": reportA, "reportB": reportB,
        "comparison": {
            "verdict": verdict,
            "winner": "B" if scoreA > scoreB else ("A" if scoreB > scoreA else "Tie"),
            "score_diff": round(abs(scoreA - scoreB), 2),
            "common_risks": common_risks,
            "unique_to_A": unique_to_A,
            "unique_to_B": unique_to_B
        }
    }