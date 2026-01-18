# --- FIX: Direct imports ---
from weights import FLAG_WEIGHTS
from flags import FLAGS

def compute_score(findings):
    overall_score = 0
    category_scores = { category: 0 for category in FLAGS.keys() }

    for finding in findings:
        flag = finding['flag']
        status = finding['status']
        confidence = finding['confidence']
        weight = FLAG_WEIGHTS.get(flag, 0)

        # Calculate score based on flag status and confidence
        if status == "true":
            overall_score += weight * confidence
            category_scores[finding['category']] += weight * confidence
        elif status == "false":
            overall_score -= weight  
        elif status == "unknown":
            overall_score -= weight * 0.5  

    return overall_score, category_scores