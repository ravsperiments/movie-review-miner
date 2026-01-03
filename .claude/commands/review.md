# Code Review

Perform a thorough code review of recent changes or specified files.

## Instructions

1. If $ARGUMENTS is provided, review those specific files
2. Otherwise, review uncommitted changes (`git diff` and `git diff --cached`)
3. Check for:
   - **Bugs**: Logic errors, edge cases, null handling
   - **Security**: SQL injection, command injection, secrets in code
   - **Performance**: N+1 queries, unnecessary loops, memory leaks
   - **Style**: Consistency with project conventions (see CLAUDE.md)
   - **Types**: Missing type hints, incorrect Pydantic models
4. For each issue found:
   - Explain the problem clearly
   - Suggest a specific fix
   - Rate severity: critical / warning / suggestion

## Output Format
```
## Review Summary
- X critical issues
- Y warnings
- Z suggestions

## Critical Issues
### [File:Line] Issue title
Problem: ...
Fix: ...

## Warnings
...

## Suggestions
...
```

$ARGUMENTS
