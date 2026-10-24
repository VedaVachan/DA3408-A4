from urllib.request import urlopen

import pytest
from prometheus_client import CollectorRegistry, start_http_server

from metrics import AppMetrics, session_bucket


@pytest.fixture
def monitored():
    registry = CollectorRegistry()
    return AppMetrics(registry), registry


def test_image_counts_separate_modes_and_outcomes(monitored):
    metrics, registry = monitored
    metrics.images.labels("single", "success").inc()
    metrics.images.labels("bulk", "success").inc(2)
    metrics.images.labels("bulk", "failed").inc()

    for mode, status, expected in [
        ("single", "success", 1),
        ("single", "failed", 0),
        ("bulk", "success", 2),
        ("bulk", "failed", 1),
    ]:
        assert registry.get_sample_value(
            "caption_images_total", {"mode": mode, "status": status}
        ) == expected


def test_latency_histogram_and_summary(monitored):
    metrics, registry = monitored
    for duration in (2, 4):
        metrics.inference.labels("bulk").observe(duration)
        metrics.image_duration.labels("bulk", "success").observe(duration)

    assert registry.get_sample_value(
        "caption_inference_seconds_bucket", {"mode": "bulk", "le": "2.5"}
    ) == 1
    assert registry.get_sample_value(
        "caption_inference_seconds_count", {"mode": "bulk"}
    ) == 2
    assert registry.get_sample_value(
        "caption_inference_seconds_sum", {"mode": "bulk"}
    ) == 6

    labels = {"mode": "bulk", "status": "success"}
    assert registry.get_sample_value(
        "caption_image_duration_seconds_count", labels
    ) == 2
    assert registry.get_sample_value(
        "caption_image_duration_seconds_sum", labels
    ) == 6


def test_active_jobs_cleanup_on_failure(monitored):
    metrics, registry = monitored

    with pytest.raises(RuntimeError):
        with metrics.active_jobs.labels("bulk").track_inprogress():
            assert registry.get_sample_value(
                "caption_active_jobs", {"mode": "bulk"}
            ) == 1
            raise RuntimeError("Simulated processing failure")

    assert registry.get_sample_value(
        "caption_active_jobs", {"mode": "bulk"}
    ) == 0


def test_session_buckets_are_stable_and_bounded():
    assert session_bucket("same-session") == session_bucket("same-session")
    buckets = {session_bucket(str(number)) for number in range(1000)}
    assert buckets <= {str(number) for number in range(16)}


def test_metrics_http_endpoint(monitored):
    metrics, registry = monitored
    metrics.images.labels("single", "success").inc()

    server, thread = start_http_server(
        0, addr="127.0.0.1", registry=registry
    )
    try:
        url = f"http://127.0.0.1:{server.server_port}/metrics"
        with urlopen(url, timeout=5) as response:
            assert response.status == 200
            text = response.read().decode()

        assert 'caption_images_total{mode="single",status="success"} 1.0' in text
        assert "# TYPE caption_inference_seconds histogram" in text
        assert "# TYPE caption_image_duration_seconds summary" in text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
