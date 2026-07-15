from __future__ import annotations
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from .models import FlakeManifest, InstalledFlake


class FlakeInstaller:
    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self.flakes_dir = self.project_root / "flakes"

    def get_installed(self) -> list[InstalledFlake]:
        if not self.flakes_dir.exists():
            return []
        installed = []
        for item in self.flakes_dir.iterdir():
            manifest_path = item / "flake.json"
            if manifest_path.exists():
                data = json.loads(manifest_path.read_text())
                manifest = FlakeManifest(**data)
                installed.append(InstalledFlake(
                    manifest=manifest,
                    install_path=str(item),
                    installed_at=str(item.stat().st_mtime)
                ))
        return installed

    def install(self, manifest: FlakeManifest, source_dir: Path, force: bool = False):
        target = self.flakes_dir / manifest.id.split("/")[-1]
        if target.exists():
            if force:
                shutil.rmtree(target)
            else:
                raise FileExistsError(f"Flake '{manifest.id}' already installed. Use force=True to overwrite.")
        target.mkdir(parents=True, exist_ok=True)
        for item in source_dir.iterdir():
            if item.name == "__pycache__":
                continue
            dest = target / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        manifest_path = target / "flake.json"
        manifest_path.write_text(json.dumps(manifest.model_dump(), indent=2))
        return InstalledFlake(
            manifest=manifest,
            install_path=str(target),
            installed_at=datetime.now().isoformat()
        )

    def remove(self, flake_id: str):
        name = flake_id.split("/")[-1]
        target = self.flakes_dir / name
        if target.exists():
            shutil.rmtree(target)
            return True
        return False
