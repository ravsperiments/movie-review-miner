import unittest
from crawler.llm.reconcile import reconcile_classifications

class TestReconciliation(unittest.TestCase):

    def test_majority_vote_success(self):
        classifications = [
            {"model": "gemini-1.5-pro", "classification": "review", "confidence": 0.95},
            {"model": "claude-3-opus", "classification": "review", "confidence": 0.92},
            {"model": "gpt-4o", "classification": "not_review", "confidence": 0.88}
        ]
        result = reconcile_classifications(classifications)
        self.assertEqual(result["final_classification"], "review")
        self.assertEqual(result["strategy"], "majority_vote")
        self.assertEqual(result["winning_vote_count"], 2)

    def test_tie_breaker_with_priority_model(self):
        classifications = [
            {"model": "gemini-1.5-pro", "classification": "review", "confidence": 0.95},
            {"model": "claude-3-opus", "classification": "not_review", "confidence": 0.92}
        ]
        result = reconcile_classifications(classifications, priority_model="claude-3-opus")
        self.assertEqual(result["final_classification"], "not_review")
        self.assertEqual(result["strategy"], "tie_breaker (priority_model: claude-3-opus)")

    def test_tie_breaker_default(self):
        classifications = [
            {"model": "gemini-1.5-pro", "classification": "review", "confidence": 0.95},
            {"model": "claude-3-opus", "classification": "not_review", "confidence": 0.92}
        ]
        result = reconcile_classifications(classifications)
        self.assertEqual(result["final_classification"], "review")
        self.assertEqual(result["strategy"], "tie_breaker (default)")

    def test_input_with_failures(self):
        classifications = [
            {"model": "gemini-1.5-pro", "classification": "review", "confidence": 0.95},
            {"model": "claude-3-opus", "classification": None, "confidence": 0.92},
            {"model": "gpt-4o", "classification": "not_review", "confidence": 0.88}
        ]
        result = reconcile_classifications(classifications)
        self.assertEqual(result["final_classification"], "review")
        self.assertEqual(result["strategy"], "tie_breaker (default)")

    def test_empty_input(self):
        classifications = []
        result = reconcile_classifications(classifications)
        self.assertEqual(result["final_classification"], "failed")
        self.assertEqual(result["error"], "No valid classifications provided.")

if __name__ == '__main__':
    unittest.main()
