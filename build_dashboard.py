"""Generate the assignment dashboard and record AI query attribution."""

import json
from pathlib import Path

# AI assistance prompt used:
# Generate a Grafana dashboard for the caption_* application metrics and
# node_exporter. Include health, counts, throughput, latency percentiles,
# Summary mean, errors, active jobs, session buckets, model memory, and
# CPU/RAM correlation with bulk jobs. Use correct units and bounded labels.
PROMPT = (
    "Generate a Grafana dashboard for caption_* and node_exporter metrics. "
    "Include health, counts, throughput, histogram percentiles, Summary mean, "
    "errors, active jobs, client buckets, model memory, and CPU/RAM correlation "
    "with bulk jobs. Use correct units, explicit legends, and descriptions."
)

DS = {"type": "prometheus", "uid": "a4-prometheus"}
COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]
panels = []


def panel(title, description, queries, unit, x, y, w=12, h=8,
          kind="timeseries", axis=None, maximum=None):
    targets = []
    overrides = []

    for index, (legend, expression) in enumerate(queries):
        ref = chr(65 + index)
        targets.append({
            "refId": ref,
            "expr": expression,
            "legendFormat": legend,
            "datasource": DS,
            "editorMode": "code",
            "range": kind == "timeseries",
            "instant": kind != "timeseries",
            "format": "table" if kind == "table" else "time_series",
        })
        if kind == "timeseries" and len(queries) > 1:
            overrides.append({
                "matcher": {"id": "byFrameRefID", "options": ref},
                "properties": [
                    {"id": "color", "value": {
                        "mode": "fixed", "fixedColor": COLORS[index % len(COLORS)]
                    }},
                    {"id": "custom.lineStyle", "value": (
                        [
                            {"fill": "solid"},
                            {"fill": "dash", "dash": [6, 4]},
                            {"fill": "dash", "dash": [2, 4]},
                            {"fill": "dash", "dash": [12, 4]},
                        ][index % 4]
                    )},
                ],
            })

    defaults = {
        "unit": unit,
        "min": 0,
        "noValue": "No data",
        "color": {"mode": "palette-classic"},
    }
    if maximum is not None:
        defaults["max"] = maximum

    if kind == "timeseries":
        defaults["custom"] = {
            "drawStyle": "line",
            "lineInterpolation": "linear",
            "lineWidth": 2,
            "fillOpacity": 0,
            "showPoints": "always",
            "pointSize": 4,
            "spanNulls": False,
            "axisLabel": axis or unit,
            "axisPlacement": "left",
            "scaleDistribution": {"type": "linear"},
        }
        options = {
            "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "none"},
        }
    elif kind == "stat":
        options = {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": "none",
            "graphMode": "none",
            "textMode": "auto",
        }
    else:
        options = {"showHeader": True}

    item = {
        "id": len(panels) + 1,
        "title": title,
        "description": description,
        "type": kind,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": defaults, "overrides": overrides},
        "options": options,
    }
    panels.append(item)
    return item


def stat(title, expression, x, description):
    return panel(title, description, [(title, expression)], "short",
                 x, 0, w=4, h=4, kind="stat")


for x, title, query, description in [
    (0, "Application metrics UP",
     'up{job="caption_app"}',
     "1 = metrics endpoint reachable; 0 = scrape failed. This does not independently test the browser UI."),
    (4, "Node exporter UP",
     'up{job="node"}',
     "1 = Ubuntu system metrics reachable; 0 = scrape failed."),
    (8, "Model ready",
     'caption_model_ready{job="caption_app"}',
     "1 = shared CPU model loaded. Zero before its first successful load."),
    (12, "Successful images",
     'sum(caption_images_total{job="caption_app",status="success"})',
     "Successful image attempts since the application process started."),
    (16, "Failed images",
     'sum(caption_images_total{job="caption_app",status="failed"})',
     "Failed image attempts, including image validation failures."),
    (20, "Active jobs",
     'sum(caption_active_jobs{job="caption_app"})',
     "Jobs currently running or waiting for the shared model."),
]:
    stat(title, query, x, description)

panel("Successful throughput",
      "Successful images per second, averaged over one minute. Idle periods approach zero.",
      [(mode.title(), 'sum(rate(caption_images_total{job="caption_app",'
        f'mode="{mode}",status="success"' + '}[1m]))')
       for mode in ("single", "bulk")],
      "ops", 0, 4, axis="Images / second")

panel("Image attempts by mode and outcome",
      "Cumulative attempts since process startup. A restart resets these counters.",
      [(f"{mode} {status}", 'sum(caption_images_total{job="caption_app",'
        f'mode="{mode}",status="{status}"' + '})')
       for mode in ("single", "bulk") for status in ("success", "failed")],
      "short", 12, 4, axis="Image attempts")

panel("Inference latency: p50 / p95 / p99",
      "Estimated percentiles over five minutes, across successful inference calls. "
      "Excludes queue wait. No observations means no percentile, not zero latency.",
      [(f"p{percent}", f'histogram_quantile({percent / 100}, '
        'sum by (le) (rate(caption_inference_seconds_bucket'
        '{job="caption_app"}[5m])))')
       for percent in (50, 95, 99)],
      "s", 0, 12, axis="Inference time (seconds)")

panel("Mean image duration: Summary",
      "Five-minute mean = rate(_sum) / rate(_count). Includes validation, "
      "queue wait, and failed image attempts. Undefined when no attempts occur.",
      [(mode.title(),
        'sum(rate(caption_image_duration_seconds_sum{job="caption_app",'
        f'mode="{mode}"' + '}[5m])) / '
        'sum(rate(caption_image_duration_seconds_count{job="caption_app",'
        f'mode="{mode}"' + '}[5m]))')
       for mode in ("single", "bulk")],
      "s", 12, 12, axis="Time per image attempt (seconds)")

cpu = '100 * (1 - avg(rate(node_cpu_seconds_total{job="node",mode="idle"}[1m])))'
ram = ('100 * (1 - node_memory_MemAvailable_bytes{job="node"} / '
       'node_memory_MemTotal_bytes{job="node"})')
bulk = 'sum(caption_active_jobs{job="caption_app",mode="bulk"})'

for title, expression, y in [
    ("CPU utilisation and bulk activity", cpu, 20),
    ("RAM utilisation and bulk activity", ram, 20),
]:
    x = 0 if title.startswith("CPU") else 12
    item = panel(
        title,
        "Ubuntu VM utilisation on the left axis; active bulk jobs on the right. "
        "Compare their timing to inspect correlation. Other VM processes also use resources.",
        [("Utilisation", expression), ("Active bulk jobs", bulk)],
        "percent", x, y, axis="VM utilisation (%)", maximum=100,
    )
    item["fieldConfig"]["overrides"].append({
        "matcher": {"id": "byName", "options": "Active bulk jobs"},
        "properties": [
            {"id": "unit", "value": "short"},
            {"id": "max", "value": None},
            {"id": "custom.axisPlacement", "value": "right"},
            {"id": "custom.axisLabel", "value": "Active bulk jobs (count)"},
        ],
    })

panel("Root disk utilisation",
      "Percentage unavailable to a normal user on Ubuntu's root filesystem, "
      "including reserved blocks; follows available-space semantics.",
      [("Root filesystem",
        '100 * (1 - node_filesystem_avail_bytes{job="node",mountpoint="/",'
        'fstype!="rootfs"} / node_filesystem_size_bytes{job="node",'
        'mountpoint="/",fstype!="rootfs"})')],
      "percent", 0, 28, axis="Root disk used (%)", maximum=100)

panel("Application RAM and model parameters",
      "Process RSS includes the model and runtime allocations. Parameter bytes "
      "count tensor parameters only; they are not total model runtime memory.",
      [("Process RAM", 'caption_app_resident_memory_bytes{job="caption_app"}'),
       ("Model parameters", 'caption_model_weight_bytes{job="caption_app"}')],
      "bytes", 12, 28, axis="Memory (bytes; displayed in binary units)")

panel("Upload job duration: p95",
      "Estimated five-minute p95 of complete jobs, including validation and model loading. "
      "Bulk jobs normally take longer because they contain multiple images.",
      [(mode.title(), 'histogram_quantile(0.95, sum by (le) (rate('
        'caption_job_duration_seconds_bucket{job="caption_app",'
        f'mode="{mode}"' + '}[5m])))')
       for mode in ("single", "bulk")],
      "s", 0, 36, axis="Job duration (seconds)")

panel("Completed upload jobs",
      "Cumulative upload jobs by mode and outcome. Rejected ZIPs are job failures "
      "before image processing and do not increment image-attempt counters.",
      [
          (
              f"{mode} / {status}",
              'sum(caption_jobs_total{job="caption_app",'
              f'mode="{mode}",status="{status}"' + '})'
          )
          for mode in ("single", "bulk")
          for status in ("success", "partial", "failed", "rejected")
      ],
      "short", 12, 36, axis="Completed jobs (count)")

panel("Image failure percentage",
      "Failed image attempts divided by all image attempts over one minute. "
      "No attempts means the percentage is undefined.",
      [("Failure percentage",
        '100 * sum(rate(caption_images_total{job="caption_app",status="failed"}[1m])) '
        '/ sum(rate(caption_images_total{job="caption_app"}[1m]))')],
      "percent", 0, 44, axis="Failed image attempts (%)", maximum=100)

panel("Mean inference latency by mode",
      "Five-minute mean of successful inference timings. Excludes queue wait "
      "and differs from the complete image-attempt duration.",
      [(mode.title(),
        'sum(rate(caption_inference_seconds_sum{job="caption_app",'
        f'mode="{mode}"' + '}[5m])) / '
        'sum(rate(caption_inference_seconds_count{job="caption_app",'
        f'mode="{mode}"' + '}[5m]))')
       for mode in ("single", "bulk")],
      "s", 12, 44, axis="Inference time (seconds)")

panel("Active jobs by mode",
      "Running and queued upload jobs. Returns to zero after jobs finish, "
      "including failures. Five-second scraping can miss very short jobs.",
      [(mode.title(), 'sum(caption_active_jobs{job="caption_app",'
        f'mode="{mode}"' + '})') for mode in ("single", "bulk")],
      "short", 0, 52, axis="Active jobs (count)")

panel("Client bucket job counts",
      "Sessions are hashed into 16 buckets. Buckets can contain multiple sessions; "
      "these are job counts, not counts of unique users.",
      [("Jobs", 'sum by (client_bucket, mode, status) '
        '(caption_jobs_total{job="caption_app"})')],
      "short", 12, 52, kind="table")

dashboard = {
    "id": None,
    "uid": "da3408-a4-captioning",
    "title": "DA3408 A4 - Image Captioning Observability",
    "description": (
        "CPU captioning health, workload, latency, and Ubuntu VM resources. "
        "AI assistance prompt: " + PROMPT +
        " Query explanations: docs/AI_PROMPTS_DASHBOARD.md."
    ),
    "tags": ["DA3408", "A4", "Prometheus"],
    "schemaVersion": 39,
    "version": 1,
    "editable": True,
    "timezone": "browser",
    "refresh": "5s",
    "time": {"from": "now-15m", "to": "now"},
    "timepicker": {"refresh_intervals": ["5s", "10s", "30s", "1m"]},
    "templating": {"list": []},
    "annotations": {"list": []},
    "panels": panels,
}

Path("grafana").mkdir(exist_ok=True)
Path("grafana/dashboard.json").write_text(
    json.dumps(dashboard, indent=2) + "\n", encoding="utf-8"
)


complex_panels = {
    "Successful throughput",
    "Inference latency: p50 / p95 / p99",
    "Mean image duration: Summary",
    "CPU utilisation and bulk activity",
    "RAM utilisation and bulk activity",
    "Root disk utilisation",
    "Upload job duration: p95",
    "Image failure percentage",
    "Mean inference latency by mode",
    "Client bucket job counts",
}

attribution = [
    "# AI Assistance — Complex PromQL Queries",
    "",
    "This document records selected complex PromQL queries for which "
    "ChatGPT helped with drafting and explanation. The dashboard was tested "
    "locally using single-image and bulk uploads.",
    "",
    "Original dashboard-generation prompt:",
    PROMPT,
    "",
    "Queries must be understood and manually explained during evaluation.",
]

for item in panels:
    if item["title"] not in complex_panels:
        continue
    attribution.extend(["", "## " + item["title"], item["description"]])
    for target in item["targets"]:
        attribution.extend(["", "```promql", target["expr"], "```"])

Path("docs").mkdir(exist_ok=True)
Path("docs/AI_PROMPTS_DASHBOARD.md").write_text(
    "\n".join(attribution) + "\n", encoding="utf-8"
)

print("Created grafana/dashboard.json")
print("Created docs/AI_PROMPTS_DASHBOARD.md")
print("Panels:", len(panels))
print("Refresh:", dashboard["refresh"])
