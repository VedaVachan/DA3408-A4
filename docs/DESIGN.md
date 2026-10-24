# Design and Metric Calculations

## Application design

The application uses Salesforce/blip-image-captioning-base on CPU.
It was selected because it provides a direct image-captioning workflow
and was practical on the tested Ubuntu VM.

Streamlit caches one CPUCaptioner instance across sessions.
A lock serialises access to its processor and model.
Bulk uploads process images sequentially to control memory consumption.
Generation uses greedy decoding, with at most 30 new tokens.

The model must be downloaded before starting the offline application.
Model weights and virtual environments are excluded from Git.

## Upload handling

Images are decoded from bytes, checked against size and resolution limits,
orientation-corrected, and converted to RGB.

ZIP entries are read in memory rather than extracted to disk.
Unsafe paths, symbolic links, encrypted entries, excessive entry counts,
and excessive image counts or sizes cause rejection.
Unsupported filename extensions are skipped.
A corrupted supported image produces a failed result while other images continue.

This is bounded local processing, not a general-purpose sandbox for
arbitrary hostile files or a public multi-tenant service.

## Instrumentation

| Metric | Type | Meaning |
|---|---|---|
| caption_images_total | Counter | Completed image attempts by mode and outcome |
| caption_jobs_total | Counter | Completed jobs by mode, outcome, and client bucket |
| caption_active_jobs | Gauge | Running and queued jobs by mode |
| caption_inference_seconds | Histogram | Successful processor/generation timing, excluding queue wait |
| caption_image_duration_seconds | Summary | Complete image-attempt timing, including errors and queue wait |
| caption_job_duration_seconds | Histogram | Complete upload-job timing |
| caption_model_ready | Gauge | Whether the shared model has loaded successfully |
| caption_model_weight_bytes | Gauge | Storage occupied by model parameter tensors |
| caption_app_resident_memory_bytes | Gauge | Application process resident memory |

Inference observations also include decoding and output validation.
Image-attempt duration includes any UI work performed inside that attempt.
Job duration includes validation, model preparation, and processing.

Counters and observations are updated during processing, not during scrapes.
The memory gauge samples current process RSS when collected.
Active-job cleanup runs even when processing fails.

Counters reset when the application process restarts.
Summary exposes _sum and _count. Counter exposes _total.
Python Summary does not provide client-side quantile estimates here;
dashboard percentiles come from the Histogram.

## Labels

mode has two values: single and bulk.
Image status has two values: success and failed.
Job status can be success, partial, failed, or rejected.

Each Streamlit session receives a random ID.
A SHA-256-derived bucket maps that ID into one of 16 values.
Only the bucket is exported.

Buckets can contain several sessions and must not be described as unique users.
Raw session IDs, filenames, captions, and IP addresses are not metric labels.
This bounds series growth and avoids exporting identifying client metadata.

## Monitoring infrastructure

Linux host networking allows containers to scrape Ubuntu loopback services.
node_exporter uses the host process namespace and read-only host filesystem paths.
It measures Ubuntu VM resources, including other workloads in that VM.

Prometheus scrapes every five seconds.
Grafana refreshes every five seconds.
A very short job can begin and finish between scrapes, so its active gauge
may not be observed even though its cumulative counter is recorded.

The application UP panel measures metrics-endpoint reachability.
It does not independently prove that the Streamlit UI is responsive.

## Worked calculations

### Throughput

Suppose a successful-image counter increases by 20 over 60 seconds:

20 / 60 = 0.333 images per second.

The dashboard uses rate(counter[1m]).
Prometheus accounts for counter resets and extrapolates near range boundaries,
so a real query need not equal a simple endpoint subtraction exactly.

### Mean inference latency

The verified bulk metrics at one checkpoint were:

- Sum: 46.922566 seconds.
- Count: 21 successful inference calls.

Mean = 46.922566 / 21 = approximately 2.234 seconds.

This is a mean across those observations, not the duration of a complete ZIP job.
The dashboard uses rate(_sum[5m]) / rate(_count[5m]) for a recent mean.
With no recent observations, the mean is undefined.

### Summary mean

Suppose three image attempts take 2, 2.5, and 3.5 seconds:

- _sum = 8 seconds.
- _count = 3.
- Mean = 8 / 3 = approximately 2.667 seconds.

Summary mean can include failed attempts; inference mean includes successful
inference calls only.

### Histogram buckets and p95

Suppose 20 observations produce these cumulative counts:

| Upper bound | Cumulative count |
|---|---:|
| 2 seconds | 2 |
| 2.5 seconds | 18 |
| 3 seconds | 20 |

The p95 rank is 0.95 × 20 = 19.
It falls between 2.5 and 3 seconds.

Linear interpolation estimates:

2.5 + ((19 - 18) / (20 - 18)) × (3 - 2.5) = 2.75 seconds.

This is an estimate from buckets, not an exact sample percentile.
The dashboard applies histogram_quantile to bucket rates and retains
the le label when aggregating classic histogram buckets.

### Failure percentage

Three failures among ten attempts:

100 × 3 / 10 = 30%.

The alert requires more than 20% failures, at least five estimated attempts
in the five-minute window, and 30 seconds continuously satisfying the condition.
Exactly 20% does not exceed the threshold.
A partial ZIP can contribute both successful and failed image attempts.

### CPU utilisation

For six cores observed over 60 seconds, total CPU capacity is:

6 × 60 = 360 core-seconds.

If aggregate idle time increases by 240 core-seconds:

100 × (1 - 240 / 360) = 33.33% utilisation.

The query averages idle-time rates across cores and subtracts from one.

### RAM utilisation

With 8 GiB total and 3 GiB available:

100 × (1 - 3 / 8) = 62.5%.

Available memory is used instead of free memory because Linux caches
can be reclaimed.

### Root disk utilisation

With 100 GiB capacity and 30 GiB available to ordinary users:

100 × (1 - 30 / 100) = 70%.

Available-space semantics include reserved blocks, so this may differ
from a calculation using raw free blocks.

## Alert delivery

Prometheus evaluates five rules and sends firing alerts to Alertmanager.
Alertmanager groups notifications and delivers them to the local receiver.
The receiver saves JSON before acknowledging successful delivery.

A real application outage produced a firing notification at
2026-10-20 09:01:04 UTC.
Recovery produced a resolved notification at
2026-10-20 09:08:46 UTC.

The other threshold alerts have configuration validation;
they have not all been triggered through real resource-pressure tests.

## Dashboard presentation

The dashboard progresses from health and counts to workload, latency,
resource correlation, job behaviour, and client buckets.

Panels have descriptive titles, units, legends, and explanatory descriptions.
Time-series axes use linear scales.
Blue/orange and additional distinguishable colours are combined with
solid/dashed lines and visible points where configured.
Descriptions are available through panel information icons.
The client bucket table uses full dashboard width.

## Validation boundaries

- 24 automated tests passed on the development VM.
- Inference unit tests use mocks.
- Real CPU inference was verified separately with a dog photograph.
- A 20-image load test used repeated copies of that photograph.
- A mixed valid/corrupted ZIP verified continued processing and failure metrics.
- Prometheus target health and Grafana data-source connectivity were verified.
- Dashboard import and layout were inspected.
- Downtime firing and recovery notification delivery were verified.

These checks establish the demonstrated local behaviour.
They do not establish production scalability or universal caption accuracy.
