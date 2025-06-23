### 📋 tasks.md — LLM Movie Review Miner

#### ✅ Milestone 1: Basic Crawler
- [x] Set up project structure and virtual environment
- [x] Create \`get_post_links()\` in \`fetch_links.py\`
- [x] Debug selector to correctly fetch blog post links
- [x] Create \`parse_post()\` in \`parse_post.py\` to extract title and intro
- [ ] Add retry/backoff logic for network failures

#### 🧠 Milestone 2: Sentiment Analysis
- [x] Choose LLM source (OpenAI or local LLaMA)
- [x] Implement \`analyze_sentiment()\` in \`llm/openai_wrapper.py\` or \`llm/llama_wrapper.py\`
- [x] Design and test prompt: “Does the author recommend this movie?”
- [x] Tag each post as positive or not

#### 🎬 Milestone 3: Curation & Output
- [x] Store movie reviews in Supabase database
- [ ] Add function to pretty-print or export results (e.g. CSV, markdown)
- [ ] Optionally group results by year or genre

#### 🔧 Milestone 4: CLI & Extensibility
- [ ] Add CLI arguments: number of posts, export format, LLM model
- [ ] Add progress bar with \`tqdm\`
- [ ] Add logging to file

#### 🚀 Milestone 5: Polish
- [ ] Write tests for \`fetch_links\` and \`parse_post\`
- [ ] Add README examples
- [ ] Dockerize or package for CLI use
- [ ] Create Makefile or \`run.sh\` for setup and run
