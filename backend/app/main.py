from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.app.llm import call_llm_extract, normalize_flags
from backend.app.schemas import AnalyzeResponse, CompareResponse

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

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    try:
        # Call LLM to extract findings from the policy text
        llm_result = call_llm_extract(req.text)

        # Normalize the response to ensure all flags are included and formatted correctly
        normalized_result = normalize_flags(llm_result)
        normalized_result["meta"] = {"url": req.url}

        # Return the normalized response
        return normalized_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during analysis: {str(e)}")

@app.post("/api/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> Dict[str, Any]:
    try:
        # Call analyze for both policies A and B
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
                # If flags are not the same, we can mark them as changed
                changed.append(flagA["flag"])

        return {
            "reportA": reportA,
            "reportB": reportB,
            "deltas": deltas,
            "added": added,
            "removed": removed,
            "changed": changed
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during comparison: {str(e)}")

