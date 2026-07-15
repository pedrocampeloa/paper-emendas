# n3 follow-up progress

Started: 2026-06-17T23:51:16.057251

Config: n_folds=3, n_reps=3 (identico ao main paper)

## Resultados em ordem de conclusao


### T3 - gov (OLS mediation)

- **T3-gov** pooled: total=+0.0009, indirect=+0.0002, prop_mediated=+26.9%, n=869,902
- **T3-gov** leg55: total=+0.0111, indirect=+0.0000, prop_mediated=+0.0%, n=226,308
- **T3-gov** leg56: total=-0.0030, indirect=+0.0001, prop_mediated=-3.4%, n=643,594

### T3 - centrao (OLS mediation)

- **T3-centrao** pooled: total=+0.0004, indirect=+0.0004, prop_mediated=+102.5%, n=869,902
- **T3-centrao** leg55: total=+0.0066, indirect=+0.0000, prop_mediated=+0.0%, n=226,308
- **T3-centrao** leg56: total=-0.0023, indirect=+0.0002, prop_mediated=-9.8%, n=643,594

### T5 - centrao sub-samples

- **00:11:44** [T5] T5 leg55_full: theta = +0.0615 pp/R$M CI [-1.473, +1.596] p = 0.9374, n = 226,308
- **07:19:26** [T5] T5 leg56_full: theta = -0.6726 pp/R$M** CI [-1.301, -0.044] p = 0.0360, n = 643,594
- **10:58:28** [T5] T5 leg56_pre_lira: theta = +0.8726 pp/R$M*** CI [+0.306, +1.439] p = 0.0025, n = 236,945
- **12:14:08** [T5] T5 leg56_post_lira: theta = +0.4021 pp/R$M** CI [+0.070, +0.734] p = 0.0176, n = 406,649
- **12:47:18** [T5] T5 leg56_post_lira_excl_centrao: theta = +0.2401 pp/R$M CI [-0.279, +0.759] p = 0.3643, n = 228,657

### T2 - gov

- **12:49:21** [T2-gov] T2 gov rp9_exposed: theta = -0.3091 pp/R$M CI [-1.331, +0.712] p = 0.5531, n = 20,755
- **13:54:20** [T2-gov] T2 gov rp9_not_exposed: theta = -0.9857 pp/R$M*** CI [-1.526, -0.445] p = 0.0004, n = 622,839

### T2 - centrao

- **13:56:16** [T2-centrao] T2 centrao rp9_exposed: theta = -0.2641 pp/R$M CI [-1.277, +0.748] p = 0.6092, n = 20,755
- **14:57:52** [T2-centrao] T2 centrao rp9_not_exposed: theta = -0.6795 pp/R$M** CI [-1.324, -0.035] p = 0.0389, n = 622,839

### T4 - gov

- **15:01:53** [T4-gov] T4 gov MDS-Euclidean leg=55 tercil=low: theta = -4.3667 pp/R$M CI [-12.797, +4.064] p = 0.3100, n = 76,036
- **15:04:33** [T4-gov] T4 gov MDS-Euclidean leg=55 tercil=mid: theta = +0.1087 pp/R$M CI [-1.194, +1.411] p = 0.8700, n = 77,208
- **15:09:31** [T4-gov] T4 gov MDS-Euclidean leg=55 tercil=high: theta = +0.3022 pp/R$M CI [-1.020, +1.625] p = 0.6542, n = 73,064
- **15:39:49** [T4-gov] T4 gov MDS-Euclidean leg=56 tercil=low: theta = -1.3793 pp/R$M*** CI [-2.344, -0.415] p = 0.0051, n = 307,104
- **15:45:56** [T4-gov] T4 gov MDS-Euclidean leg=56 tercil=mid: theta = +18.8019 pp/R$M CI [-9.261, +46.864] p = 0.1891, n = 129,364
- **15:57:52** [T4-gov] T4 gov MDS-Euclidean leg=56 tercil=high: theta = -0.3246 pp/R$M* CI [-0.659, +0.010] p = 0.0575, n = 207,126
- **16:01:34** [T4-gov] T4 gov MDS-Weak leg=55 tercil=low: theta = -1.1284 pp/R$M CI [-4.819, +2.562] p = 0.5490, n = 83,343
- **16:04:42** [T4-gov] T4 gov MDS-Weak leg=55 tercil=mid: theta = +6.9062 pp/R$M*** CI [+4.017, +9.796] p = 0.0000, n = 90,239
- **16:06:02** [T4-gov] T4 gov MDS-Weak leg=55 tercil=high: theta = +5.1305 pp/R$M** CI [+0.621, +9.640] p = 0.0258, n = 52,726
- **16:28:34** [T4-gov] T4 gov MDS-Weak leg=56 tercil=low: theta = +14.8475 pp/R$M CI [-7.152, +36.847] p = 0.1859, n = 239,890
- **16:40:46** [T4-gov] T4 gov MDS-Weak leg=56 tercil=mid: theta = -1.0993 pp/R$M*** CI [-1.581, -0.618] p = 0.0000, n = 199,686
- **16:55:27** [T4-gov] T4 gov MDS-Weak leg=56 tercil=high: theta = +1.9628 pp/R$M*** CI [+0.499, +3.427] p = 0.0086, n = 204,018
- **17:00:47** [T4-gov] T4 gov MDS-Strong leg=55 tercil=low: theta = -0.8070 pp/R$M CI [-3.526, +1.912] p = 0.5608, n = 78,178
- **17:04:12** [T4-gov] T4 gov MDS-Strong leg=55 tercil=mid: theta = +3.1122 pp/R$M*** CI [+1.527, +4.697] p = 0.0001, n = 77,747
- **17:07:42** [T4-gov] T4 gov MDS-Strong leg=55 tercil=high: theta = -1.8601 pp/R$M CI [-4.115, +0.395] p = 0.1060, n = 70,383
- **17:24:39** [T4-gov] T4 gov MDS-Strong leg=56 tercil=low: theta = +8.9924 pp/R$M CI [-8.423, +26.408] p = 0.3115, n = 218,841
- **17:43:24** [T4-gov] T4 gov MDS-Strong leg=56 tercil=mid: theta = -1.8722 pp/R$M*** CI [-2.556, -1.188] p = 0.0000, n = 240,832
- **17:56:11** [T4-gov] T4 gov MDS-Strong leg=56 tercil=high: theta = -0.0799 pp/R$M CI [-0.531, +0.371] p = 0.7284, n = 183,921

### T4 - centrao

- **18:00:33** [T4-centrao] T4 centrao MDS-Euclidean leg=55 tercil=low: theta = -3.9226 pp/R$M CI [-11.190, +3.345] p = 0.2901, n = 76,036
- **18:03:36** [T4-centrao] T4 centrao MDS-Euclidean leg=55 tercil=mid: theta = -0.1262 pp/R$M CI [-1.172, +0.920] p = 0.8131, n = 77,208
- **18:08:35** [T4-centrao] T4 centrao MDS-Euclidean leg=55 tercil=high: theta = +0.0491 pp/R$M CI [-1.148, +1.246] p = 0.9359, n = 73,064
- **18:36:57** [T4-centrao] T4 centrao MDS-Euclidean leg=56 tercil=low: theta = -1.0130 pp/R$M* CI [-2.030, +0.004] p = 0.0510, n = 307,104
- **18:42:18** [T4-centrao] T4 centrao MDS-Euclidean leg=56 tercil=mid: theta = +31.2706 pp/R$M CI [-14.324, +76.865] p = 0.1789, n = 129,364
- **18:53:55** [T4-centrao] T4 centrao MDS-Euclidean leg=56 tercil=high: theta = +0.1419 pp/R$M CI [-0.196, +0.479] p = 0.4099, n = 207,126
- **18:57:58** [T4-centrao] T4 centrao MDS-Weak leg=55 tercil=low: theta = +1.5429 pp/R$M CI [-1.353, +4.439] p = 0.2964, n = 83,343
- **19:01:20** [T4-centrao] T4 centrao MDS-Weak leg=55 tercil=mid: theta = +4.1817 pp/R$M*** CI [+1.793, +6.570] p = 0.0006, n = 90,239
- **19:02:42** [T4-centrao] T4 centrao MDS-Weak leg=55 tercil=high: theta = +3.3634 pp/R$M*** CI [+0.832, +5.895] p = 0.0092, n = 52,726
