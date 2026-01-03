# Run Pipeline

Execute the movie review mining pipeline.

## Instructions

Parse $ARGUMENTS for options, defaulting to extract stage with limit 10.

### Common Commands
```bash
# Full pipeline
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --stage all

# Just crawl
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --stage crawl

# Extract with specific model
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --stage extract --model anthropic/claude-sonnet-4-20250514 --limit 10

# Dry run (no DB writes)
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --stage extract --dry-run --limit 5

# Test mode
PYTHONPATH=. .venv/bin/python review_aggregator/run_pipeline.py --mode test --stage extract
```

### Arguments
- `crawl` - Run crawl stage
- `extract` - Run extract stage
- `enrich` - Run enrich stage
- `all` - Run all stages
- `dry` or `dry-run` - Don't write to DB
- `test` - Use test.db
- Number (e.g., `5`) - Set limit

## User Request
$ARGUMENTS
