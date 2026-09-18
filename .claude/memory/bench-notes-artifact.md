---
name: bench-notes-artifact
description: Published bench-notes page for Door and ACV — the verified figures, and the CSV copies of every ACV workbook.
metadata:
  type: reference
---

# Door & ACV Bench Notes

Published page: https://claude.ai/code/artifact/42064246-ac6a-45e2-b45d-61239af041e1

Every figure is recomputed from `data/`, not copied from notes. Covers Door's exact segmentation,
the raw-vs-normalised current separation (the before/after pair that argues for per-stream
normalisation), the current-vs-stroke profiles, all 38 test cycles with provisional calls, ACV's
per-car temperature deltas across all 7 files, and the trap table.

Source lives at `outputs/explore/reference.html` — regenerate by re-running the probe scripts and
re-injecting `data.json`. Republish to the same URL by passing that file path again.

**Browsable data copies:** `outputs/explore/acv/*.csv` is every ACV workbook converted to CSV
(including the 483-column case 04), and `outputs/explore/door/` holds the door files. Use these with
a CSV viewer instead of Excel. `outputs/` is gitignored and fully regenerable.

See also: [[jouyuan]].
