"""Load the processing parameters from a TOML file (default: config/default.toml)."""
from pathlib import Path
import tomllib

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "default.toml"


def load_config(path=None):
    """Return the configuration as a dict. `path=None` loads config/default.toml."""
    with open(path or DEFAULT_CONFIG, "rb") as fh:
        return tomllib.load(fh)
