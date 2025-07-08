from typing import List, Dict

def get_reviewers() -> List[Dict]:
    """
    Retrieves a list of reviewers with their associated metadata.

    Currently, this function returns a hardcoded list of reviewers.
    In future iterations, this function is designed to be extended to fetch
    reviewer information dynamically from a persistent data store, such as
    a Supabase table. This allows for easy addition, modification, or removal
    of reviewers without code changes.

    Each reviewer dictionary contains:
    - 'id' (str): A unique identifier for the critic.
    - 'name' (str): The full name of the critic.
    - 'base_url' (str): The base URL of the critic's blog or website.
    - 'domain' (str): The primary domain of the critic's website, used for
                      identifying the correct scraping logic.

    Returns:
        List[Dict]: A list of dictionaries, each representing a reviewer.
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
    # This block allows for standalone testing of the get_reviewers function.
    # When executed directly, it prints the details of each hardcoded reviewer.
    reviewers = get_reviewers()
    for reviewer in reviewers:
        print(f"ID: {reviewer['id']}, Name: {reviewer['name']}, Base URL: {reviewer['base_url']}")