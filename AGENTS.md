# Agent Guidelines

To log pipeline step outcomes to Supabase, use `backend/db/pipeline_logger.py`.
Insert one row per run with fields:
- `step_name`
- `link_id`
- `movie_id`
- `attempt_number`
- `status` (`"success"` or `"failure"`)
- `result_data` or `error_message`
- `timestamp` (defaults to `now()`)

Use the `log_step_result` helper to perform the insert and avoid duplicates.
