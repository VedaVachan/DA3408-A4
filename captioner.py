"""CPU-only image caption generation with inference metrics."""

import time
from threading import Lock

import torch
from PIL import Image, ImageOps
from transformers import BlipProcessor, BlipForConditionalGeneration

from metrics import METRICS

MODEL_ID = "Salesforce/blip-image-captioning-base"


class CPUCaptioner:
    def __init__(self):
        torch.set_num_threads(4)
        self.lock = Lock()

        self.processor = BlipProcessor.from_pretrained(
            MODEL_ID, local_files_only=True
        )
        self.model = BlipForConditionalGeneration.from_pretrained(
            MODEL_ID, local_files_only=True
        ).to("cpu").eval()

        weight_bytes = sum(
            parameter.numel() * parameter.element_size()
            for parameter in self.model.parameters()
        )
        METRICS.model_weight_bytes.set(weight_bytes)
        METRICS.model_ready.set(1)

    def caption(self, image: Image.Image, mode: str = "single") -> str:
        if mode not in {"single", "bulk"}:
            raise ValueError("Invalid captioning mode.")

        with self.lock:
            image = ImageOps.exif_transpose(image).convert("RGB")
            start = time.perf_counter()
            inputs = self.processor(images=image, return_tensors="pt")

            with torch.inference_mode():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=30,
                    num_beams=1,
                    do_sample=False,
                )

            text = self.processor.decode(
                output[0], skip_special_tokens=True
            ).strip()

            if not text:
                raise RuntimeError("The model returned an empty caption.")

            METRICS.inference.labels(mode).observe(
                time.perf_counter() - start
            )
            return text
