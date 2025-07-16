# crawler/llm/reconcile.py

from collections import Counter

def reconcile_classifications(classifications: list[dict], priority_model: str = None) -> dict:
    """
    Reconciles classification outputs from multiple models.

    Args:
        classifications: A list of classification results from different models.
        priority_model: The name of a model to prioritize in case of a tie.

    Returns:
        A dictionary with the final classification and reconciliation details.
    """
    # Filter out failed or invalid classifications
    valid_classifications = [c for c in classifications if c.get("classification")]

    if not valid_classifications:
        return {"final_classification": "failed", "strategy": "none", "error": "No valid classifications provided."}

    # Count votes for each classification
    votes = Counter(c["classification"] for c in valid_classifications)

    # Find the highest vote count
    max_votes = max(votes.values())

    # Get all classifications with the highest vote count
    top_classifications = [cls for cls, count in votes.items() if count == max_votes]

    # Determine final classification
    if len(top_classifications) == 1:
        # Clear majority winner
        winner = top_classifications[0]
        strategy = "majority_vote"
    else:
        # Handle tie
        if priority_model:
            # Check if the priority model's choice is among the tied classifications
            priority_vote = next((c["classification"] for c in valid_classifications if c["model"] == priority_model and c["classification"] in top_classifications), None)
            if priority_vote:
                winner = priority_vote
                strategy = f"tie_breaker (priority_model: {priority_model})"
            else:
                # If priority model is not in the tie, default to the first one
                winner = top_classifications[0]
                strategy = "tie_breaker (default)"
        else:
            # No priority model, default to the first one
            winner = top_classifications[0]
            strategy = "tie_breaker (default)"

    contributing_models = [c["model"] for c in valid_classifications if c["classification"] == winner]

    return {
        "final_classification": winner,
        "strategy": strategy,
        "winning_vote_count": max_votes,
        "contributing_models": contributing_models
    }
