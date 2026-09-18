# How to Work With Me

Wayne's standing preferences for how this project is driven. Written 2026-09-18.

## Do not modify files unless explicitly told to

**Never create, edit, delete or rename a file until asked for that specific change.** This
includes files that are "obviously" needed next, scaffolding, config, and fixes to problems
discovered in passing. Discovering that something needs changing is not permission to change it.

**Why:** the plan is still being shaped through discussion, and an unrequested edit commits the
project to a decision that has not been made yet. Scaffolding in particular is cheap to write and
expensive to unpick once other files import it — see [[project-structure]], where the layering
only works if each file's layer is decided before it exists.

**How to apply:** answer in chat by default. When a change looks necessary, describe it and wait.
When the instruction is to write one file, write that file and nothing else. If a second file
genuinely has to change for the first to work, say so and ask rather than including it.

## Explain the plan in chat before executing it

Ask for the approach first, then the work. Expect to be asked "how shall we start" and to answer
with a sequence, not a commit.

**Why:** the reasoning is being checked, not just the output.

**How to apply:** lead with the recommendation, keep it short, and stop at the point where the
next step would touch the repo.

## Brevity

Short answers are asked for often and explicitly ("as short as possible", "one summary"). Lead
with the verdict, then the evidence. Cut the survey of options that will not be pursued.

## Ground claims in the actual files

Assertions about the data or the task get checked against `docs/` and `data/` before they are
made, not after. Quote the info kit where it settles a question — it is the authoritative source
(see [[problem-statment]]).

**Why:** an early wrong assumption about a schema or a metric propagates into every model built
on top of it.

See also: [[problem-statment]], [[project-structure]].
