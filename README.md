# AIOps Assignment 4 — Application Monitoring

I built a CPU-only Streamlit app that generates image captions using Salesforce BLIP. It supports single-image and bulk ZIP uploads, with monitoring through Prometheus, node_exporter, Grafana and Alertmanager.

## Project Structure

| Files / folder | Purpose |
|---|---|
| `app.py`, `captioner.py`, `uploads.py` | Interface, caption generation and upload validation |
| `metrics.py` | Prometheus metrics |
| `download_model.py` | Download and cache the model |
| `compose*.yml`, `prometheus.yml` | Monitoring services and scrape configuration |
| `alerts.yml`, `alertmanager.yml`, `alert_receiver.py` | Alert rules and notifications |
| `grafana/` | Dashboard JSON and data-source configuration |
| `tests/` | Automated tests |
| `AI_PROMPTS_DASHBOARD.md` | AI assistance and complex dashboard queries |
| `evidence/` | Screenshots and caption results |

## Project Structure

```text
DA3408-A4/
├── app.py                        # Streamlit interface for single and bulk uploads
├── captioner.py                  # Generate image captions using BLIP on CPU
├── uploads.py                    # Validate uploaded images and ZIP files
├── metrics.py                    # Define application metrics for Prometheus
├── download_model.py             # Download and cache the BLIP model
├── requirements.txt              # Python application dependencies
├── requirements-cpu.txt          # CPU-only PyTorch dependencies
├── compose.yml                   # Run Prometheus and node_exporter
├── compose.grafana.yml           # Run Grafana
├── compose.alerting.yml          # Run Alertmanager and mount alert rules
├── prometheus.yml                # Configure metric scraping and alert evaluation
├── alerts.yml                    # Define monitoring alert conditions
├── alertmanager.yml              # Route alerts to the local receiver
├── alert_receiver.py             # Receive and save alert notifications
├── build_dashboard.py            # Generate the Grafana dashboard JSON
├── polish_dashboard.py           # Apply dashboard layout and styling
├── grafana/
│   ├── dashboard.json            # Dashboard export to import into Grafana
│   └── provisioning/datasources/
│       └── prometheus.yml        # Configure Grafana's Prometheus connection
├── demo_inputs/
│   ├── sample.jpg                # Photograph for the single-image demo
│   ├── bulk size pics.zip        # Archive for the bulk-upload demo
│   └── bulk size pics/           # Original photographs used in the ZIP
├── evidence/
│   ├── *.png                     # Screenshots of the app, dashboard and tests
│   ├── bulk_captions.csv         # Exported bulk-caption results
│   └── single_captions.csv       # Exported single-image result
├── logs/
│   └── alerts.jsonl              # Locally recorded alert notifications
├── tests/
│   ├── test_captioner.py         # Test caption generation using mocks
│   ├── test_metrics.py           # Test metric values and export
│   └── test_uploads.py           # Test image and ZIP validation
├── AI_DISCLOSURE.md              # Summary of AI assistance used
├── AI_PROMPTS_DASHBOARD.md       # Dashboard prompts and query assistance
└── README.md                     # Project overview and setup instructions
```

`demo_inputs/` and `logs/` are local folders excluded from Git.


## Setup

Requires Ubuntu/Linux, Python 3.12, Docker and Docker Compose. Run all commands from the repository folder.

```bash
/usr/bin/python3 -m venv .venv
source .venv/bin/activate

python -m pip --isolated install --no-cache-dir \
  --index-url https://pypi.org/simple -r requirements.txt

python -m pip --isolated install --no-cache-dir --no-deps \
  -r requirements-cpu.txt

python -m pip check
python download_model.py
```

Internet is needed for initial downloads. Caption generation runs locally on CPU.

## Run

**Terminal 1 — Monitoring:**

```bash
cd ~/assignments/DA3408-A4
docker compose -f compose.yml -f compose.grafana.yml \
  -f compose.alerting.yml up -d
```

**Terminal 2 — Application:**

```bash
cd ~/assignments/DA3408-A4
source .venv/bin/activate

HF_HUB_OFFLINE=1 python -m streamlit run app.py \
  --server.address 127.0.0.1 --server.port 8501
```

**Terminal 3 — Alert receiver:**

```bash
cd ~/assignments/DA3408-A4
source .venv/bin/activate
python alert_receiver.py
```

## Open and Use

Open these addresses inside Ubuntu:

| Service | URL |
|---|---|
| Application | http://127.0.0.1:8501 |
| Prometheus targets | http://127.0.0.1:9090/targets |
| Grafana | http://127.0.0.1:3000 |
| Application metrics | http://127.0.0.1:8001/metrics |
| Alertmanager | http://127.0.0.1:9093 |

Select **Single image** or **Bulk ZIP**, upload your file and click **Generate captions**. Results can be downloaded as CSV. ZIP uploads support up to **30 images**.

Demo photographs are local files excluded from Git. Use your own JPEG, PNG, WebP or AVIF photograph for single-image testing, or create a ZIP containing up to 30 supported images for bulk testing.

Opening the app page starts the metrics endpoint. The model loads on the first caption request.

For a fresh Grafana installation, log in with `admin/admin` and change the password. Import `grafana/dashboard.json`, select **Last 15 minutes** and set refresh to **5s**.

## Verification

```bash
python -m pytest tests -q
```

Verified on my VM:

- **24 automated tests passed.**
- One single image and **27 bulk images** processed successfully.
- All four Prometheus targets were UP.
- Bulk throughput and CPU activity appeared in Grafana.
- Downtime firing and recovery notifications reached the receiver.

Captioner unit tests use mocks; real inference was tested separately.

The app uses Counter, Gauge, Histogram and Summary metrics. Client labels use 16 session-derived buckets, which do not identify unique users. Dashboard prompts and query assistance are documented in `AI_PROMPTS_DASHBOARD.md`. Overall AI use is described in `AI_DISCLOSURE.md`.

## Stop

Press **Ctrl+C** in the application and receiver terminals, then run:

```bash
docker compose -f compose.yml -f compose.grafana.yml \
  -f compose.alerting.yml down
```
