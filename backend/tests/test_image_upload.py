"""Upload regressions: real codecs, temporary storage, no database access."""

from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
import re
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin, UnidentifiedImageError
from starlette.datastructures import Headers

from app.auth.auth import get_current_admin_user
from app.dependencies import get_event_service
from app.main import app
from app.services.event_service import EventService
from app.services.exceptions import InvalidImageError


def image_bytes(fmt="PNG", **kwargs):
    output = BytesIO()
    with Image.new("RGB", (16, 16), "red") as image:
        image.save(output, format=fmt, **kwargs)
    return output.getvalue()


@contextmanager
def upload(content, filename="cover.png", mime="image/png"):
    file = UploadFile(
        file=BytesIO(content), filename=filename,
        headers=Headers({"content-type": mime}) if mime else Headers(),
    )
    try:
        yield file
    finally:
        file.file.close()


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(EventService, "_UPLOAD_DIR", tmp_path / "uploads")
    return EventService(None)


@pytest.mark.parametrize("fmt,extension", [("JPEG", ".jpg"), ("PNG", ".png"), ("WEBP", ".webp")])
@pytest.mark.parametrize("mime", ["image/jpeg", "text/html", "application/octet-stream", None])
def test_format_and_filename_come_from_content(service, fmt, extension, mime):
    with upload(image_bytes(fmt), "../../unsafe\\cover.html", mime) as file:
        url = service.save_image(file)
    assert re.fullmatch(r"/static/uploads/[0-9a-f]{32}" + re.escape(extension), url)
    saved = service._UPLOAD_DIR / Path(url).name
    with Image.open(saved) as image:
        assert image.format == fmt
        image.load()
        assert image.size == (16, 16)


@pytest.mark.parametrize("payload", [
    b"", b"<script>alert(1)</script>", b"<svg xmlns='http://www.w3.org/2000/svg'/>",
    b"\xff\xd8\xff\xe0fake JPEG", b"\x89PNG\r\n\x1a\nfake PNG", b"RIFF\x10\0\0\0WEBPfake",
])
def test_fake_or_empty_image_is_rejected_without_files(service, payload):
    with upload(payload) as file, pytest.raises(InvalidImageError):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


@pytest.mark.parametrize("fmt", ["GIF", "BMP", "TIFF"])
def test_other_decodable_formats_are_rejected(service, fmt):
    with upload(image_bytes(fmt)) as file, pytest.raises(InvalidImageError):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_truncated_image_is_rejected(service, fmt):
    data = image_bytes(fmt)
    with upload(data[:len(data) // 2]) as file, pytest.raises(InvalidImageError):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


def test_invalid_png_checksum_is_rejected(service):
    data = bytearray(image_bytes())
    chunk = data.index(b"IDAT")
    length = int.from_bytes(data[chunk - 4:chunk], "big")
    data[chunk + 4 + length] ^= 1  # Corrupt the image-data checksum.
    with upload(bytes(data)) as file, pytest.raises(InvalidImageError):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


def test_recognizable_jpeg_with_truncated_pixels_is_rejected(service):
    data = image_bytes("JPEG")[:-2]
    with Image.open(BytesIO(data)) as image:
        assert image.format == "JPEG"
        image.verify()  # Header/structure checks alone do not catch this.
    with upload(data) as file, pytest.raises(InvalidImageError):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


def test_file_larger_than_five_megabytes_is_rejected(service, monkeypatch):
    data = image_bytes() + b"x" * service._MAX_UPLOAD_SIZE

    def unexpected_decode(*args, **kwargs):
        pytest.fail("Oversized input reached the decoder")

    monkeypatch.setattr(Image, "open", unexpected_decode)
    with upload(data) as file, pytest.raises(InvalidImageError, match="5MB"):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


@pytest.mark.parametrize("error", [
    UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError,
])
def test_decoder_errors_return_http_400(api, service, monkeypatch, error):
    data = image_bytes()

    def broken_decoder(*args, **kwargs):
        raise error("decoder failure")

    monkeypatch.setattr(Image, "open", broken_decoder)
    response = api.post("/events/upload-image", files={"file": ("cover.png", data, "image/png")})
    assert response.status_code == 400
    assert "valid JPG, PNG or WebP" in response.json()["detail"]
    assert list(service._UPLOAD_DIR.iterdir()) == []


def test_exact_size_limit_is_allowed_and_trailing_payload_removed(service):
    data = image_bytes()
    data += b"x" * (service._MAX_UPLOAD_SIZE - len(data))
    with upload(data) as file:
        url = service.save_image(file)
    saved = (service._UPLOAD_DIR / Path(url).name).read_bytes()
    assert len(saved) < service._MAX_UPLOAD_SIZE
    assert b"x" * 100 not in saved


def test_pixel_limit_rejects_before_decoding(service, monkeypatch):
    monkeypatch.setattr(service, "_MAX_IMAGE_PIXELS", 255)
    with upload(image_bytes()) as file, pytest.raises(InvalidImageError, match="pixels"):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


def test_encoded_output_also_obeys_size_limit(service, monkeypatch):
    data = image_bytes("PNG", optimize=True)
    monkeypatch.setattr(service, "_MAX_UPLOAD_SIZE", len(data))
    # Normalized RGBA output is larger than the optimized RGB input.
    with upload(data) as file, pytest.raises(InvalidImageError, match="Encoded"):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


def test_metadata_is_removed_and_names_are_unique(service):
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "untrusted metadata")
    data = image_bytes(pnginfo=metadata)
    urls = []
    for _ in range(2):
        with upload(data) as file:
            urls.append(service.save_image(file))
    assert len(set(urls)) == 2
    with Image.open(service._UPLOAD_DIR / Path(urls[0]).name) as image:
        assert "Comment" not in image.info


def test_exif_orientation_is_applied_before_metadata_removal(service):
    output = BytesIO()
    with Image.new("RGB", (16, 8), "red") as image:
        exif = Image.Exif()
        exif[274] = 6  # Display rotated 90 degrees clockwise.
        exif[315] = "private author"
        image.save(output, format="JPEG", exif=exif)
    with upload(output.getvalue()) as file:
        url = service.save_image(file)
    with Image.open(service._UPLOAD_DIR / Path(url).name) as saved:
        assert saved.size == (8, 16)
        assert not saved.getexif()


@pytest.mark.parametrize("fmt", ["PNG", "WEBP"])
def test_animated_images_are_rejected(service, fmt):
    output = BytesIO()
    with Image.new("RGB", (16, 16), "red") as first, Image.new("RGB", (16, 16), "blue") as second:
        first.save(output, format=fmt, save_all=True, append_images=[second], duration=100)
    with upload(output.getvalue()) as file, pytest.raises(InvalidImageError, match="Animated"):
        service.save_image(file)
    assert list(service._UPLOAD_DIR.iterdir()) == []


def test_missing_filename_is_rejected(service):
    with upload(image_bytes(), filename=None) as file, pytest.raises(InvalidImageError):
        service.save_image(file)


@pytest.fixture
def api(service):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_event_service] = lambda: service
    app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(id=1, is_admin=True)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_api_preserves_success_and_validation_error_contract(api, service):
    response = api.post("/events/upload-image", files={"file": ("cover.png", image_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["image_url"].endswith(".png")
    response = api.post("/events/upload-image", files={"file": ("fake.png", b"not an image", "image/png")})
    assert response.status_code == 400
    assert "valid JPG, PNG or WebP" in response.json()["detail"]
    assert len(list(service._UPLOAD_DIR.iterdir())) == 1


def test_upload_requires_authentication(service):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_event_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post("/events/upload-image", files={"file": ("cover.png", image_bytes(), "image/png")})
        assert response.status_code in (401, 403)
        assert list(service._UPLOAD_DIR.iterdir()) == []
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
