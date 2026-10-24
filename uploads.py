"""Validate image uploads and safely read ZIP archives."""

import warnings
from io import BytesIO
from pathlib import PurePosixPath
from stat import S_ISLNK
from zipfile import BadZipFile, ZipFile

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_IMAGES = 30
MAX_PIXELS = 16_000_000
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


class UploadError(ValueError):
    """An upload cannot be processed safely."""


def load_image(data: bytes) -> Image.Image:
    if not data:
        raise UploadError("The image is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise UploadError("Each image must be 10 MiB or smaller.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.width * source.height > MAX_PIXELS:
                    raise UploadError("Each image must be 16 megapixels or smaller.")
                if source.format not in {"JPEG", "PNG", "WEBP", "AVIF"}:
                    raise UploadError("Use JPEG, PNG, WebP, or AVIF images.")
                source.load()
                return ImageOps.exif_transpose(source).convert("RGB")
    except UploadError:
        raise
    except (
        UnidentifiedImageError, OSError, ValueError,
        Image.DecompressionBombError, Image.DecompressionBombWarning,
    ) as exc:
        raise UploadError("The image is corrupted or cannot be decoded.") from exc


def read_zip(data: bytes) -> list[tuple[str, bytes]]:
    if not data:
        raise UploadError("The ZIP upload is empty.")
    if len(data) > MAX_ZIP_BYTES:
        raise UploadError("The ZIP must be 50 MiB or smaller.")

    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 200:
                raise UploadError("The ZIP contains too many entries.")

            images = []
            expanded = 0

            for entry in entries:
                name = entry.filename.replace("\\", "/")
                path = PurePosixPath(name)

                if path.is_absolute() or ".." in path.parts or ":" in name:
                    raise UploadError("The ZIP contains an unsafe file path.")
                if S_ISLNK(entry.external_attr >> 16):
                    raise UploadError("Symbolic links are not allowed.")
                if entry.flag_bits & 1:
                    raise UploadError("Password-protected ZIPs are not supported.")

                expanded += entry.file_size
                if expanded > MAX_EXPANDED_BYTES:
                    raise UploadError("The expanded ZIP exceeds 100 MiB.")

                if entry.is_dir() or path.suffix.lower() not in EXTENSIONS:
                    continue
                if len(images) >= MAX_IMAGES:
                    raise UploadError("A ZIP may contain at most 30 images.")
                if entry.file_size > MAX_IMAGE_BYTES:
                    raise UploadError(f"Image exceeds 10 MiB: {name}")

                with archive.open(entry) as stream:
                    content = stream.read(MAX_IMAGE_BYTES + 1)
                if len(content) > MAX_IMAGE_BYTES:
                    raise UploadError(f"Image exceeds 10 MiB: {name}")

                images.append((name, content))

            if not images:
                raise UploadError("The ZIP contains no supported images.")
            return images

    except UploadError:
        raise
    except (BadZipFile, OSError, RuntimeError, NotImplementedError, EOFError) as exc:
        raise UploadError("The ZIP is corrupted or uses unsupported compression.") from exc
