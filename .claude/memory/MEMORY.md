# neb-x Project Memory — Index

Durable facts about this hackathon entry. One file per topic. Last reconciled 2026-09-18.

- [Problem Statement 3 — Train Condition Monitoring](problem-statment.md) — **start here.** The
  four subsystems, their metrics, the three compulsory deliverables, the prediction schemas, and
  how the Overall vs Average scores work.
- [Project Structure and Code Conventions](project-structure.md) — the file tree and the twelve
  rules any new file must follow. **Read before writing code.**
- [Three-Person Work Split](team-split.md) — who owns which subsystem, the five checks that
  keep the split from costing score. **Read before starting work.**
- [How to Work With Me](prompting.md) — ask before touching files; plan in chat first.

Per-subsystem build plans. The phases, what the data actually says, and what has already been
ruled out — **read the one for your subsystem before writing any of its code:**

- [Rail Corrugation Build Plan](rail-plan.md) — ten phases for `src/rail/`, all measured against
  the data. Phases 0–6 done; **Phase 8 next, and the order changed to 8 → 9 → 7** because nothing
  is banked above 0.33 until a checkpoint exists. 0.758 macro F1 at 10×5, and **the estimator is a
  closed question** — a linear baseline ties it and five booster hyperparameters all fail to beat
  the default. The per-side binary framing is refuted too. All the remaining score is in features.

Per-person change logs. Append an entry when a change crosses a package boundary:

- [Wayne](wayne.md) — what Wayne changed, newest first.
- [Jermaine](jermaine.md) — what Jermaine changed, newest first.
- [Jou](jou.md) — what Jou changed, newest first.

## Sources of truth, in order

When these disagree with each other or with memory, the higher one wins:

1. `docs/<subsystem>/info_kit.md` — the authoritative definition of that subsystem's task, schema
   and scoring formula. The summary tables in memory are convenience only.
2. `docs/problem_statement.md` — deliverables, submission structure, overall rubric.
3. `reference/submission_format/*.csv` — the prediction file schema, as shipped.
4. `.claude/memory/` — our decisions and the reasoning behind them.
