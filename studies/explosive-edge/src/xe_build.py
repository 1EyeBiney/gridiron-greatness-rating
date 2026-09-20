"""Run the whole pipeline: analysis tables, then the site. Matches
studies/home-field-advantage/src/hfa_build.py's pattern."""
import xe_analysis_shift
import xe_analysis_teams
import xe_analysis_followups
import xe_site as build_site

if __name__ == "__main__":
    xe_analysis_shift.run()
    xe_analysis_teams.run()
    xe_analysis_followups.run()
    build_site.render_all()
    print(f"Site generated at {build_site.OUT_DIR}")
