"""Run the whole pipeline: analysis tables, then the site."""
import hfa
import hfa_site as build_site

if __name__ == "__main__":
    hfa.run()
    build_site.render_all()
    print(f"Site generated at {build_site.OUT_DIR}")
