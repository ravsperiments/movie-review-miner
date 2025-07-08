# Movie Review Miner

## Project Overview
The Movie Review Miner is a data pipeline designed to scrape, process, and analyze movie reviews from various online sources. Its primary goal is to extract structured information from unstructured blog posts and reviews, enrich this data with metadata, and store it in a searchable format.

---

## Crawler

### Overview
The crawler component is responsible for systematically fetching blog posts and reviews from designated online critics. It's built to be extensible, allowing for the easy integration of new review sources and adapting to different website structures.

### Design Overview
The crawler is designed with modularity and asynchronous processing at its core. It follows a pipeline approach, where each step is a distinct, manageable unit. This design facilitates maintainability, scalability, and the ability to introduce new processing stages or modify existing ones without affecting the entire system.

### Folder Structure
The `crawler/` directory is organized as follows:
- `db/`: Contains modules for database interactions, including storing scraped data and managing reviewer information.
- `failures/`: Stores logs or records of failed processing attempts.
- `llm/`: Houses functions and prompts related to Large Language Models (LLMs) for tasks like sentiment analysis.
- `logs/`: Contains log files generated during crawler runs.
- `pipeline/`: Orchestrates the core data processing steps.
- `scraper/`: Implements the logic for gathering review and blog data, including source-specific scraping.
- `tasks/`: Defines various data processing tasks (e.g., enrichment, classification).
- `tests/`: Contains unit tests for the crawler components.
- `tmdb/`: Provides helpers for interacting with the TMDb API for movie metadata enrichment.
- `utils/`: General-purpose utility functions used across the crawler.

### Pipeline
The crawler's data pipeline is built on an asynchronous architecture, leveraging Python's `asyncio` for efficient concurrent operations. This allows the system to handle multiple fetching and processing tasks simultaneously, significantly improving throughput.

**Note on Design Evolution:**
Initially, a Redis/RQ-based task queue was considered for managing asynchronous tasks. However, for the current scope and to maintain a simpler, more direct asynchronous orchestration, a pure `asyncio`-based pipeline was chosen. This approach reduces external dependencies and provides a more streamlined control flow for the current set of operations.

#### Step 1: Fetch Links Implementation
The first step of the pipeline focuses on fetching blog post links from various critics. This step is implemented with extensibility in mind, allowing for the addition of new reviewers with potentially different scraping requirements.

*   **Reviewer Data Management (`crawler/db/reviewers.py`):**
    *   Manages a list of configured reviewers, each with a unique ID, name, base URL, and domain.
    *   Currently hardcoded for simplicity, but designed to be easily extended to fetch reviewer data from a database (e.g., Supabase) in the future.
*   **Orchestration (`crawler/pipeline/fetch_links_orchestrator.py`):**
    *   Serves as the central entry point for Step 1.
    *   Retrieves the list of reviewers and dynamically imports and executes the appropriate reviewer-specific fetching script for each.
    *   Handles logging and error reporting for individual reviewer fetching processes, ensuring that a failure for one reviewer does not halt the entire pipeline.
*   **Reviewer-Specific Fetchers (`crawler/scraper/critics/baradwajrangan_fetcher.py`):**
    *   Contains the specific logic for scraping links from a particular critic's website (e.g., Baradwaj Rangan's blog).
    *   Each new critic added to the system will ideally have its own dedicated fetcher script in this directory.
*   **Generic Link Fetching (`crawler/scraper/fetch_links.py`):**
    *   Acts as a dispatcher, routing requests to the correct reviewer-specific scraping module based on a simplified reviewer name.
    *   Provides a unified interface for the orchestrator to interact with various scraping sources.
*   **Source-Specific Scraping (`crawler/scraper/sources/baradwajrangan_links.py`):**
    *   Implements the low-level details of navigating and extracting links from a specific website.
    *   Includes mechanisms for handling pagination, retries, and early stopping if no new links are found.
*   **Database Storage (`crawler/db/store_scraped_pages.py`):**
    *   Responsible for bulk inserting newly fetched raw page URLs into the `raw_scraped_pages` table in the Supabase database.
    *   Utilizes an upsert mechanism to prevent duplicate entries and update existing ones.

---

## Web

(Content for the web component will be added here in future iterations.)
