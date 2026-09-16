"""
Run every completed phase's pipeline in order. Phase 2 rewrites
data/processed/team_season_ratings.csv from scratch and Phase 3 then adds
the z-score columns to it, so running them out of order (or Phase 2
alone) silently drops Phase 3's output - this is the one entry point that
can't get that wrong.

Run from the repo root: `python src/run_all.py`.
"""
import run_phase2
import run_phase3

if __name__ == "__main__":
    print("=== Phase 2 ===")
    run_phase2.main()
    print("\n=== Phase 3 ===")
    run_phase3.main()
