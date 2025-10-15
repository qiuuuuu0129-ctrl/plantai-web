# src/utils/hwcfg.py
from pathlib import Path
import yaml

_CFG_CACHE = None

def _load():
    global _CFG_CACHE
    if _CFG_CACHE is not None: return _CFG_CACHE
    f = Path("configs/plantai_config.yaml")
    _CFG_CACHE = yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}
    return _CFG_CACHE

def cfg_get(path, default=None):
    cfg = _load()
    cur = cfg
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur: return default
        cur = cur[p]
    return cur
