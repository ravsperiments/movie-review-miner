from prometheus_client import Counter, Gauge, Histogram

# === LLM request throughput & usage metrics ===
LLM_REQUEST_COUNT = Counter(
    'llm_requests_total',
    'Total number of LLM requests',
    ['provider'],
)
LLM_REQUESTS_IN_FLIGHT = Gauge(
    'llm_concurrent_requests',
    'Number of in-flight LLM requests',
    ['provider'],
)
LLM_PROMPT_LENGTH = Histogram(
    'llm_prompt_length_chars',
    'Length in characters of the prompt sent to LLM',
    ['provider'],
)
LLM_PROMPT_TOKENS = Histogram(
    'llm_prompt_tokens',
    'Number of prompt tokens sent to LLM',
    ['provider'],
)
LLM_COMPLETION_TOKENS = Histogram(
    'llm_completion_tokens',
    'Number of completion tokens returned by LLM',
    ['provider'],
)
LLM_TOTAL_TOKENS = Histogram(
    'llm_total_tokens',
    'Total tokens (prompt + completion) for LLM requests',
    ['provider'],
)