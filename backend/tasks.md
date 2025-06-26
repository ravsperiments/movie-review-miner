### 📋 tasks.md — LLM Movie Review Miner

#### ✅ Milestone 1: Basic Crawler
- [x] Set up project structure and virtual environment
- [x] Create \`get_post_links()\` in \`fetch_links.py\`
- [x] Debug selector to correctly fetch blog post links
- [x] Create \`parse_post()\` in \`parse_post.py\` to extract title and intro

#### 🧠 Milestone 2: Sentiment Analysis
- [x] Choose LLM source (OpenAI or local LLaMA)
- [x] Implement \`analyze_sentiment()\` in \`llm/openai_wrapper.py\` or \`llm/llama_wrapper.py\`
- [x] Design and test prompt: “Does the author recommend this movie?”
- [x] Tag each post as positive or not
- [x] Provide async script to enrich sentiment for reviews missing data

#### 🎬 Milestone 3: Curation & Output
- [x] Store movie reviews in Supabase database
- [x] Enrich reviews with movie metadata from TMDb

#### 🔧 Milestone 4: CLI & Extensibility
- [x] Add CLI arguments: number of posts, export format, LLM model
- [x] Add progress bar with \`tqdm\`
- [x] Add logging to file

#### 🧵 Milestone 5: Async Batch Orchestration
- [x] Replaced RQ setup with asyncio.gather
- [x] Add subprocess-safe job runner using `parse_post_subprocess.py`
- [ ] Modify `get_post_links()` to support pagination (page-wise crawling)
- [ ] Create `enqueue_link_batches()` to enqueue one job per page (e.g. `get_post_links_batch(page)`)
- [ ] For each batch, enqueue `parse_post(url)` jobs for every link
- [ ] Update `parse_post()` to return structured data (title, summary, date)
- [ ] Create `save_to_db(data)` function to persist parsed results
- [ ] Chain parsing jobs to enqueue `save_to_db()` with parsed result
- [ ] Add fallback to store failed results in `failed_links.txt` or log file
- [ ] Use logging to track status and timing
- [ ] Ensure tasks run in the correct order
- [ ] Implement CLI to reprocess failed links (retry mode)

#### 🚀 Milestone 6: Polish
- [ ] Write tests for \`fetch_links\` and \`parse_post\`
- [ ] Add README examples
- [ ] Dockerize or package for CLI use
- [ ] Create Makefile or \`run.sh\` for setup and run
