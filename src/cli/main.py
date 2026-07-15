from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

import click
import httpx

from flaken_core.models import FlakeManifest, RegistryConfig
from flaken_core.installer import FlakeInstaller

DEFAULT_REGISTRY = "https://flaken-api.onrender.com"
CONFIG_FILE = "flaken.json"

STYLE_ALIASES = {
    "hb": "hybrid", "hybrid": "hybrid",
    "p": "prefix", "pre": "prefix", "prefix": "prefix",
    "ac": "appcmd", "app": "appcmd", "appcmd": "appcmd",
}


def _apply_style(content: str, style: str) -> str:
    if style == "prefix":
        return content.replace("hybrid_command", "command")
    return content


def _load_config(project_root: Path) -> RegistryConfig:
    config_path = project_root / CONFIG_FILE
    if config_path.exists():
        return RegistryConfig(**json.loads(config_path.read_text()))
    return RegistryConfig()


def _save_config(project_root: Path, config: RegistryConfig):
    (project_root / CONFIG_FILE).write_text(json.dumps({"registry_url": config.registry_url}, indent=2))


def _get_registry_url(project_root: Path) -> str:
    return _load_config(project_root).registry_url or DEFAULT_REGISTRY


@click.group()
def cli():
    """Flaken — drop a flake into your code."""


@cli.command()
@click.option("--registry", default=DEFAULT_REGISTRY, help="Registry URL")
@click.pass_context
def init(ctx: click.Context, registry: str):
    """Initialize flaken in the current project."""
    project_root = Path.cwd()
    config_path = project_root / CONFIG_FILE
    if config_path.exists():
        click.echo("[!]️  flaken.json already exists. Use --registry to update.")
        return
    cfg = RegistryConfig(registry_url=registry)
    _save_config(project_root, cfg)
    flakes_dir = project_root / "flakes"
    flakes_dir.mkdir(exist_ok=True)
    (flakes_dir / ".gitkeep").touch()
    click.echo(f"[OK] Initialized flaken (registry: {registry})")
    click.echo(f"   Flakes will be installed to: {flakes_dir}/")


@cli.command()
@click.argument("query")
def search(query: str):
    """Search for flakes in the registry."""
    registry = _get_registry_url(Path.cwd())
    try:
        resp = httpx.get(f"{registry}/api/v1/flakes", params={"search": query}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        click.echo(f"[X] Failed to reach registry at {registry}: {e}")
        return
    if data["count"] == 0:
        click.echo(f"No flakes found for '{query}'.")
        return
    click.echo(f"Found {data['count']} flake(s):\n")
    for flake in data["flakes"]:
        tags = ", ".join(flake.get("tags", [])[:3])
        style_badge = f"[{flake.get('command_style', 'hybrid')}]"
        click.echo(f"  {flake['id']:30s} {flake['name']:25s} {style_badge}")
        click.echo(f"  {'':30s} {flake['description']}")
        if tags:
            click.echo(f"  {'':30s} tags: {tags}")
        click.echo()


@cli.command()
@click.argument("flake_id")
@click.option("--force", is_flag=True, help="Overwrite if already installed")
@click.option("--style", "-s", default="hybrid",
              type=click.Choice(["hybrid", "prefix", "appcmd"]),
              help="Command style: hybrid | prefix | appcmd")
def add(flake_id: str, force: bool, style: str):
    """Install a flake from the registry."""
    project_root = Path.cwd()
    registry = _get_registry_url(project_root)
    name = flake_id.split("/")[-1]
    try:
        resp = httpx.get(f"{registry}/api/v1/flakes/{name}/download", timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        click.echo(f"[X] Failed to fetch flake '{flake_id}' from {registry}: {e}")
        return
    manifest = FlakeManifest(**data["manifest"])
    installer = FlakeInstaller(project_root)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        files = data.get("files", {})
        for filename, content in files.items():
            if filename.endswith(".py"):
                content = _apply_style(content, style)
            file_path = tmp_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        flake_src = tmp_path / manifest.entry
        try:
            installed = installer.install(manifest, tmp_path, force=force)
            click.echo(f"[OK] Installed flake: {manifest.name} v{manifest.version} [{style}]")
            click.echo(f"   Location: {installed.install_path}")
            if manifest.exports:
                click.echo(f"   Import: from flakes.{manifest.id.split('/')[-1]} import {', '.join(manifest.exports)}")
            if manifest.dependencies.pip:
                deps = " ".join(manifest.dependencies.pip)
                click.echo(f"   Dependencies: pip install {deps}")
        except FileExistsError:
            click.echo(f"[!] Flake '{flake_id}' already installed. Use --force to overwrite.")


@cli.command()
@click.argument("flake_id")
def remove(flake_id: str):
    """Remove an installed flake."""
    installer = FlakeInstaller(Path.cwd())
    if installer.remove(flake_id):
        click.echo(f"[OK] Removed flake: {flake_id}")
    else:
        click.echo(f"[!] Flake '{flake_id}' not found.")


@cli.command()
def list():
    """List installed flakes."""
    installer = FlakeInstaller(Path.cwd())
    installed = installer.get_installed()
    if not installed:
        click.echo("No flakes installed.")
        click.echo("  Try: flaken search leveling")
        click.echo("  Then: flaken add flaken/leveling")
        return
    click.echo(f"Installed flakes ({len(installed)}):\n")
    for flake in installed:
        m = flake.manifest
        click.echo(f"  {m.id:30s} {m.name} v{m.version}")
        click.echo(f"  {'':30s} {m.description[:60]}")
        click.echo()


@cli.command()
@click.argument("flake_id")
def info(flake_id: str):
    """Show detailed info about a flake."""
    project_root = Path.cwd()
    # Check local first
    installer = FlakeInstaller(project_root)
    local = [f for f in installer.get_installed() if f.manifest.id == flake_id]
    if local:
        m = local[0].manifest
        click.echo(f"[PACKAGE] {m.name} v{m.version}")
        click.echo(f"   ID: {m.id}")
        click.echo(f"   Author: {m.author}")
        click.echo(f"   License: {m.license}")
        click.echo(f"   Framework: {m.framework}")
        click.echo(f"   Command Style: {m.command_style}")
        click.echo(f"   Description: {m.description}")
        click.echo(f"   Tags: {', '.join(m.tags)}")
        click.echo(f"   Dependencies: {', '.join(m.dependencies.pip) or 'none'}")
        click.echo(f"   Exports: {', '.join(m.exports)}")
        return
    # Check registry
    registry = _get_registry_url(project_root)
    name = flake_id.split("/")[-1]
    try:
        resp = httpx.get(f"{registry}/api/v1/flakes/{name}", timeout=10)
        resp.raise_for_status()
        m = FlakeManifest(**resp.json())
    except Exception:
        click.echo(f"[X] Flake '{flake_id}' not found locally or in registry.")
        return
    click.echo(f"[PACKAGE] {m.name} v{m.version}")
    click.echo(f"   ID: {m.id}")
    click.echo(f"   Author: {m.author}")
    click.echo(f"   License: {m.license}")
    click.echo(f"   Framework: {m.framework}")
    click.echo(f"   Command Style: {m.command_style}")
    click.echo(f"   Description: {m.description}")
    click.echo(f"   Tags: {', '.join(m.tags)}")
    click.echo(f"   Dependencies: {', '.join(m.dependencies.pip) or 'none'}")
    click.echo(f"   Exports: {', '.join(m.exports)}")


if __name__ == "__main__":
    cli()
