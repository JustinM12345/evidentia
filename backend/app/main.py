from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.app.llm import call_llm_extract

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

    # TEMP: just return LLM result directly first
    # Once stable, you’ll map/validate it into your expected schema.
    llm_result["meta"] = {"url": req.url}
    return llm_result

@app.post("/api/compare")
def compare(req: CompareRequest) -> Dict[str, Any]:
    # Call analyze for both A and B
    reportA = analyze(AnalyzeRequest(text=req.textA, url=req.urlA))
    reportB = analyze(AnalyzeRequest(text=req.textB, url=req.urlB))
    
    # Initialize comparison data
    added = []
    removed = []
    changed = []
    deltas = {"overall_score": reportB["overall_score"] - reportA["overall_score"]}
    
    # Compare findings (flags) between Policy A and Policy B
    for flagA, flagB in zip(reportA["findings"], reportB["findings"]):
        if flagA["flag"] == flagB["flag"]:  # Ensure comparing the same flags
            # Check if status has changed
            if flagA["status"] != flagB["status"]:
                changed.append(flagA["flag"])
            # Check if confidence has changed
            elif flagA["confidence"] != flagB["confidence"]:
                changed.append(flagA["flag"])
            # If the flag is true in A but missing in B, it's removed
            if flagA["status"] == "true" and flagB["status"] != "true":
                removed.append(flagA["flag"])
            # If the flag is true in B but missing in A, it's added
            elif flagB["status"] == "true" and flagA["status"] != "true":
                added.append(flagB["flag"])
        else:
            # In case flags are not the same, we can mark them as changed
            changed.append(flagA["flag"])
    
    return {
        "reportA": reportA,
        "reportB": reportB,
        "deltas": deltas,
        "added": added,
        "removed": removed,
        "changed": changed
    }

