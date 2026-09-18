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
- [Jou Yuan — Door and ACV](jouyuan.md) — what Jou Yuan owns, the measured data facts behind both
  subsystems, and the design decisions already taken. **Door is scored on accuracy, not macro-F1.**
- [Overfitting Audit](overfitting-audit.md) — what was measured to rule out overfitting on Door and
  ACV, and the two limits the checks do not cover. **Quote these in the write-up.**
- [Door & ACV Bench Notes](bench-notes-artifact.md) — published figures page, plus the CSV copies
  of every ACV workbook under `outputs/explore/`.

## Sources of truth, in order

When these disagree with each other or with memory, the higher one wins:

1. `docs/<subsystem>/info_kit.md` — the authoritative definition of that subsystem's task, schema
   and scoring formula. The summary tables in memory are convenience only.
2. `docs/problem_statement.md` — deliverables, submission structure, overall rubric.
3. `reference/submission_format/*.csv` — the prediction file schema, as shipped.
4. `.claude/memory/` — our decisions and the reasoning behind them.
