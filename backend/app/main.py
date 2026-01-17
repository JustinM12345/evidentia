from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

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
    # TODO: call LLM + return real findings
    return {
        "overall_score": 0,
        "category_scores": {},
        "findings": [],
        "meta": {"url": req.url}
    }

@app.post("/api/compare")
def compare(req: CompareRequest) -> Dict[str, Any]:
    # TODO: run analyze twice + diff
    return {
        "reportA": {"overall_score": 0, "category_scores": {}, "findings": [], "meta": {"url": req.urlA}},
        "reportB": {"overall_score": 0, "category_scores": {}, "findings": [], "meta": {"url": req.urlB}},
        "deltas": {"overall_score": 0, "category_scores": {}},
        "added": [],
        "removed": [],
        "changed": []
    }
