# Phase 1 exit check: SRS reproduction vs. Pro Football Reference

## 1975
Teams compared: 26
Max abs difference: 0.049
Mean abs difference: 0.0203
Largest discrepancies: {'DEN': np.float64(0.049), 'KC': np.float64(0.047), 'DAL': np.float64(0.044)}

## 1985
Teams compared: 28
Max abs difference: 0.050
Mean abs difference: 0.0269
Largest discrepancies: {'IND': np.float64(0.05), 'CIN': np.float64(0.048), 'OAK': np.float64(0.044)}

## 1995
Teams compared: 30
Max abs difference: 0.050
Mean abs difference: 0.0301
Largest discrepancies: {'SEA': np.float64(0.05), 'LAR': np.float64(0.048), 'TB': np.float64(0.047)}

## 2005
Teams compared: 32
Max abs difference: 0.047
Mean abs difference: 0.0216
Largest discrepancies: {'BUF': np.float64(0.047), 'LAR': np.float64(0.045), 'SF': np.float64(0.045)}

## 2015
Teams compared: 32
Max abs difference: 0.049
Mean abs difference: 0.0300
Largest discrepancies: {'CHI': np.float64(0.049), 'LAC': np.float64(0.049), 'IND': np.float64(0.049)}

## Overall (all 5 seasons, 148 team-seasons)
Max abs difference: 0.050 points of SRS
Mean abs difference: 0.0259 points of SRS
RMS difference: 0.0297

Differences at this magnitude (well under 0.1 points in almost all cases) are
consistent with rounding in PFR's displayed values and/or minor rounding in our
own float arithmetic, not a data or methodology error. EXIT CHECK: PASS.
