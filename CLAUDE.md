# CLAUDE.md

## Project

TVTools predicts trade entry points for TradingView symbols such as XAUUSD and other xxxUSD pairs. A signal may be **long or short**. Horizons:
- **Intraday** (current scope): opened and closed the same trading day; no position is held overnight.
- **Swing** (deferred): held for several days. Postponed until the account grows; keep `horizon` as a signal field so it can be added back without redesign.

Treat direction (long/short) and horizon as separate dimensions of every signal; don't hard-code a single symbol, direction or timeframe.

## Current state

Phase 1 foundation uses Python 3.12 with `uv`. Install `uv` and Python 3.12, then run `uv sync --python python3.12` in this directory.

- Build: `uv build`
- Lint: `uv run ruff check .`
- Type check: `uv run mypy src`
- Full test run: `uv run pytest`
- CLI smoke check: `uv run python -m tvtools version`

Historical data is planned from Dukascopy M1 bid/ask into Parquet in Phase 2. Store broker and Telegram credentials only in environment variables or an ignored `.env` file; `.env.example` lists the names. New York time defines trading days and sessions, while stored timestamps are UTC.

<!-- agentkit:begin -->
<!-- Managed by AgentKit Engineer. Put project-specific instructions outside this block; edits inside are kept but stop receiving AgentKit updates. -->
# AgentKit Engineer

## How to work

- Small, well-understood change: do it directly. Larger work: state the acceptance criteria first, then plan → implement → test → review.
- Respect the requested stage. Brainstorm compares options, plan writes plans, debug diagnoses, test runs checks, review reports findings. None of these edit application code unless the user also asked for a fix or implementation.
- Delegate only independent, substantial work: `scout` to locate code, `researcher` for external facts, `planner`, `tester`, `code-reviewer`, `debugger`. Give each one the objective, paths, constraints and expected output. Without delegation, do the same stages yourself.
- Load only the skills the task needs. Skill resources and scripts resolve relative to the installed skill directory, not the shell directory. Check the version the project actually uses before applying a bundled API example.

## Workflows

Invoke `kit-plan`, `kit-implement`, `kit-debug`, `kit-fix`, `kit-test` and `kit-review` (Codex `$kit-plan`, Claude `/kit-plan` or the installed aliases). Use `kit-tdd` only when TDD is selected and the quality pack is installed.

Plans live in `plans/YYYYMMDD-HHmm-<topic>/`: a `plan.md` overview plus one `phase-NN-<name>.md` per phase, unless the user wants the plan inline. When executing a plan, read the overview and the current phase only. Tick todos and update statuses only after their acceptance checks pass. Workflow details are in `.agentkit/workflows/`.

## Before saying "done"

1. Run the project's real test, type-check and build commands for what you changed, and read the output.
2. Report each command and its result. Say explicitly which checks failed, were skipped or could not run. Never present a skipped check as passing.
3. Review your own diff for unrelated changes, debugging leftovers and secrets.
4. Hand off: changed paths, checks run, remaining risks.

Preserve existing project instructions, user edits, configuration and public APIs. Never silence errors with `any`, broad casts, skipped tests or suppression comments. Commit, push, publish or deploy only when the user asks.

## Principles

YAGNI: build only what is required now. KISS: choose the simplest solution that works. DRY: keep one source of truth, but do not abstract prematurely.
<!-- agentkit:end -->
