# video/

The pitch video: the manim scene sources, and the stitched result the submission
picks up.

```
video/
├── src/              one file per scene, rendered in filename order
├── out/              demo_video.mp4, the stitched result
├── media/            manim's working tree and its cache, generated
└── requirements.txt  manim, which the root requirements.txt deliberately lacks
```

Only `src/`, `README.md` and `requirements.txt` are committed. Everything else is
generated, or too large for git.

## Rendering

```bash
./scripts/render.sh        # macOS / Linux
scripts\render.bat         # Windows
```

It asks for a manim quality and an fps and takes the defaults on Enter, then renders
every scene in `src/` and stitches them into `out/demo_video.mp4`.

`./submit.sh` copies that file into the submission folder as the `demo_video.<ext>`
the problem statement asks for, preferring it over any loose recording left in
`video/`.

## Adding or reordering a scene

Scenes render in filename order, so the two-digit prefix is the running order. Add
`09_<name>.py` holding one `Scene` subclass; nothing else needs editing.

A scene whose `construct` is still empty renders no video, and the render stops and
names it. That is deliberate: a silently skipped scene is a hole in the cut that
nobody notices until the video is uploaded.

## Requirements

**ffmpeg must be on PATH.** manim renders through it, and the scenes are stitched
with it. `winget install Gyan.FFmpeg`, `brew install ffmpeg`, or `apt install
ffmpeg`.
