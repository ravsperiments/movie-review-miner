# CLAUDE.md - Project Instructions

## Project Overview
Movie Review Miner: A 3-stage data pipeline (CRAWL → EXTRACT → ENRICH) that scrapes, processes, and analyzes movie reviews using LLMs.

## Quick Reference

### Running the Pipeline
```bash
# From project root
cd /Users/ravi/Documents/Projects/movie-review-miner

# Run specific stages
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --stage crawl
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --stage extract --limit 10
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --stage enrich

# Test mode (uses test.db instead of local.db)
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --mode test --stage extract
```

### Running Eval System
```bash
# Create sample batch
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.sampler --size 100

# Run models on batch
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.model_runner --batch latest

# Judge outputs
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.judge --batch latest

# View results
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.view <batch_id>
```

### Viewing Database
```bash
# View local.db contents
python data/view_db.py

# Direct SQLite queries
sqlite3 data/local.db "SELECT COUNT(*) FROM pages"
sqlite3 data/eval.db ".tables"
```

## Code Style & Conventions

### Python
- Python 3.11+ with type hints
- Async/await for I/O operations (asyncio-based pipeline)
- Pydantic models for LLM response validation
- Instructor library for structured LLM outputs

### Project Structure
```
review_aggregator/
├── critics/       # Critic-specific scrapers (baradwajrangan.py)
├── db/            # Database queries (SQLite via sqlite_client.py)
├── eval/          # Evaluation system (sampler, model_runner, judge, view)
├── llm/           # LLM client & prompts
│   ├── client.py  # Unified Instructor-based client
│   ├── schemas.py # Pydantic models for LLM responses
│   └── prompts/   # Versioned prompts (process_review_v1.py, etc.)
├── pipeline/      # Pipeline orchestrators
└── utils/         # Logging, helpers
```

### LLM Model Format
Models use `provider/model-name` format:
- `anthropic/claude-sonnet-4-20250514`
- `openai/gpt-4o`
- `google/gemini-2.0-flash`
- `groq/llama-3.1-70b-versatile`

### Database Schema (3 tables)
- `pages`: Scraped pages with parsed content and LLM extraction results
- `critics`: Reviewer metadata
- `movies`: TMDB-enriched movie data

## IMPORTANT Rules

1. **Always use PYTHONPATH**: Run Python scripts with `PYTHONPATH=. .venv/bin/python` from project root
2. **Virtual environment**: Use `.venv/bin/python`, not system Python
3. **Database files**: SQLite databases are in `data/` folder (local.db, test.db, eval.db)
4. **No secrets in code**: API keys are in `review_aggregator/.env`
5. **Prompt versioning**: New prompts go in `llm/prompts/` with version suffix (e.g., `_v2.py`)

## Testing Changes

Before committing, verify with:
```bash
# Dry run extract (no DB writes)
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --stage extract --dry-run --limit 3

# Run eval on golden set
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --mode eval --model anthropic/claude-sonnet-4-20250514
```

## Common Issues

### "ModuleNotFoundError"
Always run with `PYTHONPATH=.` from project root

### "No module named 'instructor'"
Activate venv: `source .venv/bin/activate` or use `.venv/bin/python`

### LLM rate limits
Reduce concurrency: `--concurrency 2`
