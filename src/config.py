from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "config.yaml"

def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)