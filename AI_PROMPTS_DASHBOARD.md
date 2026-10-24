# AI Assistance — Grafana Dashboard

I used ChatGPT to help draft and explain complex PromQL queries and improve the dashboard presentation. I tested the dashboard locally with single-image and bulk ZIP uploads.

## Prompts used

**Dashboard generation:**
“Generate a Grafana dashboard for caption_* and node_exporter metrics. Include health, counts, throughput, histogram percentiles, Summary mean, errors, active jobs, client buckets, model memory, and CPU/RAM correlation with bulk jobs. Use correct units, explicit legends, and descriptions.”

**Presentation improvements:**
“Add short visible subtitles, explicit linear scale labels, inclusive colors, distinct dash patterns, legends and self-explanatory descriptions. Preserve existing metric queries and the 5-second refresh interval.”

## Queries covered

- Successful image throughput using rate().
- Inference and upload-duration percentiles using histogram_quantile().
- Mean image and inference duration using rate(_sum) / rate(_count).
- CPU, RAM and disk utilisation.
- Resource activity alongside active bulk jobs.
- Image failure percentage and job counts by client bucket.

The complete expressions are saved in grafana/dashboard.json. Prompt comments are also included in build_dashboard.py.

Percentiles are estimates, idle duration queries may have no value, and client buckets represent grouped sessions rather than unique users.
