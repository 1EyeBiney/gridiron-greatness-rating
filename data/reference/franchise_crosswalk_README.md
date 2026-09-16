# Franchise crosswalk

Maps every team code seen in either raw source, for every season, to one stable
`franchise_id` (32 total for the 1970-present era, matching the current NFL).
Codes not listed here map to themselves (identity - no relocation or naming
difference between the two raw sources).

Franchise continuity rules applied, matching NFL's own historical position and
Pro Football Reference's convention (needed for the Phase 1 SRS reproduction
check to line up team-by-team):

- Colts (BAL 1953-1983 -> IND 1984-present): one continuous franchise, coded
  IND throughout by FiveThirtyEight; nflverse only starts in 1999 so this only
  matters for the pre-1999 slice, no crosswalk entry needed there.
- Cardinals (Chicago -> St. Louis 1960 -> Arizona 1988): one continuous
  franchise, coded ARI throughout by FiveThirtyEight.
- Rams (LA -> St. Louis 1995-2015 -> LA 2016-present): one continuous
  franchise. nflverse splits this into LA/STL; both map to franchise_id LAR.
- Raiders (Oakland -> LA 1982-1994 -> Oakland -> Las Vegas 2020-present): one
  continuous franchise. nflverse splits this into OAK/LV; both map to OAK.
- Chargers (LA -> San Diego 1961-2016 -> LA 2017-present): one continuous
  franchise. nflverse splits this into SD/LAC; both map to LAC.
- Browns/Ravens (1996 split): the NFL ruled the Browns' history, name, and
  records stayed in Cleveland; the Baltimore franchise that started play in
  1996 is a SEPARATE, new franchise (the Ravens), not a relocated Browns. The
  Browns paused 1996-1998 and resumed as the same franchise in 1999. Both raw
  sources already encode it this way (CLE has a 1996-1998 gap; BAL starts in
  1996) - no crosswalk entry needed, this note just documents that the gap is
  intentional and must not be "fixed" by treating CLE and BAL as one entity.
- Oilers/Titans (Houston -> Tennessee 1997, renamed Titans 1999): one
  continuous franchise, coded TEN throughout by FiveThirtyEight, distinct
  from the Houston Texans expansion franchise (HOU, 2002-present).
- Washington: name changes (Redskins / Football Team / Commanders) are the
  same franchise throughout; nflverse codes it WAS, FiveThirtyEight codes it
  WSH. Standardized on WSH.

Not yet built: a team-season conference/division table (needed for the
Conference Strength Index in Phase 5 and for div_game validation before
1999). Tracked as an open item - see docs/BUILD_PLAN.md.
