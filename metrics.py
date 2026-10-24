"""Prometheus metric definitions for image captioning."""

import hashlib

import psutil
from prometheus_client import (
    REGISTRY, Counter, Gauge, Histogram, Summary,
)


def session_bucket(session_id: str) -> str:
    """Group sessions into 16 buckets to bound metric cardinality."""
    digest = hashlib.sha256(session_id.encode()).digest()
    return str(digest[0] % 16)


class AppMetrics:
    def __init__(self, registry=REGISTRY):
        self.images = Counter(
            "caption_images_total",
            "Image attempts completed, including validation failures.",
            ["mode", "status"],
            registry=registry,
        )
        self.jobs = Counter(
            "caption_jobs_total",
            "Upload jobs completed.",
            ["mode", "status", "client_bucket"],
            registry=registry,
        )
        self.active_jobs = Gauge(
            "caption_active_jobs",
            "Upload jobs currently running, including queued jobs.",
            ["mode"],
            registry=registry,
        )
        self.inference = Histogram(
            "caption_inference_seconds",
            "Successful processor and model generation time; excludes queue wait.",
            ["mode"],
            buckets=(0.1, 0.25, 0.5, 1, 2, 2.5, 3, 4, 5, 8, 10, 20, 40, 60),
            registry=registry,
        )
        self.image_duration = Summary(
            "caption_image_duration_seconds",
            "Time per completed image attempt, including queue wait and errors.",
            ["mode", "status"],
            registry=registry,
        )
        self.job_duration = Histogram(
            "caption_job_duration_seconds",
            "Upload job duration, including validation and model loading.",
            ["mode"],
            buckets=(1, 2, 5, 10, 20, 40, 60, 120, 180, 300, 600),
            registry=registry,
        )
        self.model_ready = Gauge(
            "caption_model_ready",
            "One when the shared model has loaded successfully.",
            registry=registry,
        )
        self.model_weight_bytes = Gauge(
            "caption_model_weight_bytes",
            "Bytes occupied by model parameters; excludes runtime allocations.",
            registry=registry,
        )
        self.process_ram = Gauge(
            "caption_app_resident_memory_bytes",
            "Current application process resident memory, including the model.",
            registry=registry,
        )
        process = psutil.Process()
        self.process_ram.set_function(lambda: process.memory_info().rss)

        for mode in ("single", "bulk"):
            self.active_jobs.labels(mode).set(0)
            self.inference.labels(mode)
            self.job_duration.labels(mode)
            for status in ("success", "failed"):
                self.images.labels(mode, status)
                self.image_duration.labels(mode, status)


METRICS = AppMetrics()
