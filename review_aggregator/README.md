# Movie Review Miner - Crawler

A comprehensive pipeline for mining and processing movie reviews from critic websites, with LLM-powered classification and cleaning capabilities.

## Architecture Overview

The crawler is organized into several key components:

### 📁 Directory Structure

```
crawler/
├── db/                     # Database operations and queries
├── eval/                   # Model evaluation and testing
├── llm/                    # LLM integrations and processing
│   ├── prompts/           # System and user prompts
│   ├── reconcile_llm_output/  # Output reconciliation logic
│   └── schemas.py         # Pydantic models
├── pipeline/              # Pipeline orchestration modules
├── scraper/               # Web scraping functionality
├── tmdb/                  # TMDB API integration
├── utils/                 # Utility functions and helpers
└── run_pipeline.py        # Main pipeline entry point
```

### 🔄 Pipeline Stages

1. **Crawl Stage**
   - Fetch review links from configured sources
   - Parse review content from web pages
   - Store raw review data

2. **Validation Stage**  
   - Classify content as reviews using LLMs
   - Clean and improve review titles/summaries
   - Validate output quality with judge models

3. **Enrichment Stage**
   - Generate sentiment analysis
   - Add metadata from TMDB
   - Enhance review data

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Required API keys (see Environment Variables)

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file with:

```env
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# LLM APIs
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
MISTRAL_API_KEY=your_mistral_key
HF_TOKEN=your_huggingface_token
XAI_API_KEY=your_xai_key

# TMDB
TMDB_API_KEY=your_tmdb_key
```

### Running the Pipeline

```bash
# Run complete pipeline
python run_pipeline.py

# Run specific stages
python run_pipeline.py --stage crawl
python run_pipeline.py --stage validate
python run_pipeline.py --stage enrich

# Run with options
python run_pipeline.py --limit 100 --dry-run
```

## 🔧 Key Components

### LLM Integration

The system supports multiple LLM providers:
- **OpenAI** (GPT-4, GPT-3.5)
- **Anthropic** (Claude models)
- **Google** (Gemini)
- **Groq** (Llama models)
- **Mistral AI**
- **Hugging Face**
- **xAI** (Grok)

### Review Processing Pipeline

1. **Classification**: Determine if content is a movie review
2. **Cleaning**: Improve titles and summaries using LLMs
3. **Validation**: Judge model validates cleaning quality
4. **Reconciliation**: Combine primary and judge outputs

### Evaluation Framework

- Model comparison across different LLM providers
- Quality assessment using judge models
- Performance metrics and reporting

## 📊 Monitoring

- Prometheus metrics for LLM usage
- Structured logging with step-by-step tracking
- Pipeline summary reports in JSON format

## 🔍 Development

### Adding New LLM Providers

1. Create wrapper in `llm/` directory
2. Implement `prompt_llm` method
3. Add to controller mappings

### Extending Pipeline Stages

1. Create new orchestrator in `pipeline/`
2. Add to `__init__.py` exports
3. Integrate in `run_pipeline.py`

## 📝 Configuration

Pipeline behavior can be customized through:
- Environment variables
- Command-line arguments  
- Model-specific configurations in orchestrators

## 🚨 Error Handling

- Automatic retries with exponential backoff
- Rate limiting protection
- Comprehensive error logging
- Graceful degradation for optional components
