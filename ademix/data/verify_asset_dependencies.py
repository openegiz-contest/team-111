"""D8: prove every runtime model/texture dependency is local and case-correct."""

import json
import re
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
FRONTEND = ROOT / "ademix" / "frontend"
PUBLIC = FRONTEND / "public"
SOURCE = FRONTEND / "src"
RUNTIME_EXTENSIONS = (".glb", ".gltf", ".png", ".jpg", ".jpeg", ".webp", ".svg")


def exact_case_path(root: Path, relative: str) -> Path:
    current = root
    for part in Path(relative).parts:
        matches = [entry for entry in current.iterdir() if entry.name == part]
        if not matches:
            raise AssertionError(f"missing or wrong-case asset path: {relative}")
        current = matches[0]
    return current


def glb_json(path: Path) -> dict:
    raw = path.read_bytes()
    if raw[:4] != b"glTF" or len(raw) < 20:
        raise AssertionError(f"invalid GLB header: {path}")
    _, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if version != 2 or declared_length != len(raw):
        raise AssertionError(f"invalid GLB version/length: {path}")
    chunk_length, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != 0x4E4F534A:
        raise AssertionError(f"first GLB chunk is not JSON: {path}")
    return json.loads(raw[20:20 + chunk_length].decode("utf-8").rstrip(" \t\r\n\0"))


class AssetDependencyTests(unittest.TestCase):
    def test_every_runtime_asset_reference_is_repository_local_and_exists_exactly(self):
        references = set()
        remote_references = []
        quoted = re.compile(r"['\"]([^'\"]+\.(?:glb|gltf|png|jpe?g|webp|svg))['\"]", re.I)
        css_url = re.compile(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", re.I)
        for path in SOURCE.rglob("*"):
            if path.suffix.lower() not in {".ts", ".tsx", ".css"}:
                continue
            text = path.read_text(encoding="utf-8")
            for value in quoted.findall(text) + css_url.findall(text):
                if value.startswith(("http://", "https://", "//")):
                    remote_references.append((path, value))
                elif Path(value.split("?", 1)[0]).suffix.lower() in RUNTIME_EXTENSIONS:
                    references.add(value.split("?", 1)[0].lstrip("/"))
        self.assertEqual(remote_references, [])
        self.assertTrue(references)
        for reference in references:
            with self.subTest(asset=reference):
                asset = exact_case_path(PUBLIC, reference)
                self.assertTrue(asset.is_file())
                self.assertGreater(asset.stat().st_size, 0)

    def test_all_committed_models_are_referenced_and_self_contained(self):
        source_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SOURCE.rglob("*") if path.suffix.lower() in {".ts", ".tsx", ".css"}
        )
        models = list((PUBLIC / "models").glob("*.glb"))
        self.assertEqual(len(models), 7)
        for model in models:
            with self.subTest(model=model.name):
                self.assertIn(f"/models/{model.name}", source_text)
                document = glb_json(model)
                external = []
                for collection in ("buffers", "images"):
                    for item in document.get(collection, []):
                        uri = item.get("uri")
                        if uri and not uri.startswith("data:"):
                            external.append(uri)
                for uri in external:
                    exact_case_path(model.parent, uri)

    def test_all_committed_textures_are_referenced_and_licensed(self):
        source_text = "\n".join(path.read_text(encoding="utf-8") for path in SOURCE.rglob("*")
                                if path.suffix.lower() in {".ts", ".tsx", ".css"})
        licenses = (ROOT / "DATA_LICENSES.md").read_text(encoding="utf-8")
        textures = [path for path in (PUBLIC / "textures").rglob("*") if path.is_file()]
        self.assertEqual(len(textures), 3)
        self.assertIn("/textures/dirt/${name}.jpg", source_text)
        self.assertIn("['Diffuse', 'rough', 'nor_gl']", source_text)
        for texture in textures:
            with self.subTest(texture=texture.name):
                self.assertIn(texture.name, licenses)


if __name__ == "__main__":
    unittest.main()
