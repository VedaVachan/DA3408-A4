# AI Assistance — Complex PromQL Queries

This document records selected complex PromQL queries for which ChatGPT helped with drafting and explanation. The dashboard was tested locally using single-image and bulk uploads.

Presentation update prompt:
Add short visible subtitles, explicit linear scale labels, inclusive colors, distinct dash patterns, legends and self-explanatory descriptions. Preserve existing metric queries and the 5-second refresh interval.

Original dashboard-generation prompt:
Generate a Grafana dashboard for caption_* and node_exporter metrics. Include health, counts, throughput, histogram percentiles, Summary mean, errors, active jobs, client buckets, model memory, and CPU/RAM correlation with bulk jobs. Use correct units, explicit legends, and descriptions.

Queries must be understood and manually explained during evaluation.

## Successful throughput
Successful images per second, averaged over one minute. Idle periods approach zero.

```promql
sum(rate(caption_images_total{job="caption_app",mode="single",status="success"}[1m]))
```

```promql
sum(rate(caption_images_total{job="caption_app",mode="bulk",status="success"}[1m]))
```

## Inference latency: p50 / p95 / p99
Estimated percentiles over five minutes, across successful inference calls. Excludes queue wait. No observations means no percentile, not zero latency.

```promql
histogram_quantile(0.5, sum by (le) (rate(caption_inference_seconds_bucket{job="caption_app"}[5m])))
```

```promql
histogram_quantile(0.95, sum by (le) (rate(caption_inference_seconds_bucket{job="caption_app"}[5m])))
```

```promql
histogram_quantile(0.99, sum by (le) (rate(caption_inference_seconds_bucket{job="caption_app"}[5m])))
```

## Mean image duration: Summary
Five-minute mean = rate(_sum) / rate(_count). Includes validation, queue wait, and failed image attempts. Undefined when no attempts occur.

```promql
sum(rate(caption_image_duration_seconds_sum{job="caption_app",mode="single"}[5m])) / sum(rate(caption_image_duration_seconds_count{job="caption_app",mode="single"}[5m]))
```

```promql
sum(rate(caption_image_duration_seconds_sum{job="caption_app",mode="bulk"}[5m])) / sum(rate(caption_image_duration_seconds_count{job="caption_app",mode="bulk"}[5m]))
```

## CPU utilisation and bulk activity
Ubuntu VM utilisation on the left axis; active bulk jobs on the right. Compare their timing to inspect correlation. Other VM processes also use resources.

```promql
100 * (1 - avg(rate(node_cpu_seconds_total{job="node",mode="idle"}[1m])))
```

```promql
sum(caption_active_jobs{job="caption_app",mode="bulk"})
```

## RAM utilisation and bulk activity
Ubuntu VM utilisation on the left axis; active bulk jobs on the right. Compare their timing to inspect correlation. Other VM processes also use resources.

```promql
100 * (1 - node_memory_MemAvailable_bytes{job="node"} / node_memory_MemTotal_bytes{job="node"})
```

```promql
sum(caption_active_jobs{job="caption_app",mode="bulk"})
```

## Root disk utilisation
Percentage unavailable to a normal user on Ubuntu's root filesystem, including reserved blocks; follows available-space semantics.

```promql
100 * (1 - node_filesystem_avail_bytes{job="node",mountpoint="/",fstype!="rootfs"} / node_filesystem_size_bytes{job="node",mountpoint="/",fstype!="rootfs"})
```

## Upload job duration: p95
Estimated five-minute p95 of complete jobs, including validation and model loading. Bulk jobs normally take longer because they contain multiple images.

```promql
histogram_quantile(0.95, sum by (le) (rate(caption_job_duration_seconds_bucket{job="caption_app",mode="single"}[5m])))
```

```promql
histogram_quantile(0.95, sum by (le) (rate(caption_job_duration_seconds_bucket{job="caption_app",mode="bulk"}[5m])))
```

## Image failure percentage
Failed image attempts divided by all image attempts over one minute. No attempts means the percentage is undefined.

```promql
100 * sum(rate(caption_images_total{job="caption_app",status="failed"}[1m])) / sum(rate(caption_images_total{job="caption_app"}[1m]))
```

## Mean inference latency by mode
Five-minute mean of successful inference timings. Excludes queue wait and differs from the complete image-attempt duration.

```promql
sum(rate(caption_inference_seconds_sum{job="caption_app",mode="single"}[5m])) / sum(rate(caption_inference_seconds_count{job="caption_app",mode="single"}[5m]))
```

```promql
sum(rate(caption_inference_seconds_sum{job="caption_app",mode="bulk"}[5m])) / sum(rate(caption_inference_seconds_count{job="caption_app",mode="bulk"}[5m]))
```

## Client bucket job counts
Sessions are hashed into 16 buckets. Buckets can contain multiple sessions; these are job counts, not counts of unique users.

```promql
sum by (client_bucket, mode, status) (caption_jobs_total{job="caption_app"})
```
