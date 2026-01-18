import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
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

class AnalyzeRequest(BaseModel):
    text: str

class CompareRequest(BaseModel):
    textA: str
    textB: str

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    try:
        # Directly analyze the provided text
        llm_result = call_llm_extract(req.text)
        return llm_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compare")
def compare(req: CompareRequest) -> Dict[str, Any]:
    try:
        comparison_result = call_llm_compare_side_by_side(req.textA, req.textB)
        
        reportA = comparison_result["reportA"]
        reportB = comparison_result["reportB"]
        
        findingsA = {f["flag"]: f for f in reportA["findings"]}
        findingsB = {f["flag"]: f for f in reportB["findings"]}
        
        common_risks, unique_to_A, unique_to_B = [], [], []
        all_flags = set(findingsA.keys()).union(set(findingsB.keys()))

        for flag_id in all_flags:
            fA, fB = findingsA.get(flag_id), findingsB.get(flag_id)
            is_risk_A = fA and fA["status"] == "true"
            is_risk_B = fB and fB["status"] == "true"

            if is_risk_A and is_risk_B:
                common_risks.append(fA) 
            elif is_risk_A:
                unique_to_A.append(fA)
            elif is_risk_B:
                unique_to_B.append(fB)

        scoreA, scoreB = reportA["overall_score"], reportB["overall_score"]
        verdict = "Policy B is Safer" if scoreA > scoreB else ("Policy A is Safer" if scoreB > scoreA else "Tie")
        
        return {
            "reportA": reportA,
            "reportB": reportB,
            "comparison": {
                "verdict": verdict,
                "winner": "B" if scoreA > scoreB else ("A" if scoreB > scoreA else "Tie"),
                "score_diff": round(abs(scoreA - scoreB), 2),
                "common_risks": common_risks,
                "unique_to_A": unique_to_A,
                "unique_to_B": unique_to_B
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))