# `data/` — raw datasets, copied verbatim

Source: [aochinwen/NebulaX-Hackathon-ProblemStatement](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement),
folder `PS3/02_Datasets/`. Copied 2026-09-18; 433 files, ~6 GB. **Gitignored** — re-copy from a
clone of that repo rather than committing it.

| Here | Upstream |
|---|---|
| `data/door/` | `PS3/02_Datasets/Door/` |
| `data/acv/` | `PS3/02_Datasets/ACV/` |
| `data/rail/` | `PS3/02_Datasets/Rail_Corrugation/` |
| `data/shm/` | `PS3/02_Datasets/SHM/` |

```
data/
├── door/  Train.csv · Train_Segments_Answer.csv · Test.csv   (Test is one continuous stream)
├── acv/   Train_Labels.csv · train/ 6 .xlsx · test/ 1 .xlsx
├── rail/  Train_Labels.csv · train/ 272 .csv · test/ 68 .csv
└── shm/   Train_Labels.csv · train/ 64 .csv  · test/ 16 .csv
```

**Never rename a file under `test/`.** The `file_id` column of `acv_predictions.csv`,
`rail_predictions.csv` and `shm_predictions.csv` must be the source file name including its
extension, exactly as the organisers shipped it. Only the directory names were lowercased in the
copy (`Train/` → `train/`, `Test/` → `test/`); every file name is untouched.
