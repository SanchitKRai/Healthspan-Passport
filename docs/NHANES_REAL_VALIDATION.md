# Real CDC NHANES (1999–2010) & NCHS 2019 Linked Mortality Replication

> **Generated:** `2026-11-28T04:16:25Z`
> **Script:** [`backend/scripts/nhanes_real/build_cohort.py`](../backend/scripts/nhanes_real/build_cohort.py) (uses `calculate_phenoage` imported directly from [`backend/app/core/phenoage.py`](../backend/app/core/phenoage.py))
> **Raw Data JSON Output:** [`data/results/nhanes_real_results.json`](../data/results/nhanes_real_results.json)

---

## 1. Cohort & Participant Exclusion Flow

| Exclusion Step | Remaining $N$ | Excluded $N$ |
| :--- | ---: | ---: |
| 1. Total participants in NHANES 1999-2010 Demographics (DEMO*) | 62,160 | 0 |
| 2. Adults aged 20-84 excluding top-coded ages (>=85 in 1999-2006; >=80 in 2007-2010) | 30,798 | 31,362 |
| 3. Mortality-eligible (ELIGSTAT == 1) with non-missing MORTSTAT and PERMTH_EXM >= 0 | 29,311 | 1,487 |
| 4. Complete cases across all 9 PhenoAge biomarkers (final analytic sample) | 27,256 | 2,055 |

- **Final Analytic Cohort:** **27,256 adults** across 6 cycles (1999–2000 through 2009–2010).
- **Follow-Up (PERMTH_EXM):** Median **159.0 months** (max 249.0 months through Dec 31, 2019).
- **Mortality Events (`MORTSTAT == 1`):** **5,212** across full follow-up (**3,178** within $\le 120$ months).

---

## 2. Primary Survival & Concordance Results (Unweighted)

- **Cox Proportional Hazards (`lifelines.CoxPHFitter`, adjusted for `RIDAGEYR`):**
  - **HR per +1 year of PhenoAge Acceleration (`PhenoAge - Age`):** **1.0285** (95% CI: **1.0272–1.0298**, $p = 0.00e+00$)
  - **HR per +1 year of Chronological Age (`RIDAGEYR`):** 1.0913 (95% CI: 1.0889–1.0938)
- **Concordance Index (c-index) Comparison:**
  - **PhenoAge alone:** **0.8534**
  - **Chronological Age alone:** **0.8313**
  - **Delta (PhenoAge - Age):** **+0.0222**
- **Pearson Correlation (PhenoAge vs. Chronological Age):** **$r = 0.9041$** ($p = 0.00e+00$)

### 10-Year & Full Follow-Up Mortality by Age Acceleration Quartile

| Quartile | Accel Range (yrs) | Mean Accel | $N$ | $\le 120$m Deaths | Crude 10-Yr Mort (%) | KM 10-Yr Mort (%) | KM RR vs Q1 | Full Follow-Up Mort (%) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Q1 (Lowest)** | -24.8 to -10.2 | -12.85 | 6,981 | 387 | 5.54% | **5.60%** | 1.00x | 11.86% |
| **Q2** | -10.1 to -6.7 | -8.41 | 6,754 | 465 | 6.88% | **6.93%** | 1.24x | 13.78% |
| **Q3** | -6.6 to -2.3 | -4.65 | 6,748 | 712 | 10.55% | **10.62%** | 1.89x | 18.08% |
| **Q4 (Highest)** | -2.2 to +171.5 | +5.53 | 6,773 | 1,614 | 23.83% | **23.93%** | 4.27x | 32.97% |

![Real NHANES Validation Plot](./nhanes_real_validation.png)

---

## 3. Pre-Specified Sensitivity Analyses & Extreme Value Audit

| Analysis Specification (All Adjusted for `RIDAGEYR`) | $N$ | Deaths | HR | 95% CI | Joint Model c-index |
| :--- | ---: | ---: | ---: | :---: | ---: |
| **Primary (unweighted, per +1 yr raw `PhenoAge - Age`)** | 27,256 | 5,212 | **1.0285** | 1.0272–1.0298 | 0.8475 |
| **1. Per +1 SD of raw `PhenoAge - Age` (SD = 8.93 yrs)** | 27,256 | 5,212 | **1.2856** | 1.2712–1.3002 | 0.8475 |
| **2a. Winsorized 1st/99th pct ([-17.4, +26.2] yrs), per +1 yr** | 27,256 | 5,212 | **1.0593** | 1.0564–1.0622 | 0.8534 |
| **2b. Winsorized 1st/99th pct (SD = 7.54 yrs), per +1 SD** | 27,256 | 5,212 | **1.5443** | 1.5132–1.5761 | 0.8534 |
| **3. Excluding `CRP > 10 mg/dL` (excluded 36 rows), per +1 yr** | 27,220 | 5,194 | **1.0302** | 1.0289–1.0315 | 0.8480 |
| **4a. Residual-based (`PhenoAge ~ Age`, slope=1.0670, int=-8.3771), per +1 yr** | 27,256 | 5,212 | **1.0285** | 1.0272–1.0298 | 0.8475 |
| **4b. Residual-based (SD = 8.85 yrs), per +1 SD** | 27,256 | 5,212 | **1.2828** | 1.2685–1.2972 | 0.8475 |

### What the Sensitivity Analyses Show About the Primary HR (1.0285 vs. ~1.09)
- **Verified primary driver (right-tail compression):** Winsorizing `age_acceleration` at the 1st/99th percentiles (`-17.4` to `+26.2` years; clipping `252` low and `270` high rows) raises the age-adjusted HR per +1 year from **1.0285** to **1.0593** (95% CI: 1.0564–1.0622) and increases the joint Cox model c-index from **0.8475** to **0.8534**. Because creatinine (`+0.0095 * umol/L`) and glucose (`+0.1953 * mmol/L`) enter the Gompertz linear predictor linearly, severe clinical extremes produce +90 to +171.5 years of acceleration (see table below), flattening the log-linear Cox slope per +1 year on unwinsorized data.
- **Verified non-drivers in this sample:** Excluding `CRP > 10 mg/dL` removes only `36` rows and changes HR minimally (**1.0302**). Linear residualization (`PhenoAge ~ RIDAGEYR`) yields essentially identical per-year HR (**1.0285**) because chronological age is already controlled in the Cox model.
- **Untested hypotheses for the remaining gap below ~1.09:** Even after winsorization, HR per +1 year is 1.0593 rather than ~1.09. Untested hypotheses (not evaluated here) include survey weighting/strata/PSU adjustment, differences in NHANES cycle/age inclusion rules, non-fasting serum glucose (`LBXSGL`) vs. alternative glucose definitions, early-cycle creatinine calibration differences, and NCHS public-use linked mortality perturbation.

### Top 20 Most Extreme `|Age Acceleration|` Rows (All 9 Markers)
Inspection of the 20 largest absolute acceleration values (all positive extremes, +90.0 to +171.5 years): all 20 show plausible severe clinical pathology (predominantly end-stage renal-range creatinine 551.6–1,573.5 µmol/L, hyperglycemic crisis glucose up to 43.12 mmol/L, and/or acute CRP/RDW/ALP abnormalities), and 14 of 20 died during follow-up (`MORTSTAT = 1`), rather than obvious coding/sentinel errors.

| SEQN | Cycle | Age | PhenoAge | Accel | Mort | Months | Alb (g/L) | Creat (µmol/L) | Gluc (mmol/L) | CRP (mg/dL) | Lymph % | MCV (fL) | RDW % | ALP (U/L) | WBC | Assessment |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| 35764 | `2005_2006` | 59 | 230.5 | +171.5 | 0 | 169 | 39.0 | 1573.5 | 4.77 | 0.05 | 24.0 | 99.6 | 18.0 | 32 | 7.6 | plausible_clinical_extreme (survived_followup): severe_creatinine(1573.5 umol/L), high_rdw(18.0%) |
| 57643 | `2009_2010` | 45 | 179.4 | +134.4 | 0 | 118 | 42.0 | 1384.3 | 4.05 | 0.50 | 25.9 | 97.4 | 13.5 | 65 | 4.8 | plausible_clinical_extreme (survived_followup): severe_creatinine(1384.3 umol/L) |
| 22413 | `2003_2004` | 68 | 199.5 | +131.5 | 1 | 47 | 27.0 | 1211.1 | 5.38 | 1.94 | 8.5 | 98.7 | 14.1 | 83 | 9.2 | plausible_clinical_extreme (died): severe_creatinine(1211.1 umol/L), low_albumin(27 g/L), low_lymph(8.5%) |
| 9172 | `1999_2000` | 75 | 205.5 | +130.5 | 1 | 9 | 44.0 | 875.2 | 19.54 | 1.01 | 29.5 | 81.6 | 19.5 | 112 | 7.5 | plausible_clinical_extreme (died): severe_creatinine(875.2 umol/L), severe_glucose(19.5 mmol/L), high_rdw(19.5%) |
| 16283 | `2001_2002` | 72 | 198.1 | +126.1 | 1 | 11 | 37.0 | 1140.4 | 5.22 | 0.38 | 30.7 | 90.1 | 17.7 | 154 | 7.7 | plausible_clinical_extreme (died): severe_creatinine(1140.4 umol/L), high_rdw(17.7%) |
| 3886 | `1999_2000` | 66 | 191.3 | +125.3 | 1 | 85 | 42.0 | 733.7 | 10.27 | 0.05 | 9.0 | 82.4 | 27.6 | 70 | 6.6 | plausible_clinical_extreme (died): severe_creatinine(733.7 umol/L), high_rdw(27.6%), low_lymph(9.0%) |
| 33294 | `2005_2006` | 60 | 175.7 | +115.7 | 1 | 147 | 31.0 | 760.2 | 10.16 | 5.90 | 43.0 | 108.2 | 20.6 | 121 | 5.9 | plausible_clinical_extreme (died): severe_creatinine(760.2 umol/L), high_rdw(20.6%) |
| 11791 | `2001_2002` | 32 | 145.2 | +113.2 | 1 | 89 | 41.0 | 875.2 | 4.88 | 1.24 | 6.7 | 112.8 | 17.4 | 63 | 15.5 | plausible_clinical_extreme (died): severe_creatinine(875.2 umol/L), high_rdw(17.4%), high_wbc(15.5), low_lymph(6.7%) |
| 25966 | `2003_2004` | 38 | 148.8 | +110.8 | 1 | 131 | 42.0 | 1140.4 | 4.16 | 0.12 | 30.5 | 95.2 | 14.5 | 70 | 5.1 | plausible_clinical_extreme (died): severe_creatinine(1140.4 umol/L) |
| 9405 | `1999_2000` | 46 | 154.0 | +108.0 | 1 | 67 | 42.0 | 901.7 | 5.27 | 1.83 | 19.5 | 87.2 | 18.8 | 87 | 9.4 | plausible_clinical_extreme (died): severe_creatinine(901.7 umol/L), high_rdw(18.8%) |
| 58111 | `2009_2010` | 29 | 136.9 | +107.9 | 0 | 114 | 27.0 | 551.6 | 25.42 | 0.14 | 31.3 | 84.0 | 16.7 | 111 | 6.5 | plausible_clinical_extreme (survived_followup): severe_creatinine(551.6 umol/L), severe_glucose(25.4 mmol/L), low_albumin(27 g/L) |
| 61998 | `2009_2010` | 26 | 133.9 | +107.9 | 0 | 118 | 43.0 | 970.6 | 4.33 | 1.39 | 18.5 | 94.4 | 15.6 | 349 | 4.9 | plausible_clinical_extreme (survived_followup): severe_creatinine(970.6 umol/L), high_alp(349 U/L) |
| 20234 | `2001_2002` | 40 | 145.2 | +105.2 | 1 | 91 | 38.0 | 954.7 | 4.05 | 0.47 | 24.6 | 97.5 | 17.3 | 57 | 5.1 | plausible_clinical_extreme (died): severe_creatinine(954.7 umol/L), high_rdw(17.3%) |
| 15185 | `2001_2002` | 58 | 160.9 | +102.9 | 1 | 40 | 31.0 | 804.4 | 3.39 | 2.60 | 33.9 | 83.2 | 21.3 | 94 | 9.2 | plausible_clinical_extreme (died): severe_creatinine(804.4 umol/L), high_rdw(21.3%) |
| 9483 | `1999_2000` | 51 | 153.1 | +102.1 | 1 | 163 | 46.0 | 689.5 | 13.54 | 0.45 | 19.8 | 105.1 | 17.5 | 146 | 10.0 | plausible_clinical_extreme (died): severe_creatinine(689.5 umol/L), high_rdw(17.5%) |
| 51643 | `2009_2010` | 42 | 143.6 | +101.6 | 0 | 129 | 36.0 | 224.5 | 43.12 | 1.41 | 17.1 | 91.2 | 12.6 | 120 | 11.2 | plausible_clinical_extreme (survived_followup): severe_glucose(43.1 mmol/L) |
| 3743 | `1999_2000` | 76 | 176.7 | +100.7 | 0 | 231 | 37.0 | 79.6 | 24.92 | 29.60 | 13.9 | 78.1 | 27.5 | 110 | 17.3 | plausible_clinical_extreme (survived_followup): severe_glucose(24.9 mmol/L), crp>=10(29.60 mg/dL), high_rdw(27.5%), high_wbc(17.3) |
| 3894 | `1999_2000` | 61 | 161.4 | +100.4 | 1 | 116 | 43.0 | 1043.1 | 4.77 | 0.22 | 36.5 | 88.5 | 15.7 | 52 | 4.2 | plausible_clinical_extreme (died): severe_creatinine(1043.1 umol/L) |
| 1855 | `1999_2000` | 69 | 159.0 | +90.0 | 1 | 45 | 44.0 | 892.8 | 4.99 | 0.39 | 20.3 | 92.7 | 16.0 | 86 | 4.9 | plausible_clinical_extreme (died): severe_creatinine(892.8 umol/L) |
| 24589 | `2003_2004` | 60 | 150.0 | +90.0 | 1 | 71 | 37.0 | 831.0 | 10.32 | 1.05 | 28.0 | 88.6 | 13.1 | 109 | 9.4 | plausible_clinical_extreme (died): severe_creatinine(831.0 umol/L) |

---

## 4. Variable Mapping, Unit Conversions & Glucose Choice

### Glucose Variable Rationale (`BIOPRO` `LBXSGL` vs. `GLU` Fasting)
We use **standard biochemistry profile serum glucose (`LBXSGL`)** rather than the fasting plasma glucose subsample (`GLU_*` / `LBXGLU`). In NHANES 1999–2010, fasting plasma glucose is collected only in the morning fasting subsample (~half of MEC participants), whereas `BIOPRO` (`LBXSGL`) is measured across the full examined adult cohort aged 12+. Note that `LBXSGL` includes non-fasted participants.

### NHANES Variable & Unit Conversions

| NHANES Variable | PhenoAge Key | Source Unit | Target Unit (`phenoage.py`) | Conversion | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `LBXSAL` | `albumin` | g/dL | g/L | `LBXSAL * 10.0` | Consistent across all 6 cycles (1999-2010) |
| `LBXSCR (1999-2000, 2003-2010) / LBDSCR (2001-2002 L40_B)` | `creatinine` | mg/dL | umol/L | `LBXSCR * 88.4` | Standard molecular-weight factor (matches backend/app/core/normalizer.py) |
| `LBXSGL` | `glucose` | mg/dL | mmol/L | `LBXSGL / 18.0182` | Biochemistry-profile serum glucose (full MEC examined sample; includes non-fasted) |
| `LBXCRP` | `crp` | mg/dL | mg/dL | `LBXCRP * 1.0` | NHANES 1999-2010 LBXCRP is already reported in mg/dL per codebooks (no /10 scaling) |
| `LBXLYPCT` | `lymphocyte_pct` | % | % | `LBXLYPCT * 1.0` | CBC automated differential |
| `LBXMCVSI` | `mcv` | fL | fL | `LBXMCVSI * 1.0` | CBC mean cell volume |
| `LBXRDW` | `rdw` | % | % | `LBXRDW * 1.0` | CBC red cell distribution width |
| `LBXSAPSI (1999-2000, 2003-2010) / LBDSAPSI (2001-2002 L40_B)` | `alp` | U/L | U/L | `LBXSAPSI * 1.0` | Biochemistry-profile alkaline phosphatase |
| `LBXWBCSI` | `wbc` | 1000 cells/uL | 10^9/L | `LBXWBCSI * 1.0` | 1000 cells/uL is numerically 1:1 equivalent to 10^9/L |

### Cycle-Specific Breakdown & Age Top-Coding
Per official CDC `DEMO*.htm` codebooks, `RIDAGEYR` is top-coded at **85** in 1999–2006 (`>=85` collapsed to 85; `20–84` un-topcoded) and at **80** in 2007–2010 (`>=80` collapsed to 80; `20–79` un-topcoded). Top-coded ages are excluded.

| Cycle | Analytic $N$ | Mean Age | Mean PhenoAge | Median Follow-Up (mo) | $\le 120$m Deaths | Full Follow-Up Deaths |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1999_2000` | 3,982 | 48.9 | 41.9 | 234.0 | 536 | 1,195 |
| `2001_2002` | 4,523 | 47.9 | 42.5 | 212.0 | 572 | 1,118 |
| `2003_2004` | 4,246 | 49.1 | 44.3 | 189.0 | 581 | 1,009 |
| `2005_2006` | 4,294 | 47.3 | 43.6 | 166.0 | 494 | 746 |
| `2007_2008` | 4,934 | 48.5 | 43.2 | 141.0 | 527 | 665 |
| `2009_2010` | 5,277 | 47.3 | 42.4 | 119.0 | 468 | 479 |

---

## 5. Limitations

1. **US Population:** NHANES is a US civilian non-institutionalized population survey. Biomarker distributions, baseline mortality rates, and cardiometabolic risk relationships differ in Indian / South Asian populations.
2. **Unweighted Analysis:** Results above are unweighted NHANES sample estimates (survey weights, strata, and PSUs were not applied), so hazard ratios and percentages reflect the analytic sample rather than weighted US national population rates.
3. **Non-Fasting Biochemistry-Profile Glucose (`LBXSGL`):** Using standard biochemistry-profile serum glucose instead of fasting plasma glucose maximizes sample size across all MEC adults but includes participants who were not fasting at blood draw.
4. **Public-Use Linked Mortality Perturbation:** Per NCHS disclosure-avoidance rules, the public-use 2019 Linked Mortality Files apply perturbation to follow-up times and/or vital status for a small subset of records to protect participant privacy; therefore, estimates may differ slightly from NCHS restricted-use linked mortality files.

---

## 6. Official Data Sources Downloaded (`data/nhanes_raw/download_manifest.json`)

- `https://ftp.cdc.gov/pub/Health_statistics/NCHS/datalinkage/linked_mortality/R_ReadInProgramAllSurveys.R`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/DEMO.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/LAB25.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/LAB18.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/LAB11.xpt`
- `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_1999_2000_MORT_2019_PUBLIC.dat`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/DEMO_B.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/L25_B.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/L40_B.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/L11_B.xpt`
- `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2001_2002_MORT_2019_PUBLIC.dat`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/DEMO_C.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/L25_C.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/L40_C.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/L11_C.xpt`
- `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2003_2004_MORT_2019_PUBLIC.dat`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DEMO_D.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/CBC_D.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/BIOPRO_D.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/CRP_D.xpt`
- `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2005_2006_MORT_2019_PUBLIC.dat`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/DEMO_E.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/CBC_E.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/BIOPRO_E.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/CRP_E.xpt`
- `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2007_2008_MORT_2019_PUBLIC.dat`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/DEMO_F.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/CBC_F.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/BIOPRO_F.xpt`
- `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/CRP_F.xpt`
- `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2009_2010_MORT_2019_PUBLIC.dat`
