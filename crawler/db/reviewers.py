from typing import List, Dict

def get_reviewers() -> List[Dict]:
    """
    Returns a hardcoded list of reviewers.
    In the future, this function will fetch reviewers from a Supabase table.
    """
    return [
        {
            "id": "79031f4e-3785-425d-a17d-4796cdf0a87e",
            "name": "Baradwaj Rangan",
            "base_url": "https://baradwajrangan.wordpress.com/",
            "domain": "baradwajrangan.wordpress.com"
        }
    ]

if __name__ == "__main__":
    reviewers = get_reviewers()
    for reviewer in reviewers:
        print(f"ID: {reviewer['id']}, Name: {reviewer['name']}, Base URL: {reviewer['base_url']}")