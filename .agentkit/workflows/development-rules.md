# development-rules

Keep changes focused, use clear paths and preserve user configuration. Prefer scoped search. Extract cohesive modules when useful. Run appropriate validation and report untested behavior. Never treat placeholder checks as proof.

## Engineering principles

- **YAGNI (You Aren't Gonna Need It):** Implement the current requirements; avoid speculative features, dependencies and abstractions.
- **KISS (Keep It Simple, Stupid):** Prefer the simplest clear solution that satisfies the requirements; add complexity only when justified.
- **DRY (Don't Repeat Yourself):** Reuse established logic and keep one source of truth. Extract shared code when duplication reflects the same responsibility; avoid premature abstractions.

## Delivery checks

Inspect existing patterns before editing; use descriptive paths and cohesive modules. Keep changes scoped and avoid source changes that only silence errors. Never replace a meaningful type with `any` or skip a failing check just to claim success.

Before a commit, review the diff and run applicable lint/verification. Before pushing, run the required tests and inspect material failures. Keep credentials, real environment files, caches and unrelated changes out of the commit. Use conventional commit headers and respect the user’s publishing scope.

Prefer descriptive kebab-case names for new project files and cohesive implementation modules around 200 lines where practical. Split on real responsibilities rather than creating artificial fragments, and preserve established/upstream resource filenames. Keep commit/PR text free of generated agent/model signatures or co-author trailers unless the user requests them.
