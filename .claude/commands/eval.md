# Run Evaluation

Run the model evaluation system.

## Instructions

Based on $ARGUMENTS, run one of these workflows:

### Sample (create new batch)
```bash
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.sampler --size 100
```

### Run Models
```bash
# Run all configured models
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.model_runner --batch latest

# Run specific model
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.model_runner --models anthropic/claude-sonnet-4-20250514 --batch latest
```

### Judge
```bash
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.judge --batch latest
```

### View Results
```bash
PYTHONPATH=. .venv/bin/python -m review_aggregator.eval.view <batch_id>
```

### Full Eval Pipeline
If user says "full" or "all", run: sample → model_runner → judge → view

## User Request
$ARGUMENTS
