# Primary workflow

1. Inspect project instructions, requirements and relevant source. Handle a small well-understood task directly. For complex changes, identify acceptance criteria, dependencies and risks first.
2. Distinguish the requested stage: brainstorming compares options; planning writes the overview and phase files; diagnosis and testing report by default. Implement only when the request authorizes that stage.
3. For requested implementation plans, use `kit-plan`. Persist `plans/YYYYMMDD-HHmm-<topic>/plan.md` plus separate phase files, unless inline-only output is requested. A read-only planner returns per-file contents for the coordinator to write and verify.
4. When following an existing plan, read its overview and the relevant phases, execute pending work in dependency order and preserve unrelated user changes. Update checkboxes/status only after acceptance evidence confirms completion.
5. Run relevant tests/type/build checks, review the diff and inspect material failures. Delegate substantial independent work when useful and available; otherwise perform the same stages sequentially.
6. Reconcile affected existing documentation and plan progress, and hand off changed paths, actual check outcomes, pending work and risks. Commit, push, publish or deploy only within the user's authorization.

Preserve existing API contracts and backward compatibility. Document intended breaking changes and the migration path before changing consumers. Load the overview and only the phase currently being executed; keep verified progress and substantial worker reports traceable to the active plan.
