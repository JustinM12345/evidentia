from .weights import FLAG_WEIGHTS
from .flags import FLAGS

def compute_score(findings: list) -> dict:
    """
    Computes the overall score and category-based scores based on the flag findings.
    
    Args:
        findings (list): A list of finding dictionaries returned from the LLM response, each containing
                         'flag', 'status', 'confidence', and 'category'.
                         
    Returns:
        dict: A dictionary containing the 'overall_score' and 'category_scores'.
    """
    overall_score = 0
    category_scores = {category: 0 for category in FLAGS.keys()}  # Initialize category scores

    total_weight = 0  # Keep track of the total weight for normalization

    for finding in findings:
        flag = finding['flag']
        status = finding['status']
        confidence = finding['confidence']
        
        # Get the flag weight from FLAG_WEIGHTS (default to 0 if not found)
        weight = FLAG_WEIGHTS.get(flag, 0)

        # Score calculation based on status and confidence
        if status == "true":
            overall_score += weight * confidence  # Increase score based on weight and confidence
        elif status == "false":
            overall_score -= weight  # Decrease score if flag is false
        elif status == "unknown":
            overall_score -= weight * 0.5  # Give partial weight to unknown flags

        # Update category-specific scores based on category and weight
        category = finding.get("category", "unknown")
        if category in category_scores:
            category_scores[category] += weight * confidence  # Increase category score based on confidence

        # Track the total weight to normalize the overall score later
        total_weight += weight

    # Normalize the overall score based on the total weight
    if total_weight > 0:
        overall_score = (overall_score / total_weight) * 100  # Normalize to a percentage

    return {
        "overall_score": overall_score,
        "category_scores": category_scores
    }

