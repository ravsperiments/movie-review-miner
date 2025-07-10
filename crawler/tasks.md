### 📋 tasks.md — LLM Movie Review Miner

#### Week 1: Basic Crawler
- [x] Set up project structure and virtual environment
- [x] Create `get_post_links()` in `fetch_links.py`
- [x] Debug selector to correctly fetch blog post links
- [x] Create `parse_post()` in `parse_post.py` to extract title and intro

#### Week 2: Sentiment Analysis
- [x] Choose LLM source (OpenAI or local LLaMA)
- [x] Implement `analyze_sentiment()` in `llm/openai_wrapper.py` or `llm/llama_wrapper.py`
- [x] Design and test prompt: “Does the author recommend this movie?”
- [x] Tag each post as positive or not
- [x] Provide async script to enrich sentiment for reviews missing data

#### Week 3: Curation & Output
- [x] Store movie reviews in Supabase database
- [x] Enrich reviews with movie metadata from TMDb

#### Week 4: CLI & Extensibility
- [x] Add CLI arguments: number of posts, export format, LLM model
- [x] Add progress bar with `tqdm`
- [x] Add logging to file

#### Week 5: Async Batch Orchestration
- [x] Remove Redis/RQ based task queue (discard `run_worker.py`, `enqueue_tasks.py`, `master_orchestrator.py`)
- [x] Implement asynchronous pagination scraper (`get_post_links_async` in `scraper/sources`)
- [x] Create pipeline step1 (`pipeline/step_1_fetch_links.py`) to fetch & store blog post URLs in Supabase
- [x] Implement async `parse_post_async` in `scraper/parse_post.py` to extract structured data from posts
- [x] Create pipeline step2 (`pipeline/step_2_parse_posts.py`) to parse posts concurrently and upsert reviews
- [x] Add structured logging (`utils/logger`) and failure tracking (`failed_post_links.txt`) in scraper & pipeline
- [x] Use asyncio.gather and semaphores to control concurrency

#### Week 6: Refactor Pipeline & Modularize Blog Post Specific Crawling Logic
- [x] Extract remaining pipeline stages into modules (`pipeline/step_3_classify_reviews.py`, `pipeline/step_3b_llm_validation.py`, `pipeline/step_4_link_movies.py`, `pipeline/step_5_generate_sentiment.py`, `pipeline/step_6_enrich_metadata.py`)
- [x] Implement classification step to tag film reviews (`pipeline/step_3_classify_reviews.py`)
- [x] Implement LLM-based review validation placeholder (`pipeline/step_3b_llm_validation.py`)
- [x] Link reviews to movies via LLM title extraction (`pipeline/step_4_link_movies.py`)
- [x] Enrich reviews with sentiment labels (`pipeline/step_5_generate_sentiment.py`)
- [x] Fetch and update TMDb metadata (`pipeline/step_6_enrich_metadata.py`)
- [x] Add weekly orchestrator script (`run_pipeline.py`) with CLI options (`--limit`, `--dry-run`, `--reviewer`)
- [x] Modularize blog-specific scraping in `scraper/sources` and parsing in `scraper/parse_post.py`
- [x] Log pipeline metrics and results via `utils.StepLogger` and `db.pipeline_logger`
- [x] Instrument remote LLM throughput & token usage metrics (requests, concurrency, prompt/completion tokens) via Prometheus_client

##### 2025-07-07
- [x] Implement `raw_scraped_pages` staging table
- [x] Update `fetch_links` to insert into `raw_scraped_pages` with critic ID and status
- [x] Update `parse_posts` to read from and update `raw_scraped_pages`
- [x] Implement early stopping in `baradwajrangan_links.py`
- [x] Implement upsert for duplicate prevention in `store_scraped_pages.py`
- [x] Refactor `fetch_links` to support multiple reviewers with dedicated scripts
- [x] Create `crawler/db/reviewers.py` for reviewer data management
- [x] Create `crawler/scraper/critics/baradwajrangan_fetcher.py` for critic-specific fetching logic
- [x] Create `crawler/pipeline/fetch_links_orchestrator.py` to orchestrate reviewer-specific fetchers
- [x] Update `crawler/run_pipeline.py` to use the new orchestrator
- [x] Move `crawler/reviewers.py` to `crawler/db/reviewers.py`
- [x] Add comprehensive in-code comments to all modules involved in the `fetch_links` pipeline step
- [x] Update `README.md` with project overview, crawler design, folder structure, pipeline explanation, and Step 1 details

##### 2025-07-08
- [x] Move `baradwaj_rangan_parse.py` to `crawler/scraper/critics/baradwaj_rangan_parser.py`
- [x] Update `crawler/scraper/parse_post.py` to reflect new parser location and use critic UUIDs
- [x] Rename `crawler/db/store_scraped_pages.py` to `crawler/db/scraper_queries.py`
- [x] Add new functions to `scraper_queries.py` for `new_scraped_links` table (get, update parsed, update error)
- [x] Create `crawler/pipeline/parse_posts_orchestrator.py` for testing with `new_scraped_links`
- [x] Fix `parse_posts_orchestrator.py` to use `page_url` instead of `post_url`
- [x] Fix `parse_posts_orchestrator.py` to map `critic_id` correctly
- [x] Fix `scraper_queries.py` to map parsed data keys (`parsed_title`, etc.) to correct database column names (`title`, etc.) for `raw_scraped_pages`
- [x] Fix `scraper_queries.py` to use correct table name `new_scraped_links` (removed typo `new_scrapped_links`)
- [x] Refactor `crawler/db/supabase_client.py` to use standard logging to resolve circular dependency
- [x] Upgrade `parse_posts_orchestrator.py` (formerly `crawl_step2_parse_posts.py`) to dynamically select parsers based on `critic_id`
- [x] Rename `crawl_step2_parse_posts.py` to `parse_posts_orchestrator.py`
- [x] Revert `parse_posts_orchestrator.py` to use `new_scraped_links` table for testing
- [x] Update `crawler/scraper/parse_post.py` to use critic UUIDs in `SOURCES` dictionary
- [x] Switch `parse_posts_orchestrator.py` back to `raw_scraped_pages` table
- [x] Add robust comments to `parse_posts_orchestrator.py`
- [x] Refactor `pipeline/parse_posts_orchestrator.py` to iterate per critic+base_url (DB-driven critic lookup) with improved concurrency and retry logic
- [x] Refactor `pipeline/review_validation_orchestrator.py` to use an LLMController for explicit model selection or parallel multi-model runs, and batch-store results in `stg_llm_logs`

##### 2025-07-09
- [x] Fixed "Broken pipe" error in `review_validation_orchestrator.py` by removing redundant batch insert.
- [x] Implemented rate limiting in `review_validation_orchestrator.py` to avoid overwhelming APIs.
- [x] Refactored `review_validation_orchestrator.py` to stream LLM logs to the database.
- [x] Refactored `review_validation_orchestrator.py` to simplify the `classify_review_with_llm` function and remove unnecessary `asyncio.gather`.
- [x] TODO: implement LLaMA wrapper via Ollama CLI for local LLaMA2 inference
- [x] TODO: build a comparison script to evaluate multiple model outputs and apply a voting system for final decision

#### 2025-07-10
- [ ] TODO: execute the classification orchestrator for all parsed posts in staging
- [ ] TODO: update `stg_cleaned_reviews` with final voted results
