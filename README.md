# Flaken

Drop a flake into your code. Build complex Discord interactions in seconds.

```bash
pip install flaken
flaken init
flaken add flaken/leveling
```

```python
from flakes.leveling import LevelingSystem
await bot.add_cog(LevelingSystem(bot))
```

## Commands

- `flaken init` — Initialize a project
- `flaken search <query>` — Search the registry
- `flaken add <flake>` — Install a flake (use `--style prefix` for prefix-only commands)
- `flaken list` — List installed flakes
- `flaken remove <flake>` — Remove a flake
- `flaken info <flake>` — Show flake details
- `flaken update` — Update all installed flakes to the latest version

## Documentation

https://flaken.xyz

## Badges

[![PyPI version](https://img.shields.io/pypi/v/flaken)](https://pypi.org/project/flaken/)
[![Python version](https://img.shields.io/pypi/pyversions/flaken)](https://pypi.org/project/flaken/)
[![License](https://img.shields.io/pypi/l/flaken)](https://github.com/sharktubey/Flaken/blob/master/LICENSE)
