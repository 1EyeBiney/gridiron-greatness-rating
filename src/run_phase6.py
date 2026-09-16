"""
Phase 6 driver: computes the query tables and generates the static site.
See src/queries.py and src/build_site.py for the actual work; this is
just the single entry point matching the other phases' run_phaseN.py
convention.

Run from the repo root: `python src/run_phase6.py`.
"""
from pathlib import Path

from build_site import render_all
from queries import build_all_queries

REPO = Path(__file__).resolve().parents[1]


def main():
    print("Computing query tables...")
    out_dir = REPO / "data" / "processed" / "queries"
    out_dir.mkdir(exist_ok=True)
    for name, table in build_all_queries().items():
        table.to_csv(out_dir / f"{name}.csv", index=False)
    print(f"Wrote {len(list(out_dir.glob('*.csv')))} query CSVs to {out_dir}")

    print("Building the static site...")
    render_all()


if __name__ == "__main__":
    main()
