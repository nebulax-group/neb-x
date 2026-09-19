"""Build a compact, offline maintenance review folder from assessed findings."""

import csv
from datetime import datetime, timezone
from html import escape
from io import BytesIO, StringIO
import json
import math
import zipfile

from src.common.config import SUBSYSTEM_LABELS

DISCLAIMER = (
    "Decision support for maintenance review. Findings require confirmation under the "
    "operator's procedures; this package is not an LTA approval or fitness-for-service decision."
)
EXCLUSIONS = "Raw sensor recordings, full prediction tables, trained model binaries and application code are not included."


def _csv(records: list[dict]) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(records[0]))
    writer.writeheader()
    for row in records:
        # Filenames can be opened in Excel. Never let one become a formula.
        writer.writerow({key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value) for key, value in row.items()})
    return output.getvalue()


def chart_svg(chart: dict, rows: list[dict]) -> str:
    """Signed horizontal bars, with actual values printed and a visible zero line."""
    values = [float(row["value"]) for row in rows]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Chart evidence contains a non-finite value.")
    low, high = min(0, *values), max(0, *values)
    if high == low:
        high = low + 1
    left, width = 330, 490
    x = lambda value: left + width * (value - low) / (high - low)
    height = 115 + len(rows) * 38
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {height}" role="img" aria-label="{escape(chart["title"], quote=True)}">',
        f'<rect width="960" height="{height}" fill="white"/>',
        '<g font-family="Arial, sans-serif" fill="#122630">',
        f'<text x="20" y="27" font-size="18" font-weight="bold">{escape(chart["title"])}</text>',
        f'<text x="20" y="51" font-size="12">{escape(chart["unit"])}</text>',
        f'<line x1="{x(0):.2f}" x2="{x(0):.2f}" y1="64" y2="{height - 25}" stroke="#70808a"/>',
    ]
    for index, (row, value) in enumerate(zip(rows, values)):
        y = 72 + index * 38
        label = str(row["label"])
        short = label if len(label) <= 40 else label[:37] + "..."
        colour = "#b42318" if row.get("severity") == "danger" else "#956300"
        parts.extend([
            f'<text x="20" y="{y + 19}" font-size="13"><title>{escape(label)}</title>{escape(short)}</text>',
            f'<rect x="{min(x(0), x(value)):.2f}" y="{y}" width="{max(abs(x(value) - x(0)), 1):.2f}" height="26" rx="3" fill="{colour}"/>',
            f'<text x="840" y="{y + 19}" font-size="13">{value:.4g}</text>',
        ])
    parts.append(f'<text x="{x(0):.2f}" y="{height - 5}" text-anchor="middle" font-size="11">0</text>')
    return "".join([*parts, '</g></svg>'])


def _table(records: list[dict]) -> str:
    if not records:
        return "<p>No review findings were selected by this model. Read the scope and limitations below.</p>"
    headers = "".join(f"<th>{escape(key.replace('_', ' '))}</th>" for key in records[0])
    rows = "".join("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row.values()) + "</tr>" for row in records)
    return f'<div class="table-scroll"><table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>'


def build(runs: dict, reference: str = "", prepared_by: str = "", notes: str = "", created_at: datetime | None = None) -> tuple[str, bytes]:
    """Return a ZIP with one folder per completed system, including clear summaries."""
    if not runs:
        raise ValueError("Assess at least one recording before preparing a handoff.")
    now = created_at or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    root = f"maintenance-review-{stamp}"
    overview = [
        "MAINTENANCE REVIEW", f"Prepared: {now.isoformat()}",
        f"Review reference: {reference or 'Not supplied'}", f"Prepared by: {prepared_by or 'Not supplied'}",
        f"Notes: {notes or 'None'}", "", DISCLAIMER, "", EXCLUSIONS,
        "", "SCOPE: latest completed batch per system in this browser session.",
        "Source filenames are identifiers; verify the train, asset and measurement point before action.",
        "Recipients are suggested maintenance roles, not named contacts or verified routing.", "",
    ]
    unassessed = [label for key, label in SUBSYSTEM_LABELS.items() if key not in runs]
    overview.append("Not assessed / unavailable: " + ", ".join(unassessed) if unassessed else "All configured systems assessed.")
    manifest = {"schema_version": 1, "prepared_at": now.isoformat(), "reference": reference, "prepared_by": prepared_by, "notes": notes, "not_assessed": unassessed, "systems": {}}
    sections = []
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key in SUBSYSTEM_LABELS:
            if key not in runs:
                continue
            run = runs[key]
            label = SUBSYSTEM_LABELS[key]
            report = run.report
            manifest["systems"][key] = {"assessed_at": run.assessed_at, "batch_sha256": run.digest, "sources": run.sources, "review_evidence_ready": report is not None}
            if report is None:
                message = f"{label}: assessment exists, but review evidence is incomplete. Do not interpret this as no findings."
                overview.append(message)
                archive.writestr(f"{root}/{key}/README.txt", message + "\n" + (run.report_error or ""))
                sections.append(f"<section><h2>{escape(label)}</h2><p>{escape(message)}</p></section>")
                continue
            count = len(report["findings"])
            manifest["systems"][key]["finding_count"] = count
            overview.extend(["", f"{label}: {report['summary']}", f"Suggested recipient: {report['recipient']}"])
            overview.extend(f"  - {action}" for action in report["actions"])
            text = [label, f"Assessed: {run.assessed_at}", f"Suggested recipient: {report['recipient']}", "", report["summary"], "", "NEXT ACTIONS", *[f"{i}. {action}" for i, action in enumerate(report["actions"], 1)], "", "METHOD", report["method"], "", "LIMITATIONS", *report["limitations"], "", "SOURCE RECORDINGS (not included)", *[f"{s['name']} | SHA-256 {s['sha256']}" for s in run.sources]]
            if not count:
                text.append("\nNo findings CSV or chart is included because no items met this model's review criteria.")
            archive.writestr(f"{root}/{key}/README.txt", "\n".join(text))
            if count:
                archive.writestr(f"{root}/{key}/findings.csv", _csv(report["findings"]))
            images = []
            chart = report.get("chart")
            if chart:
                for start in range(0, len(chart["rows"]), 24):
                    svg = chart_svg(chart, chart["rows"][start:start + 24])
                    archive.writestr(f"{root}/{key}/evidence-{start // 24 + 1:02d}.svg", svg)
                    images.append(svg)
            actions = "".join(f"<li>{escape(action)}</li>" for action in report["actions"])
            limits = "".join(f"<li>{escape(line)}</li>" for line in report["limitations"])
            sections.append(f'<section><h2>{escape(label)}</h2><p class="recipient">Suggested recipient: {escape(report["recipient"])}</p><p>{escape(report["summary"])}</p><h3>Next actions</h3><ol>{actions}</ol>{"".join(images)}{_table(report["findings"])}<h3>Method and limitations</h3><p>{escape(report["method"])}</p><ul>{limits}</ul></section>')
        overview.extend(["", "OPEN FIRST", "Open Report.html in a browser for charts and tables, or Summary.txt for plain text.", "Each system folder has README.txt and, when applicable, findings.csv and evidence charts.", "manifest.json records source filenames, checksums and assessment times for traceability."])
        archive.writestr(f"{root}/Summary.txt", "\n".join(overview))
        archive.writestr(f"{root}/manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        intro = escape("\n".join(overview[:15]))
        missing = escape("Not assessed / unavailable: " + ", ".join(unassessed))
        html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Maintenance review</title>
<style>body{{font:16px/1.5 Arial,sans-serif;color:#122630;background:#f2f5f7;margin:0;padding:24px}}main{{max-width:1100px;margin:auto}}header,section{{background:white;border:1px solid #c6d0d6;border-radius:8px;padding:24px;margin-bottom:24px}}h1,h2{{margin-top:0}}.intro{{white-space:pre-wrap;overflow-wrap:anywhere}}.recipient{{font-weight:bold}}svg{{width:100%;height:auto}}.table-scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #dce3e8;padding:8px;text-align:left;overflow-wrap:anywhere}}th{{background:#edf3f6}}li{{margin-bottom:6px}}@media print{{body{{background:white;padding:0}}section{{break-inside:auto}}.table-scroll{{overflow:visible}}}}</style></head>
<body><main><header><h1>Maintenance review</h1><div class="intro">{intro}</div><p>{missing}</p></header>{''.join(sections)}</main></body></html>'''
        archive.writestr(f"{root}/Report.html", html)
    return f"{root}.zip", buffer.getvalue()
