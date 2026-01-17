from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Finding(BaseModel):
    flag: str
    label: str
    category: str
    status: str  # true, false, unknown
    confidence: float
    evidence_quote: Optional[str] = None
    url: Optional[str] = None

class AnalyzeResponse(BaseModel):
    overall_score: float
    category_scores: Dict[str, float]
    findings: List[Finding]
    meta: Optional[Dict[str, Any]] = None  # Add meta field to store additional info like URL


class CompareResponse(BaseModel):
    reportA: AnalyzeResponse
    reportB: AnalyzeResponse
    deltas: Dict[str, float]
    added: List[str]
    removed: List[str]
    changed: List[str]
    metrics: Dict[str, float]
