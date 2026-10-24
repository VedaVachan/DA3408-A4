"""Improve dashboard layout without changing its PromQL queries."""

import json
from pathlib import Path

path = Path("grafana/dashboard.json")
dashboard = json.loads(path.read_text())
backup = Path("grafana/dashboard.before_polish.json")

if not backup.exists():
    backup.write_text(json.dumps(dashboard, indent=2) + "\n")

stats = [p for p in dashboard["panels"] if p["type"] == "stat"]

for index, item in enumerate(stats):
    item["gridPos"].update(
        x=(index % 3) * 8,
        y=(index // 3) * 4,
        w=8,
        h=4,
    )

for item in dashboard["panels"]:
    if item["type"] != "stat":
        item["gridPos"]["y"] = backup_y = next(
            original["gridPos"]["y"]
            for original in json.loads(backup.read_text())["panels"]
            if original["id"] == item["id"]
        ) + 4

    if item["title"] in {
        "Successful throughput",
        "Active jobs by mode",
    }:
        custom = item["fieldConfig"]["defaults"]["custom"]
        custom["axisSoftMax"] = (
            1 if item["title"] == "Successful throughput" else 2
        )

    if item["title"] in {
        "CPU utilisation and bulk activity",
        "RAM utilisation and bulk activity",
    }:
        for override in item["fieldConfig"]["overrides"]:
            if override["matcher"] == {
                "id": "byName", "options": "Active bulk jobs"
            }:
                properties = override["properties"]
                properties[:] = [
                    p for p in properties
                    if p["id"] != "custom.axisSoftMax"
                ]
                properties.append({
                    "id": "custom.axisSoftMax", "value": 2
                })

    if item["title"] == "Active jobs by mode":
        item["gridPos"].update(x=0, y=56, w=24, h=6)

    if item["title"] == "Client bucket job counts":
        item["gridPos"].update(x=0, y=62, w=24, h=7)
        item["transformations"] = [{
            "id": "organize",
            "options": {
                "excludeByName": {"Time": True},
                "indexByName": {
                    "client_bucket": 0,
                    "mode": 1,
                    "status": 2,
                    "Value": 3,
                },
                "renameByName": {
                    "client_bucket": "Client bucket",
                    "mode": "Mode",
                    "status": "Outcome",
                    "Value": "Jobs",
                },
            },
        }]

dashboard["version"] = 2
path.write_text(json.dumps(dashboard, indent=2) + "\n")
print("Updated:", path)
print("Panels:", len(dashboard["panels"]))
print("Refresh:", dashboard["refresh"])
