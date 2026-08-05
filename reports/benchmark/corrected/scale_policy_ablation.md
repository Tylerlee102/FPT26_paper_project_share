# MXFP4 State Scale-Policy Ablation

Status: `PASS` for synthetic floating Q/DQ diagnostics only. 
This uses floating Q/DQ recurrence arithmetic; 
event counts cover state requantization only, not encoded accumulation or HLS.

Configuration: value heads=32, Q/K heads=16, K=128, V=128, activation B32, state B32, seed=64370, family=nominal.

| Token | Policy | Output cosine | State rel L2 | State max abs | Cumulative state saturations | Cumulative scale changes |
|---:|---|---:|---:|---:|---:|---:|
| 64 | mxfp4_scale_every_token | 0.864884 | 0.697283 | 0.393287 | 1 | 192170 |
| 64 | mxfp4_scale_fixed | 0.881201 | 0.581477 | 0.293212 | 325581 | 0 |
| 64 | mxfp4_scale_periodic_16 | 0.878286 | 0.625192 | 0.343964 | 196055 | 15472 |
| 64 | mxfp4_scale_periodic_4 | 0.874760 | 0.649982 | 0.393287 | 121561 | 56475 |
| 64 | mxfp4_scale_periodic_8 | 0.876650 | 0.638411 | 0.372342 | 153588 | 29477 |
| 64 | mxfp4_scale_threshold_0p75_5p5 | 0.849676 | 0.751898 | 0.393287 | 0 | 15553 |
| 256 | mxfp4_scale_every_token | 0.767398 | 1.082337 | 0.591019 | 1 | 838563 |
| 256 | mxfp4_scale_fixed | 0.852817 | 0.711178 | 0.296946 | 1883530 | 0 |
| 256 | mxfp4_scale_periodic_16 | 0.802002 | 0.940795 | 0.546849 | 752694 | 71546 |
| 256 | mxfp4_scale_periodic_4 | 0.795470 | 0.977894 | 0.541694 | 509772 | 255205 |
| 256 | mxfp4_scale_periodic_8 | 0.797930 | 0.952135 | 0.541694 | 636168 | 136227 |
| 256 | mxfp4_scale_threshold_0p75_5p5 | 0.731196 | 1.207095 | 0.591019 | 0 | 21017 |
| 1024 | mxfp4_scale_every_token | 0.726945 | 1.131784 | 1.053724 | 7 | 3328329 |
| 1024 | mxfp4_scale_fixed | 0.833785 | 0.697721 | 0.459402 | 8183112 | 0 |
| 1024 | mxfp4_scale_periodic_16 | 0.763763 | 0.972644 | 0.584402 | 2839171 | 293766 |
| 1024 | mxfp4_scale_periodic_4 | 0.756227 | 1.012296 | 0.560351 | 2014133 | 1039179 |
| 1024 | mxfp4_scale_periodic_8 | 0.754494 | 0.983950 | 0.586130 | 2494633 | 556465 |
| 1024 | mxfp4_scale_threshold_0p75_5p5 | 0.600805 | 1.529403 | 0.708834 | 0 | 28524 |
| 4096 | mxfp4_scale_every_token | 0.734925 | 1.138261 | 0.787032 | 33 | 13289083 |
| 4096 | mxfp4_scale_fixed | 0.844881 | 0.696878 | 0.472892 | 33799255 | 0 |
| 4096 | mxfp4_scale_periodic_16 | 0.780520 | 0.956279 | 0.720791 | 11324960 | 1176091 |
| 4096 | mxfp4_scale_periodic_4 | 0.765503 | 1.009543 | 0.563381 | 8038797 | 4172932 |
| 4096 | mxfp4_scale_periodic_8 | 0.777531 | 0.979115 | 0.556725 | 10022103 | 2224651 |
| 4096 | mxfp4_scale_threshold_0p75_5p5 | 0.562819 | 1.761081 | 0.757654 | 0 | 34842 |
| 8192 | mxfp4_scale_every_token | 0.729275 | 1.103841 | 0.789244 | 73 | 26504191 |
| 8192 | mxfp4_scale_fixed | 0.847089 | 0.676620 | 0.395369 | 67980414 | 0 |
| 8192 | mxfp4_scale_periodic_16 | 0.785347 | 0.939046 | 0.554241 | 22646994 | 2354947 |
| 8192 | mxfp4_scale_periodic_4 | 0.773418 | 0.985345 | 0.801489 | 16091670 | 8345806 |
| 8192 | mxfp4_scale_periodic_8 | 0.785090 | 0.951738 | 0.570926 | 20026426 | 4448732 |
| 8192 | mxfp4_scale_threshold_0p75_5p5 | 0.558410 | 1.724816 | 0.813811 | 0 | 35057 |

The preregistered development diagnostic thresholds are output cosine at least 0.99 at every required checkpoint and state relative L2 at most 0.10 at token 8192. These are engineering thresholds, not model-quality claims.

Refresh semantics: fixed scales use token-0 calibration; periodic scales refresh after tokens divisible by N; threshold refresh occurs per block when nonzero normalized maximum magnitude leaves [0.75, 5.5].
