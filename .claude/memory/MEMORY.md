# neb-x Project Memory — Index

Durable facts about this hackathon entry. One file per topic. Last reconciled 2026-09-19 (rail only;
the door, ACV and SHM entries were last checked 2026-09-18).

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
  the data. **Rail is done: all ten phases closed, 0.750 ± 0.114 macro F1 / 0.757 pooled submitted**,
  not just measured, with the 68 held-out files running through the app and `explain.py` drawing why.
  **Both searches are closed** — the estimator (a linear baseline ties it, five hyperparameters fail)
  and now the features (Phase 7 refuted all five candidate blocks and shipped a *narrowing*, 342 → 228
  columns, for the same score and no change to a single held-out call). Two findings there are worth
  borrowing before any other subsystem tunes anything: **36 columns of shuffled noise buy +0.012 macro
  F1 and +0.027 on the rare class**, so an added block has to beat its own shuffled control; and three
  of five candidates gained on the full set while losing on the honest subset. Side I is still the
  weakest class at 0.515.

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
