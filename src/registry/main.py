from __future__ import annotations
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from flake_schema import FlakeManifest

app = FastAPI(title="Flaken Registry API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FLAKES_DIR = Path(__file__).resolve().parent / "flakes"


def _discover_flakes() -> list[FlakeManifest]:
    manifests = []
    if not FLAKES_DIR.exists():
        return manifests
    for item in sorted(FLAKES_DIR.iterdir()):
        manifest_path = item / "flake.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifests.append(FlakeManifest(**data))
    return manifests


def _find_by_name(name: str) -> Optional[FlakeManifest]:
    for f in _discover_flakes():
        if f.id.split("/")[-1] == name:
            return f
    return None


def _apply_style(content: str, style: str) -> str:
    if style == "prefix":
        return content.replace("hybrid_command", "command")
    return content


class PublishRequest(BaseModel):
    manifest: FlakeManifest
    files: dict[str, str]


class FlakeSelection(BaseModel):
    name: str
    style: str = "hybrid"
    config: dict[str, object] = {}


class GenerateRequest(BaseModel):
    prefix: str = "!"
    flakes: list[FlakeSelection] = []


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
    (flake_dir / "flake.json").write_text(json.dumps(req.manifest.model_dump(), indent=2), encoding="utf-8")
    for filename, content in req.files.items():
        file_path = flake_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    return {"status": "published", "id": req.manifest.id}


@app.post("/api/v1/generate")
async def generate_bot(req: GenerateRequest):
    if not req.flakes:
        raise HTTPException(status_code=400, detail="At least one flake is required.")

    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        imports = []
        add_cogs = []
        all_pip_deps = set()
        prefix = req.prefix

        for selection in req.flakes:
            manifest = _find_by_name(selection.name)
            if not manifest:
                raise HTTPException(status_code=404, detail=f"Flake '{selection.name}' not found.")

            name = manifest.id.split("/")[-1]
            style = selection.style
            flake_dir = FLAKES_DIR / name

            imports.append(f"from flakes.{name} import {', '.join(manifest.exports)}")

            config_args = ""
            if selection.config:
                parts = []
                for k, v in selection.config.items():
                    if isinstance(v, str):
                        parts.append(f'    {k}="{v}"')
                    elif isinstance(v, bool):
                        parts.append(f"    {k}={str(v)}")
                    else:
                        parts.append(f"    {k}={v}")
                config_args = ",\n    ".join(parts)

            if config_args:
                add_cogs.append(f"    await bot.add_cog({manifest.exports[0]}(bot,\n        {config_args},\n    ))")
            else:
                add_cogs.append(f"    await bot.add_cog({manifest.exports[0]}(bot))")

            for dep in manifest.dependencies.pip:
                all_pip_deps.add(dep)

            for item in flake_dir.rglob("*"):
                if item.is_file() and item.name != "flake.json" and "__pycache__" not in item.parts:
                    rel = item.relative_to(flake_dir)
                    content = item.read_text(encoding="utf-8")
                    content = _apply_style(content, style)
                    zf.writestr(f"flakes/{name}/{rel}", content)

        bot_py = f"""import os
import discord
from discord.ext import commands

{chr(10).join(imports)}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="{prefix}", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {{bot.user}}", flush=True)
{chr(10).join(add_cogs)}
    await bot.tree.sync()
    print("Bot ready!", flush=True)


token = os.environ.get("DISCORD_BOT_TOKEN")
if not token:
    print("ERROR: Set DISCORD_BOT_TOKEN environment variable")
    exit(1)

bot.run(token)
"""
        zf.writestr("bot.py", bot_py)

        pip_deps = "\n".join(sorted(all_pip_deps)) if all_pip_deps else "# No extra dependencies"
        zf.writestr("requirements.txt", f"discord.py>=2.0.0\n{pip_deps}")

        readme = f"""# Flaken Bot

Generated with Flaken (https://flaken.xyz)

## Setup

1. Create a bot at https://discord.com/developers/applications
2. Copy your bot token
3. Enable Message Content Intent and Server Members Intent under the Bot page
4. Run the bot:

   set DISCORD_BOT_TOKEN=your_token_here
   pip install -r requirements.txt
   python bot.py

## Hosting (free)

- Render: https://api.flaken.xyz/health
- Railway: https://railway.app
- Fly.io: https://fly.io

## Included flakes

{chr(10).join(f'- {f.name} ({f.style})' for f in req.flakes)}
"""
        zf.writestr("README.txt", readme)

    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=flaken-bot.zip"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "flakes": len(_discover_flakes())}
