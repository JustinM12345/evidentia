from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# --- FIX: Direct import ---
from llm import call_llm_extract 

app = FastAPI(title="Evidentia API")

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

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    llm_result = call_llm_extract(req.text)
    llm_result["meta"] = {"url": req.url}
    return llm_result

@app.post("/api/compare")
def compare(req: CompareRequest) -> Dict[str, Any]:
    # 1. Analyze both policies
    reportA = analyze(AnalyzeRequest(text=req.textA, url=req.urlA))
    reportB = analyze(AnalyzeRequest(text=req.textB, url=req.urlB))
    
    # 2. Extract Findings Maps
    findingsA = {f["flag"]: f for f in reportA["findings"]}
    findingsB = {f["flag"]: f for f in reportB["findings"]}
    
    # 3. Categorize Risks
    common_risks = []
    unique_to_A = []
    unique_to_B = []

    all_flags = set(findingsA.keys()).union(set(findingsB.keys()))

    for flag_id in all_flags:
        fA = findingsA.get(flag_id)
        fB = findingsB.get(flag_id)

        is_risk_A = fA and fA["status"] in ["true", "unknown"]
        is_risk_B = fB and fB["status"] in ["true", "unknown"]

        if is_risk_A and is_risk_B:
            common_risks.append(fA) 
        elif is_risk_A and not is_risk_B:
            unique_to_A.append(fA)
        elif is_risk_B and not is_risk_A:
            unique_to_B.append(fB)

    # 4. Determine Verdict
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