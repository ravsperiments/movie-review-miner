# Commit Changes

Create a well-structured git commit for staged changes.

## Instructions

1. Run `git status` and `git diff --cached` to see staged changes
2. If nothing is staged, suggest what should be staged based on recent work
3. Analyze the changes and create a commit message following this format:
   - Type: feat|fix|refactor|chore|docs|test
   - Brief subject line (imperative mood, max 50 chars)
   - Blank line
   - Body explaining the "why" (wrap at 72 chars)
4. Create the commit with the Claude Code signature

## Commit Types
- `feat`: New feature or functionality
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `chore`: Maintenance tasks, cleanup
- `docs`: Documentation only
- `test`: Adding or updating tests

$ARGUMENTS
