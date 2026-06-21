"""Shared config and environment loading for all modules."""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

def load_config() -> dict:
    with open(ROOT / "config" / "config.yaml", "r") as f:
        return yaml.safe_load(f)

def env(key: str, default=None):
    val = os.getenv(key, default)
    if val is None:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val
