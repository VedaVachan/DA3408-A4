from io import BytesIO
from zipfile import ZipFile

import pytest
from PIL import Image

from uploads import (
    MAX_IMAGE_BYTES,
    MAX_IMAGES,
    UploadError,
    load_image,
    read_zip,
)


def image_bytes():
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "blue").save(buffer, format="JPEG")
    return buffer.getvalue()


def zip_bytes(entries):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return buffer.getvalue()


def test_single_image():
    image = load_image(image_bytes())
    assert image.size == (32, 32)
    assert image.mode == "RGB"


def test_bulk_images():
    content = image_bytes()
    items = read_zip(zip_bytes([
        ("first.jpg", content),
        ("folder/second.jpg", content),
    ]))
    assert len(items) == 2
    for _, data in items:
        assert load_image(data).size == (32, 32)


@pytest.mark.parametrize("data", [b"", b"not an image"])
def test_invalid_image(data):
    with pytest.raises(UploadError):
        load_image(data)


def test_oversized_image():
    with pytest.raises(UploadError):
        load_image(b"x" * (MAX_IMAGE_BYTES + 1))


@pytest.mark.parametrize("data", [b"", b"not a zip"])
def test_invalid_zip(data):
    with pytest.raises(UploadError):
        read_zip(data)


def test_empty_archive():
    with pytest.raises(UploadError):
        read_zip(zip_bytes([]))


@pytest.mark.parametrize("name", [
    "../escape.jpg",
    "/absolute.jpg",
    r"..\escape.jpg",
    "C:/escape.jpg",
])
def test_unsafe_paths(name):
    with pytest.raises(UploadError):
        read_zip(zip_bytes([(name, image_bytes())]))


def test_image_count_limit():
    content = image_bytes()
    entries = [(f"{i}.jpg", content) for i in range(MAX_IMAGES + 1)]
    with pytest.raises(UploadError):
        read_zip(zip_bytes(entries))


def test_unsupported_files_skipped():
    items = read_zip(zip_bytes([
        ("notes.txt", b"notes"),
        ("valid.jpg", image_bytes()),
    ]))
    assert [name for name, _ in items] == ["valid.jpg"]


def test_mixed_archive_preserves_valid_image():
    items = read_zip(zip_bytes([
        ("valid.jpg", image_bytes()),
        ("corrupt.jpg", b"invalid image"),
    ]))
    outcomes = []
    for _, content in items:
        try:
            load_image(content)
            outcomes.append("success")
        except UploadError:
            outcomes.append("failed")

    assert outcomes == ["success", "failed"]
