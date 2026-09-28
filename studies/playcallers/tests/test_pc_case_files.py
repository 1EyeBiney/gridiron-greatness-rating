"""Pins the claims made in the case-file prose (src/pc_case_files.py) to
the tables. Numbers are injected at render time; the sentences built on
them are asserted here."""
import pandas as pd
import pytest

import pc_case_files as cf
import pc_site


@pytest.fixture(scope="module")
def t():
    return pc_site.load_tables()


@pytest.fixture(scope="module")
def k(t):
    return {c["slug"]: c["k"] for c in cf.build_cases(t)}


def z(k, slug, season):
    s = k[slug]["seasons_table"]
    return float(s.loc[s["season"] == season, "z_epa"].iloc[0])


def test_every_case_has_a_record_and_renders(t, tmp_path):
    pc_site.render_all(tmp_path)
    for case in cf.CASES:
        page = tmp_path / "case-files" / f"{case['slug']}.html"
        html = page.read_text(encoding="utf-8")
        assert case["person"] in html and "{{" not in html and ">nan<" not in html and "None" not in html, case["slug"]
    index = (tmp_path / "case-files" / "index.html").read_text(encoding="utf-8")
    assert all(f'{c["slug"]}.html' in index for c in cf.CASES)


def test_shanahan_is_far_better_on_recent_form_than_for_his_career(k):
    s = k["kyle-shanahan"]
    assert s["career"]["rank"] > 15 and s["recent"]["rank"] <= 5
    assert s["early"]["n"] == 6 and s["early"]["mean"] < 0                      # WSH x4, CLE, ATL 2015
    assert list(s["seasons_table"]["franchise"].head(6)) == ["WSH"] * 4 + ["CLE", "ATL"]
    assert s["recent"]["mean"] > 0.8
    assert s["n_qbs"] >= 7 and s["qb_rank"] < s["career"]["rank"]
    assert s["career"]["mean_explosive"] > s["career"]["mean"] and s["career"]["mean_ypp"] > s["career"]["mean"]


def test_bradley_two_halves_in_seattle_and_below_average_since(k, t):
    b = k["gus-bradley"]
    assert b["first_stop"]["franchise"] == "SEA" and b["first_stop"]["n"] == 4
    assert b["first_two"]["mean"] < -1 and b["last_two_of_first"]["mean"] > 0.5
    assert b["after"]["n"] == 6 and b["after"]["mean"] < 0
    after = b["seasons_table"][b["seasons_table"]["season"] > 2012]["z_epa"].tolist()
    assert all(v > 0 for v in after[:2]) and all(v < 0 for v in after[2:])       # two good, four below
    assert k["dan-quinn"]["stop"]["SEA"]["mean"] > b["last_two_of_first"]["mean"]   # better still after he left
    assert len(b["excluded"]) == 2
    assert b["career"]["rank"] > 50


def test_quinn_has_two_excellent_stops_and_one_poor_one(k, t):
    q = k["dan-quinn"]
    assert q["stop"]["SEA"]["mean"] > 2 and q["stop"]["DAL"]["mean"] > 1 and q["stop"]["ATL"]["mean"] < 0
    s = t["playcaller_seasons"]
    d = s[s["unit"] == "defense"].groupby(["person", "franchise"])["z_epa"].agg(["size", "mean"])
    assert d[d["size"] >= 2]["mean"].max() == pytest.approx(q["stop"]["SEA"]["mean"])


def test_quarterback_cases(k):
    r = k["andy-reid"]
    assert abs(r["stop"]["PHI"]["mean"]) < 0.2 and r["stop"]["KC"]["mean"] > 1
    kc = r["seasons_table"]
    smith = kc[(kc["franchise"] == "KC") & (kc["primary_qb_name"] == "Alex Smith")]["z_epa"]
    assert len(smith) >= 3 and smith.mean() > 0.3                                  # "already good with Alex Smith"
    assert r["career"]["share_unverified"] == 1.0 and r["qb_rank"] <= 5
    p = k["sean-payton"]
    assert p["stop"]["NO"]["mean"] > 1 and abs(p["stop"]["DEN"]["mean"]) < 0.3 and p["qb_rank"] > p["career"]["rank"]
    m = k["josh-mcdaniels"]
    assert m["ne"]["n"] >= 12 and m["ne"]["mean"] > 0.9 and m["elsewhere"]["n"] == 2 and m["elsewhere"]["mean"] < 0
    assert m["last"]["season"] == 2025 and m["last"]["z"] > 1
    tm = k["tom-moore"]
    assert tm["career"]["rank"] == 1 and tm["n_stops"] == 1 and tm["n_qbs"] == 1
    basis = tm["seasons_table"].set_index("season")["basis"]
    assert all(basis[y] == "continuity_guess" for y in (2003, 2004, 2005))


def test_one_great_stop_cases(k):
    m = k["mike-martz"]
    assert m["stop"]["LAR"]["mean"] > 0.9 and m["after"]["n"] == 4 and m["after"]["mean"] < -0.5
    assert m["qb_rank"] < m["career"]["rank"]
    mc = k["mike-mccarthy"]
    assert mc["stop"]["GB"]["mean"] > 0.9 and mc["elsewhere"]["mean"] < 0 and mc["elsewhere"]["n"] == 8
    lb = k["dick-lebeau"]
    assert lb["stop"]["PIT"]["n"] >= 10 and lb["stop"]["PIT"]["mean"] > 0.4 and lb["elsewhere"]["mean"] < -0.5
    rm = k["rod-marinelli"]
    assert rm["stop"]["CHI"]["mean"] > 1.5 and rm["after"]["n"] == 7 and rm["after"]["mean"] < 0


def test_reputation_cases(k):
    g = k["jon-gruden"]
    assert g["first_stop"]["franchise"] == "OAK" and g["first_stop"]["mean"] > 1
    assert g["stop"]["TB"]["mean"] < 0 and abs(g["last_stop"]["mean"]) < 0.3
    tb = g["seasons_table"][g["seasons_table"]["franchise"] == "TB"]["primary_qb_name"].nunique()
    assert tb == 5
    s = k["steve-spagnuolo"]
    assert 0 < s["career"]["mean"] < 0.4 and s["career"]["rank"] > 30


def test_better_than_rank_and_travelled(k):
    f = k["vic-fangio"]
    assert f["before2011"]["n"] == 7 and f["before2011"]["mean"] < -0.4 and f["since2011"]["mean"] > 0.4
    assert f["stop"]["SF"]["mean"] > 1 and f["stop"]["PHI"]["mean"] > 1 and f["career"]["seasons"] == 21
    w = k["wade-phillips"]
    assert w["n_stops"] == 6 and w["worst_stop"]["mean"] > 0                       # above average everywhere
    assert z(k, "wade-phillips", 2015) == pytest.approx(w["best_stop"]["mean"])
    v = k["sean-mcvay"]
    assert v["stop"]["LAR"]["n"] == 9 and v["qb_rank"] < v["career"]["rank"]


def test_the_two_who_prompted_the_study(k):
    j = k["ben-johnson"]
    det = [z(k, "ben-johnson", y) for y in (2022, 2023, 2024)]
    assert det == sorted(det) and j["stop"]["CHI"]["mean"] > 0.5                   # "improved each year"
    assert j["career"]["rating"] < j["career"]["mean"] and j["mean_rank"] <= 5
    m = k["mike-macdonald"]
    assert z(k, "mike-macdonald", 2023) > z(k, "mike-macdonald", 2022) + 1
    assert z(k, "mike-macdonald", 2025) > z(k, "mike-macdonald", 2024) + 0.5
    assert m["mean_rank"] <= 3
