# n3 — outcome y_pres_camara_orient

Started: 2026-06-19T12:18:56.754378

Outcome: voto == orientação do partido do presidente da Câmara em t

Sub-períodos:
- 2015-02 a 2016-07: Cunha (PMDB)
- 2016-07 a 2021-02: Maia (DEM)
- 2021-02 em diante: Lira (PP)

Config: n_folds=3, n_reps=3


### T3 — OLS mediation Pix

- pooled: total=-0.0023, indirect=+0.0002, prop_med=-9.1%, n=735,336
- leg55: total=-0.0008, indirect=+0.0000, prop_med=-0.0%, n=119,505
- leg56: total=-0.0027, indirect=+0.0003, prop_med=-9.5%, n=615,831

### T5 — sub-amostras por presidente

- **12:25:28** [T5] T5 leg55_maia: theta=-2.7623 pp/R$M*** p=0.0083 n=119,389
- **12:45:01** [T5] T5 leg56_maia: theta=+0.0360 pp/R$M p=0.8464 n=219,765
- **13:28:59** [T5] T5 leg56_lira: theta=+0.3295 pp/R$M** p=0.0430 n=396,066
- **14:13:27** [T5] T5 leg56_lira_excl_pp: theta=+0.3218 pp/R$M* p=0.0763 n=363,271
- **14:51:32** [T5] T5 leg56_lira_excl_centrao: theta=-0.0628 pp/R$M p=0.8134 n=181,278

### T2 — RP-9 exposure (Leg 56)

- **14:53:17** [T2] T2 rp9_exposed: theta=-0.2642 pp/R$M p=0.6037 n=20,277
- **15:55:55** [T2] T2 rp9_not_exposed: theta=-1.2727 pp/R$M*** p=0.0000 n=595,554

### T4 — tercis MDS por leg

- **15:57:31** [T4] T4 MDS-Euclidean leg=55 tercil=low: theta=+11.4251 pp/R$M*** p=0.0018 n=42,304
- **15:58:58** [T4] T4 MDS-Euclidean leg=55 tercil=mid: theta=+14.8073 pp/R$M* p=0.0799 n=37,426
- **16:00:39** [T4] T4 MDS-Euclidean leg=55 tercil=high: theta=-1.3237 pp/R$M** p=0.0280 n=39,775
- **16:30:43** [T4] T4 MDS-Euclidean leg=56 tercil=low: theta=-1.8550 pp/R$M*** p=0.0000 n=289,827
- **16:36:24** [T4] T4 MDS-Euclidean leg=56 tercil=mid: theta=+20.4152 pp/R$M p=0.1289 n=124,428
- **16:45:12** [T4] T4 MDS-Euclidean leg=56 tercil=high: theta=+0.2208 pp/R$M p=0.2095 n=201,576
- **16:46:53** [T4] T4 MDS-Weak leg=55 tercil=low: theta=+11.5228 pp/R$M*** p=0.0023 n=42,331
- **16:48:24** [T4] T4 MDS-Weak leg=55 tercil=mid: theta=-1.8674 pp/R$M*** p=0.0067 n=38,977
- **16:49:42** [T4] T4 MDS-Weak leg=55 tercil=high: theta=-8.6813 pp/R$M* p=0.0615 n=38,197
- **17:10:47** [T4] T4 MDS-Weak leg=56 tercil=low: theta=+14.3886 pp/R$M p=0.3215 n=224,684
- **17:20:54** [T4] T4 MDS-Weak leg=56 tercil=mid: theta=-1.2230 pp/R$M*** p=0.0000 n=192,171
- **17:37:07** [T4] T4 MDS-Weak leg=56 tercil=high: theta=+3.7206 pp/R$M*** p=0.0001 n=198,976
- **17:38:39** [T4] T4 MDS-Strong leg=55 tercil=low: theta=-4.9343 pp/R$M*** p=0.0056 n=52,372
- **17:40:15** [T4] T4 MDS-Strong leg=55 tercil=mid: theta=-4.0581 pp/R$M*** p=0.0031 n=47,402
- **17:41:10** [T4] T4 MDS-Strong leg=55 tercil=high: theta=+0.0821 pp/R$M p=0.8373 n=19,731
- **17:56:41** [T4] T4 MDS-Strong leg=56 tercil=low: theta=+2.8224 pp/R$M p=0.1226 n=208,238
- **18:14:46** [T4] T4 MDS-Strong leg=56 tercil=mid: theta=-3.2662 pp/R$M*** p=0.0000 n=227,700
- **18:25:27** [T4] T4 MDS-Strong leg=56 tercil=high: theta=+0.4053 pp/R$M* p=0.0967 n=179,893

### T1 — IV-DML with proxies

- **18:31:20** [T1] T1 leg=55 base_pure: theta=-2.9168 pp/R$M*** p=0.0071 n=119,505
- **18:36:39** [T1] T1 leg=55 base+proxies: theta=-3.0383 pp/R$M*** p=0.0053 n=119,505
- **19:31:04** [T1] T1 leg=56 base_pure: theta=-1.3047 pp/R$M*** p=0.0001 n=615,831
- **20:25:49** [T1] T1 leg=56 base+proxies: theta=-1.3190 pp/R$M*** p=0.0001 n=615,831

## End: 2026-06-19T20:25:49.482350 (8.11h)
