from unittest.mock import Mock

import pytest
from PIL import Image
from prometheus_client import CollectorRegistry

import captioner as module
from metrics import AppMetrics


@pytest.fixture
def fake_captioner(monkeypatch):
    registry = CollectorRegistry()
    metrics = AppMetrics(registry)
    monkeypatch.setattr(module, "METRICS", metrics)

    processor = Mock()
    processor.return_value = {"pixel_values": "fake-image-tensor"}
    processor.decode.return_value = "a dog sitting in the grass"

    model = Mock()
    model.to.return_value = model
    model.eval.return_value = model
    model.parameters.return_value = []
    model.generate.return_value = [[1, 2, 3]]

    monkeypatch.setattr(
        module.BlipProcessor, "from_pretrained", Mock(return_value=processor)
    )
    monkeypatch.setattr(
        module.BlipForConditionalGeneration,
        "from_pretrained",
        Mock(return_value=model),
    )

    instance = module.CPUCaptioner()
    return instance, model, processor, registry


def test_caption_and_cpu_configuration(fake_captioner):
    instance, model, processor, registry = fake_captioner

    result = instance.caption(Image.new("RGB", (32, 32)), mode="single")

    assert result == "a dog sitting in the grass"
    model.to.assert_called_once_with("cpu")
    model.eval.assert_called_once()
    assert model.generate.call_args.kwargs["do_sample"] is False
    assert registry.get_sample_value("caption_model_ready") == 1
    assert registry.get_sample_value(
        "caption_inference_seconds_count", {"mode": "single"}
    ) == 1


def test_model_error_releases_lock_and_allows_retry(fake_captioner):
    instance, model, processor, registry = fake_captioner
    model.generate.side_effect = RuntimeError("Simulated model failure")

    with pytest.raises(RuntimeError, match="Simulated model failure"):
        instance.caption(Image.new("RGB", (32, 32)), mode="bulk")

    assert not instance.lock.locked()
    assert registry.get_sample_value(
        "caption_inference_seconds_count", {"mode": "bulk"}
    ) == 0

    model.generate.side_effect = None
    assert instance.caption(Image.new("RGB", (32, 32)), mode="bulk")
    assert registry.get_sample_value(
        "caption_inference_seconds_count", {"mode": "bulk"}
    ) == 1


def test_empty_caption_rejected(fake_captioner):
    instance, model, processor, registry = fake_captioner
    processor.decode.return_value = "   "

    with pytest.raises(RuntimeError, match="empty caption"):
        instance.caption(Image.new("RGB", (32, 32)))

    assert not instance.lock.locked()
    assert registry.get_sample_value(
        "caption_inference_seconds_count", {"mode": "single"}
    ) == 0


def test_invalid_mode_rejected(fake_captioner):
    instance, model, processor, registry = fake_captioner

    with pytest.raises(ValueError, match="Invalid captioning mode"):
        instance.caption(Image.new("RGB", (32, 32)), mode="invalid")

    model.generate.assert_not_called()
