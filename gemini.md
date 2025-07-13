## Workflow Guidelines for Making Code Changes

### Always Work in a New Branch
Before making any code changes, always create a new Git branch using a clear and descriptive naming convention.

**Branch Naming Suggestions** (use a prefix based on the type of change):

- `fix/short-description` – for bug fixes
- `feature/short-description` – for new features
- `refactor/short-description` – for code cleanups or structure changes
- `chore/short-description` – for minor, non-functional updates

**Examples**:

- `fix/crawler-timeout-bug`
- `feature/add-tmdb-enrichment`
- `refactor/clean-db-utils`

Each branch should focus on only one logical change or set of related changes.
If you're making unrelated changes, create a separate branch for each.

### Implementation
- Always share an implementation plan before you start making Changes
- Add compheresntive docuentation and comments inline in the code

### Committing and Merging

After completing and testing your changes:
- update tasks.md
- provide a bullet point summary of changes done under the current date. If the current date section doesn;t exist create one.
- follow the formatting elsewhere in the doc

- After updating tasks.md, use a descriptive commit message in this format:
`<type>: <concise summary>`
`<detailed description of the change>`

**Example**:
```
fix: handle missing sentiment key in classification

Added a check to skip entries without 'sentiment' key, preventing classification errors on edge cases.
```

**Commit types**:

- `fix:` – bug fixes
- `feature:` – new features
- `refactor:` – refactoring without behavior change
- `chore:` – maintenance and non-functional changes

#### Merge and Push

- Merge the branch into `main`
- Delete the branch locally and remotely
- Push the updated `main` branch:

```
git push origin main
```

### Running Crawler Scripts
For any crawler-related scripts, always run them from the project root (`movie-review-miner`) after activating the virtual environment:

**Activate venv**:
```
source .venv/bin/activate
```

**Run script from parent directory**:
```
python3 -m crawler.<script_name>
```

**Example**:
```
python3 -m crawler.pipeline.val_step1_classify_reviews
```

---

Keep changes focused, commits clean, and testing thorough. This will help keep the repo stable and collaborative.

crawler/
├── __pycache__/            # Python bytecode cache
├── .venv/                  # Python virtual environment (should be excluded from version control)
├── db/                     # Database helpers and SQL logic
├── failures/               # Logs or records of failed processing
├── llm/                    # LLM-related functions or prompts
├── logs/                   # Log files from crawler runs
├── pipeline/               # Core data pipeline scripts and processors
├── scraper/                # Scraping logic for gathering review/blog data
├── tasks/                  # Task definitions (e.g., enrichment, classification)
│   └── __pycache__/
├── tests/                  # Unit tests and test utilities
├── tmdb/                   # TMDb API helpers for metadata enrichment
├── utils/                  # General-purpose utility functions

# Root-Level Files
.env                        # Environment variables (not checked in)
.gitignore                 # Files and folders to ignore in git
.python-version            # Python version for tools like pyenv
config.py                  # Project-level configuration settings
debug_page_1.html          # HTML page for debugging or offline analysis
README.md                  # Project overview and instructions
requirements.txt           # List of Python dependencies
reviewers.py               # Reviewer-related logic or processing
run_pipeline.py            # Entry point to run the full data pipeline
tasks.md                   # Task documentation or process instructions
