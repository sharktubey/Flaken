from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from flaken_core.models import FlakeManifest

app = FastAPI(title="Flaken Registry", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FLAKES_DIR = Path(__file__).resolve().parent.parent.parent / "flakes"


def _discover_flakes() -> list[FlakeManifest]:
    manifests = []
    if not FLAKES_DIR.exists():
        return manifests
    for item in FLAKES_DIR.iterdir():
        manifest_path = item / "flake.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text())
            manifests.append(FlakeManifest(**data))
    return manifests


def _find_flake(flake_id: str) -> Optional[FlakeManifest]:
    for f in _discover_flakes():
        if f.id == flake_id:
            return f
    return None


def _find_by_name(name: str) -> Optional[FlakeManifest]:
    for f in _discover_flakes():
        if f.id.split("/")[-1] == name:
            return f
    return None


class PublishRequest(BaseModel):
    manifest: FlakeManifest
    files: dict[str, str]


@app.get("/api/v1/flakes")
async def list_flakes(search: str = "", tag: str = "", framework: str = ""):
    flakes = _discover_flakes()
    if search:
        flakes = [f for f in flakes if search.lower() in f.name.lower() or search.lower() in f.description.lower()]
    if tag:
        flakes = [f for f in flakes if tag.lower() in [t.lower() for t in f.tags]]
    if framework:
        flakes = [f for f in flakes if f.framework == framework]
    return {"count": len(flakes), "flakes": [f.model_dump() for f in flakes]}


@app.get("/api/v1/flakes/{name}")
async def get_flake(name: str):
    flake = _find_by_name(name)
    if not flake:
        raise HTTPException(status_code=404, detail=f"Flake '{name}' not found")
    return flake.model_dump()


@app.get("/api/v1/flakes/{name}/download")
async def download_flake(name: str):
    flake = _find_by_name(name)
    if not flake:
        raise HTTPException(status_code=404, detail=f"Flake '{name}' not found")
    flake_dir = FLAKES_DIR / name
    files: dict[str, str] = {}
    for item in flake_dir.rglob("*"):
        if item.is_file() and item.name != "flake.json" and "__pycache__" not in item.parts:
            rel = item.relative_to(flake_dir)
            files[str(rel)] = item.read_text(encoding="utf-8")
    return {"manifest": flake.model_dump(), "files": files}


@app.post("/api/v1/flakes")
async def publish_flake(req: PublishRequest):
    name = req.manifest.id.split("/")[-1]
    flake_dir = FLAKES_DIR / name
    flake_dir.mkdir(parents=True, exist_ok=True)
    (flake_dir / "flake.json").write_text(json.dumps(req.manifest.model_dump(), indent=2))
    for filename, content in req.files.items():
        file_path = flake_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    return {"status": "published", "id": req.manifest.id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
