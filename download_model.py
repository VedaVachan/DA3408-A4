"""Download and verify model files before starting the offline app."""

import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

MODEL_ID = "Salesforce/blip-image-captioning-base"


def main():
    torch.set_num_threads(4)
    print("Preparing model files. Internet is needed for uncached files.", flush=True)

    BlipProcessor.from_pretrained(MODEL_ID)
    model = BlipForConditionalGeneration.from_pretrained(
        MODEL_ID, use_safetensors=True
    ).to("cpu").eval()

    print("Model files are cached.")
    print("Verified model device:", next(model.parameters()).device)


if __name__ == "__main__":
    main()
