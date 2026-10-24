# Recording and Submission Guide

## Recording plan: approximately four minutes

| Time | What to show |
|---|---|
| 0:00–0:20 | Explain the objective and local architecture |
| 0:20–0:45 | Upload one image and generate its caption |
| 0:45–1:50 | Start a 20-image ZIP, then show the dashboard continuously for at least 60 seconds |
| 1:50–2:15 | Show Prometheus targets and application metrics |
| 2:15–2:40 | Process a valid/corrupted mixed ZIP and explain the two outcomes |
| 2:40–3:35 | Demonstrate or show saved evidence of firing and resolved notifications |
| 3:35–4:10 | Show tests, setup guide, key code, and limitations |

Adjust timing to stay within the required 2–5 minutes.

## Dashboard recording

Keep refresh set to 5 seconds and select a recent time range.
Generate fresh traffic immediately before or during recording.

Show a continuous dashboard segment lasting approximately one minute.
Include throughput, latency, and CPU/RAM alongside bulk activity.
Scroll deliberately so titles, units, and legends remain readable.

Provide:
1. The complete 2–5 minute demonstration.
2. A separate approximately one-minute dashboard clip, which may be exported
   from the continuous dashboard segment of the full recording.

The 20-image test uses repeated sample images to create load.
Do not describe it as a test of 20 distinct photographs.

## Before recording

- Start all monitoring containers.
- Start Streamlit and open its browser page.
- Start the local notification receiver.
- Generate a caption to load the model.
- Verify all four Prometheus targets are UP.
- Run fresh single and bulk jobs.
- Confirm the latency panels have recent observations.
- Keep Grafana refresh at 5s.
- Keep passwords and unrelated personal information out of the recording.

## Recording access

Upload the recordings to the platform permitted by the course.
Provide viewing access to evaluators.
If link-based viewing is allowed, test each link in a signed-out or private
browser window before submission.
Keep recordings accessible throughout evaluation.
Do not assume a local file path provides evaluator access.

Add the actual video links to the repository README before submission.
Do not commit large recordings to Git unnecessarily.

## GitHub visibility

- Create the repository as PRIVATE.
- Keep it private until the official assignment deadline has passed.
- Submit its actual URL through the official college Google Form.
- Make it PUBLIC only after the deadline, following course instructions.
- Verify public repository access from a signed-out browser afterward.

Obtain the deadline and submission form URL from the official announcement.

## Required repository contents

- app.py, captioner.py, uploads.py, metrics.py
- download_model.py and alert_receiver.py
- requirements.txt and requirements-cpu.txt
- .streamlit/config.toml
- prometheus.yml and alerts.yml
- alertmanager.yml
- compose.yml, compose.grafana.yml, compose.alerting.yml
- grafana/provisioning/datasources/prometheus.yml
- grafana/dashboard.json
- build_dashboard.py and polish_dashboard.py
- tests/
- README.md, DESIGN.md, SUBMISSION.md
- AI_PROMPTS_DASHBOARD.md
- .gitignore

Include any additional final verification and attribution files created
during the submission review.

Exclude virtual environments, model weights, credentials, local logs,
temporary backups, and unnecessary test archives.

## Rubric checklist: 60 marks

| Category | Marks | Evidence to prepare |
|---|---:|---|
| Python instrumentation | 25 | All four metric types, correct update semantics, bounded client labels, exported series, tests, and manual calculations |
| Node exporting | 5 | node_exporter target UP and Ubuntu CPU/RAM/disk metrics |
| Grafana intuitiveness | 20 | Logical layout, inclusive presentation, labels, units, legends, titles, descriptions, and bulk/resource correlation |
| Application logic | 10 | Working CPU single/bulk workflows, progress, results, limits, and error handling |

This is a preparation checklist, not a guarantee of marks.

## Final review

- Run the automated tests.
- Validate Prometheus configuration, alert rules, and Alertmanager configuration.
- Verify the dashboard JSON imports successfully.
- Confirm that setup instructions match the final files.
- Preserve evidence of real-model and notification tests.
- Add working recording links.
- Verify the repository is private before the deadline.
- Submit the correct repository URL through the official form.
