# Controlled RS2/R3 Long-Sequence Comparison

Status: `PASS`

All paths use the same `high_retention` synthetic trace, random initial state, seed `0x0000FB72`, GDN layer shape, B32 block size, and FP32 recurrence reference.

| Token | Variant | Output cosine | State relative L2 | State max abs |
|---:|---|---:|---:|---:|
| 64 | bf16_qdq_fp32_accum_state_bf16 | 0.999939 | 0.011382 | 0.016382 |
| 64 | flat_int4_qdq | 0.596227 | 1.595326 | 1.072564 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 |
| 64 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.966908 | 0.222288 | 0.240712 |
| 64 | mxfp4_qdq_act_b32_state_b32 | 0.858245 | 0.514852 | 0.476668 |
| 64 | mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5 | 0.998466 | 0.053847 | 0.049046 |
| 256 | bf16_qdq_fp32_accum_state_bf16 | 0.999842 | 0.018909 | 0.032969 |
| 256 | flat_int4_qdq | 0.229780 | 3.253407 | 3.071876 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 |
| 256 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.954358 | 0.285436 | 0.457339 |
| 256 | mxfp4_qdq_act_b32_state_b32 | 0.723672 | 0.741886 | 1.060105 |
| 256 | mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5 | 0.996776 | 0.077222 | 0.105534 |
| 1024 | bf16_qdq_fp32_accum_state_bf16 | 0.999815 | 0.020935 | 0.029921 |
| 1024 | flat_int4_qdq | 0.073600 | 5.088272 | 5.505537 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 |
| 1024 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.950803 | 0.300345 | 0.523942 |
| 1024 | mxfp4_qdq_act_b32_state_b32 | 0.662794 | 0.880347 | 1.270876 |
| 1024 | mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5 | 0.996624 | 0.081606 | 0.097831 |
| 4096 | bf16_qdq_fp32_accum_state_bf16 | 0.999810 | 0.021515 | 0.035727 |
| 4096 | flat_int4_qdq | 0.031689 | 7.518989 | 8.164949 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 |
| 4096 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.953532 | 0.300994 | 0.502278 |
| 4096 | mxfp4_qdq_act_b32_state_b32 | 0.667069 | 0.898157 | 1.345301 |
| 4096 | mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5 | 0.996507 | 0.081595 | 0.097780 |
| 8192 | bf16_qdq_fp32_accum_state_bf16 | 0.999812 | 0.020998 | 0.041461 |
| 8192 | flat_int4_qdq | 0.121427 | 2.736632 | 2.891224 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 |
| 8192 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.950258 | 0.301757 | 0.443426 |
| 8192 | mxfp4_qdq_act_b32_state_b32 | 0.672818 | 0.903408 | 1.287642 |
| 8192 | mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5 | 0.996725 | 0.081526 | 0.089080 |

The exact RS2/R3 row carries encoded arithmetic event counters. Floating Q/DQ rows remain diagnostic and do not claim encoded hardware parity.
