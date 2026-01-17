from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Finding(BaseModel):
    flag: str
    label: str
    category: str
    status: str  # "true", "false", "unknown"
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
    deltas: Dict[str, float]  # Deltas between reportA and reportB, like score differences
    added: List[str]  # List of flags added in reportB but not in reportA
    removed: List[str]  # List of flags removed in reportB but not in reportA
    changed: List[str]  # List of flags that changed between reportA and reportB
    metrics: Optional[Dict[str, float]] = None  # Optional, additional metrics (e.g., coverage, latency)

