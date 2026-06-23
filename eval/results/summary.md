# Evaluation results

Reproduce with `python eval/run_all.py`. One row per run; metrics are the
agent / interaction / system / human tiers from `docs/evaluation.md`.

| run | base peak | coord peak | peak red. | slots>cap | oscill | escal. | curtailed | gini | fair breach | HITL calls | HITL appr. | comfort |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal_day | 115 | 87 | +24% | 0 | 0.000 | 0 | 0 | 0.000 | False | 0 | 0 | 6/6 |
| heatwave_peak | 256 | 176 | +31% | 0 | 0.000 | 0 | 0 | 0.000 | False | 0 | 0 | 8/8 |
| supply_shortfall | 249 | 161 | +35% | 1 | 0.120 | 1 | 11 | 0.000 | False | 1 | 1 | 6/6 |
| failure_rebound | 256 | 224 | +12% | 0 | 0.036 | 0 | 0 | 0.000 | False | 0 | 0 | 8/8 |
| heatwave +inject rebound | 256 | 224 | +12% | 0 | 0.036 | 0 | 0 | 0.000 | False | 0 | 0 | 8/8 |
| supply_shortfall --no-human | 249 | 161 | +35% | 1 | 0.120 | 1 | 0 | 0.000 | False | 1 | 0 | 6/6 |
