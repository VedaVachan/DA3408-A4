# AIOps Assignment 4 — Application Monitoring

This repository contains my implementation of CPU-only image captioning
with Prometheus instrumentation, node_exporter, Grafana and Alertmanager.

The Streamlit application supports single-image and bulk ZIP uploads using
Salesforce/blip-image-captioning-base.

## Project Structure

| File or folder | Purpose |
|---|---|
| app.py | Streamlit interface and upload processing |
| captioner.py | CPU-only BLIP caption generation |
| uploads.py | Image and ZIP validation |
| metrics.py | Prometheus metric definitions |
| download_model.py | Download and cache the model |
| alert_receiver.py | Receive and log alert notifications |
| requirements.txt | Python dependencies |
| requirements-cpu.txt | CPU-only PyTorch dependencies |
| compose.yml | Prometheus and node_exporter |
| compose.grafana.yml | Grafana service |
| compose.alerting.yml | Alertmanager and alert-rule mount |
| prometheus.yml | Scrape targets and alerting configuration |
| alerts.yml | Five Prometheus alert rules |
| alertmanager.yml | Webhook notification routing |
| grafana/ | Dashboard JSON and data-source provisioning |
| build_dashboard.py | Generate the dashboard |
| polish_dashboard.py | Improve dashboard layout |
| tests/ | Automated tests |
| docs/ | Design, calculations, AI attribution and submission guide |
| evidence/ | Screenshots and demonstration results |
| demo_inputs/ | Local single-image and bulk ZIP inputs |
| .streamlit/config.toml | Streamlit configuration |

## Setup (once)

Requires Ubuntu/Linux, Python 3.12, Docker Engine and Docker Compose.
Internet is needed for initial downloads. Approximately 8 GB RAM is recommended.

Run all commands from the repository root.

```bash
/usr/bin/python3 -m venv .venv
source .venv/bin/activate

python -m pip --isolated install --upgrade pip \
  --index-url https://pypi.org/simple

python -m pip --isolated install --no-cache-dir \
  --index-url https://pypi.org/simple -r requirements.txt

python -m pip --isolated install --no-cache-dir --no-deps \
  -r requirements-cpu.txt

python -m pip check
python download_model.py
```

The model is cached outside the repository. Model weights and virtual
environments are excluded from Git.

## 1. Start the Monitoring Stack

Terminal 1:

```bash
docker compose -f compose.yml -f compose.grafana.yml \
  -f compose.alerting.yml up -d

docker compose -f compose.yml -f compose.grafana.yml \
  -f compose.alerting.yml ps
```

## 2. Start the Captioning Application

Terminal 2:

```bash
source .venv/bin/activate

HF_HUB_OFFLINE=1 python -m streamlit run app.py \
  --server.address 127.0.0.1 --server.port 8501
```

Open http://127.0.0.1:8501 inside Ubuntu.

- Single image: upload a photograph and click Generate captions.
- Bulk ZIP: upload a ZIP and click Generate captions.
- Download the generated captions using Download results CSV.

Supported formats: JPEG, PNG, WebP and AVIF.

Limits: 30 images per ZIP, 50 MiB ZIP size, 100 MiB expanded size,
10 MiB per image and 16 megapixels per image.

Opening the Streamlit page starts the separate metrics endpoint.
The model loads on the first caption request.

## 3. Start the Alert Receiver

Terminal 3:

```bash
source .venv/bin/activate
python alert_receiver.py
```

Notifications print in the terminal and are saved in logs/alerts.jsonl.

To demonstrate target downtime, stop Streamlit while monitoring and the
receiver remain running. After the 30-second pending period and notification
delay, check for a firing alert. Restart Streamlit and reopen its page to
restore scraping and receive a resolved notification.

## 4. Open Prometheus and Grafana

Use a browser inside the Ubuntu VM.

| Service | URL |
|---|---|
| Application | http://127.0.0.1:8501 |
| Application metrics | http://127.0.0.1:8001/metrics |
| Prometheus targets | http://127.0.0.1:9090/targets |
| Grafana | http://127.0.0.1:3000 |
| node_exporter | http://127.0.0.1:9100/metrics |
| Alertmanager | http://127.0.0.1:9093 |

Confirm caption_app, node, prometheus and alertmanager are UP.

For a fresh Grafana installation, sign in with admin/admin and change the
password. Use the saved password for an existing installation.

The A4 Prometheus data source is provisioned automatically.
Import grafana/dashboard.json using Dashboards → New → Import.
Select Last 15 minutes and keep refresh at 5s.

Run a bulk upload to observe throughput, latency and CPU/RAM alongside
active bulk jobs.

## 5. Instrumentation

| Type | Examples |
|---|---|
| Counter | Image attempts and completed upload jobs |
| Gauge | Active jobs, model readiness and process RAM |
| Histogram | Successful inference and complete job duration |
| Summary | Image-attempt duration, including failures |

Metrics include mode, outcome and session-derived client bucket labels.

Python Summary exports _sum and _count; counters export _total.
Client sessions are grouped into 16 buckets, so buckets do not identify
individual sessions or unique users.

Metric calculations and explanations are in docs/DESIGN.md.
AI prompts and dashboard queries are in docs/AI_PROMPTS_DASHBOARD.md.

## 6. Tests and Results

```bash
python -m pytest tests -q

docker compose -f compose.yml -f compose.grafana.yml \
  -f compose.alerting.yml config --quiet
```

Verified on the development VM:

- 24 automated tests passed.
- Single image: 1 success and 0 failures.
- Bulk ZIP: 27 successes and 0 failures.
- Dashboard: 28 total successful images.
- All four Prometheus targets UP.
- Bulk throughput and CPU activity visible.
- Downtime firing and recovery notifications received.

Captioner unit tests use mocks. Real CPU inference was tested separately.
Evidence screenshots and exported results are in evidence/.

## Stop

Stop Streamlit and the receiver with Ctrl+C, then run:

```bash
docker compose -f compose.yml -f compose.grafana.yml \
  -f compose.alerting.yml down
```

## Notes

- Use all three Compose files together.
- Counters reset when Streamlit restarts.
- Idle latency charts may have no recent observations.
- node_exporter measures the whole Ubuntu VM, including other processes.
- Captions may be inaccurate; inference uses one shared CPU model.
- Local demonstration inputs are excluded from Git.
- Recording links will be added before submission.
- Keep the repository private until the official deadline has passed.
