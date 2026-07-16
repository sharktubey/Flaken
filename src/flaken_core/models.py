from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class FlakeDependency(BaseModel):
    pip: list[str] = []
    flakes: list[str] = []


class FlakeConfigProperty(BaseModel):
    type: str = "string"
    default: object = None
    description: str = ""


class FlakeConfig(BaseModel):
    properties: dict[str, FlakeConfigProperty] = {}


class FlakeManifest(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "Flaken"
    license: str = "MIT"
    language: str = "python"
    framework: str = "discord.py"
    min_framework_version: str = "2.0.0"
    command_style: str = "hybrid"
    entry: str = "cog.py"
    exports: list[str] = []
    dependencies: FlakeDependency = FlakeDependency()
    config: FlakeConfig = FlakeConfig()
    tags: list[str] = []
    created_at: str = ""
    updated_at: str = ""


class InstalledFlake(BaseModel):
    manifest: FlakeManifest
    install_path: str
    installed_at: str = "unknown"


class RegistryConfig(BaseModel):
    registry_url: str = "https://flaken-api.onrender.com"
    flakes_dir: str = "flakes"
    auto_install_deps: bool = True
