"""Build with an ignored .env canary, then inspect every saved image layer.

Usage: python3 tests/image-smoke.py UNIQUE_TEST_IMAGE_TAG
Does not start containers or touch volumes. Leaves the test image for inspection.
"""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

root = Path(__file__).resolve().parents[1]
image = sys.argv[1]
assert image.startswith("afisha-pr10-"), "Use a dedicated test image tag"
canary = root / ".env.pr10-smoke-canary"
marker = b"PR10_IMAGE_SECRET_CANARY_MUST_NOT_BE_PRESENT"
with canary.open("xb") as stream:
    stream.write(b"SECRET_KEY=" + marker + b"\n")
try:
    subprocess.run(["docker", "build", "-t", image, str(root)], check=True)
finally:
    canary.unlink()
config = json.loads(subprocess.check_output(["docker", "image", "inspect", image]))[0]
assert config["Config"]["User"] == "node"
for env in config["Config"]["Env"]:
    assert env.split("=", 1)[0] not in {"SECRET_KEY", "DATABASE_URL", "ADMIN_PASSWORD", "POSTGRES_PASSWORD", "INTERNAL_API_URL"}
with tempfile.TemporaryDirectory(prefix="afisha-pr10-image-") as directory:
    archive = Path(directory) / "image.tar"
    subprocess.run(["docker", "image", "save", "-o", str(archive), image], check=True)
    with tarfile.open(archive) as saved:
        manifest = json.load(saved.extractfile("manifest.json"))
        for layer_name in manifest[0]["Layers"]:
            with tarfile.open(fileobj=io.BytesIO(saved.extractfile(layer_name).read())) as layer:
                for entry in layer:
                    if not entry.isfile():
                        continue
                    assert not Path(entry.name).name.startswith(".env"), entry.name
                    with layer.extractfile(entry) as content:
                        tail = b""
                        while chunk := content.read(1024 * 1024):
                            data = tail + chunk
                            assert marker not in data, entry.name
                            tail = data[-len(marker):]
print(f"PASS image: non-root, no backend credentials/config, no .env/canary in any layer; {config['Size']} bytes")
