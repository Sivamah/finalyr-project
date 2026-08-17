r"""
check_results_consistency.py — research-integrity guard for evaluation output.

Run AFTER regenerating results:

    cd backend
    .venv\Scripts\activate
    python scripts\check_results_consistency.py

It answers four questions that a viva examiner can ask, and that no test
currently covers:

  C1  Does any published metric duplicate another?
      (R3: "Avg waiting (min)" and "Avg delay (min)" were the same field,
       printed as two independent results with identical values in every row.)

  C2  Is any dispatch-based count labelled as a completion?
      (R4: `requests_completed` counts requests that reached "Assigned" —
       dispatched, not finished.)

  C3  Do the numbers quoted in the IEEE paper draft still match the generated
      tables?  Hand-written prose drifts from regenerated output silently.

  C4  Were the results produced by the current code?
      Compares result-file mtimes against the engine source files whose
      output they depend on.  P0-3 changed `Trip.max_delay_min` and
      `total_duration_min`; any result older than that fix is stale.

Exit code 0 only if every check passes.  Nothing is modified.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
RESULTS = BACKEND / "evaluation" / "results"
PAPER = REPO / "docs" / "04_IEEE_Paper_Draft.md"

# Engine files whose behaviour determines the recorded trip metrics.
ENGINE_SOURCES = [
    BACKEND / "app" / "dmfe" / "optimizer.py",        # P0-3, P1-4
    BACKEND / "app" / "dmfe" / "pipeline.py",         # P0-1, P0-2
    BACKEND / "app" / "dmfe" / "driver_selection.py",  # P1-5
    BACKEND / "app" / "dmfe" / "decision_engine.py",
    BACKEND / "evaluation" / "framework.py",          # R3, R4
]

# Labels that must never appear in published output.
FORBIDDEN_LABELS = {
    "avg waiting": (
        "R3 — waiting time is not measured independently. `avg_waiting_min` "
        "is an alias of `avg_delay_min` (both are mean(trip.max_delay_min)); "
        "the driver ETA to first pickup is never persisted on the Trip row, "
        "so dispatch-to-pickup waiting cannot be reconstructed."
    ),
    "waves completion": (
        "R4 — this counts requests at status Assigned or Completed, i.e. "
        "DISPATCHED. Label it as a dispatch rate."
    ),
    "requests completed": (
        "R4 — `requests_completed` counts Assigned (dispatched) requests. "
        "Label it 'Requests dispatched'."
    ),
}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{('  — ' + detail) if detail else ''}")


def head(title: str) -> None:
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


# ── C1: duplicate metrics ───────────────────────────────────────────────────

def parse_markdown_rows(path: Path) -> dict[str, list[tuple[str, ...]]]:
    """label -> list of value tuples, one per row bearing that label."""
    rows: dict[str, list[tuple[str, ...]]] = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- :"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        label = cells[0]
        if not label or label.lower() in ("metric", "workload", "id"):
            continue
        rows.setdefault(label, []).append(tuple(cells[1:]))
    return rows


def c1_duplicate_metrics() -> None:
    head("C1 — duplicate published metrics")
    tables = RESULTS / "ieee_tables.md"
    if not tables.exists():
        check("ieee_tables.md present", False, f"missing: {tables}")
        return
    rows = parse_markdown_rows(tables)

    # Fingerprint each label by the full sequence of its value rows.
    fingerprints: dict[tuple, list[str]] = {}
    for label, value_rows in rows.items():
        if len(value_rows) < 2:
            continue          # single-row labels are not comparable series
        fingerprints.setdefault(tuple(sorted(value_rows)), []).append(label)

    dupes = {fp: labels for fp, labels in fingerprints.items() if len(labels) > 1}
    if dupes:
        for _fp, labels in dupes.items():
            print(f"      identical series: {' == '.join(labels)}")
        check(
            "no two published metrics carry identical value series",
            False,
            f"{len(dupes)} duplicate group(s) — one measurement is being "
            f"reported as several independent findings",
        )
    else:
        check("no two published metrics carry identical value series", True,
              f"{len(rows)} labels checked")


# ── C2: dispatch mislabelled as completion ──────────────────────────────────

def c2_forbidden_labels() -> None:
    head("C2 — dispatch counts labelled as completions")
    targets = [
        RESULTS / "ieee_tables.md",
        RESULTS / "ieee_tables.tex",
        RESULTS / "research_summary.md",
        RESULTS / "final_metrics_table.md",
        RESULTS / "admfe_comparison_metrics.csv",
        RESULTS / "final_statistical_summary.csv",
        PAPER,
    ]
    hits: list[str] = []
    for path in targets:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for needle, why in FORBIDDEN_LABELS.items():
            if needle in text:
                hits.append(f"{path.name}: '{needle}' — {why}")
    if hits:
        for h in hits:
            print(f"      {h}")
    check("no forbidden metric label in published output", not hits,
          f"{len(hits)} occurrence(s)" if hits else "")


# ── C3: paper prose vs generated tables ─────────────────────────────────────

def c3_paper_matches_tables() -> None:
    head("C3 — IEEE paper draft vs generated tables")
    if not PAPER.exists():
        check("paper draft present", False, f"missing: {PAPER}")
        return
    paper = PAPER.read_text(encoding="utf-8", errors="replace")

    csv_path = RESULTS / "admfe_comparison_metrics.csv"
    if not csv_path.exists():
        check("admfe_comparison_metrics.csv present", False, "cannot cross-check")
        return

    table_numbers: set[str] = set()
    with csv_path.open(encoding="utf-8", errors="replace") as fh:
        for row in csv.reader(fh):
            for cell in row:
                cell = cell.strip().rstrip("%")
                if re.fullmatch(r"[-+]?\d+\.\d+", cell):
                    table_numbers.add(f"{abs(float(cell)):.1f}")

    # Percentages the paper states in its results section.
    quoted = re.findall(r"[−+-]?(\d+\.\d)%", paper)
    if not quoted:
        check("paper quotes numeric results", False, "no percentages found")
        return

    missing = sorted({q for q in quoted if q not in table_numbers})
    # A tolerance: the paper legitimately rounds and derives some figures.
    ratio = 1.0 - (len(missing) / len(set(quoted)))
    ok = ratio >= 0.5
    if missing:
        print(f"      quoted in the paper but not found in the CSV: "
              f"{', '.join(missing[:15])}{' …' if len(missing) > 15 else ''}")
    check("paper percentages traceable to the generated tables", ok,
          f"{ratio * 100:.0f}% traceable ({len(set(quoted))} distinct figures)")
    if not ok:
        print("      → after regenerating results, re-read §V of the paper and "
              "update every quoted figure. Prose does not regenerate itself.")


# ── C4: staleness ───────────────────────────────────────────────────────────

def c4_staleness() -> None:
    head("C4 — were these results produced by the current engine?")
    if not RESULTS.exists():
        check("results directory present", False, str(RESULTS))
        return
    result_files = [p for p in RESULTS.rglob("*")
                    if p.is_file() and p.suffix in (".json", ".csv", ".md", ".tex")]
    if not result_files:
        check("results present", False, "no result files")
        return

    newest_source = max(
        ((p, p.stat().st_mtime) for p in ENGINE_SOURCES if p.exists()),
        key=lambda t: t[1], default=(None, 0.0),
    )
    oldest_result = min(((p, p.stat().st_mtime) for p in result_files),
                        key=lambda t: t[1])
    newest_result = max(((p, p.stat().st_mtime) for p in result_files),
                        key=lambda t: t[1])

    src_path, src_mtime = newest_source
    stale = [p for p in result_files if p.stat().st_mtime < src_mtime]

    print(f"      newest engine source : {src_path.name if src_path else '?'}")
    print(f"      oldest result file   : {oldest_result[0].name}")
    print(f"      newest result file   : {newest_result[0].name}")
    check("every result file postdates the newest engine change", not stale,
          f"{len(stale)} of {len(result_files)} result file(s) are older than "
          f"{src_path.name if src_path else 'the engine'} — regenerate"
          if stale else "")
    if stale:
        print("      → P0-3 changed Trip.max_delay_min and total_duration_min, "
              "which feed avg_delay_min / avg_travel_time_min. Results older "
              "than that fix are not comparable with post-fix results.")


def main() -> int:
    print(f"A-DMFE results consistency check — {REPO}")
    c1_duplicate_metrics()
    c2_forbidden_labels()
    c3_paper_matches_tables()
    c4_staleness()

    head("SUMMARY")
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    print()
    print(f"  {len(results) - len(failed)} passed, {len(failed)} failed")
    if failed:
        print()
        print("  Regenerate with:")
        print("    python -m evaluation.run_admfe_experiments")
        print("    python -m evaluation.make_admfe_report")
        print("    python -m evaluation.final_validation")
        print("  then re-run this check and update the paper prose by hand.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
