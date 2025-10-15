from pathlib import Path
import yaml, csv

def ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def load_yaml(path: str, default: dict = None):
    p = Path(path)
    if not p.exists():
        return default or {}
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_yaml(path: str, data: dict):
    p = Path(path)
    ensure_parent(p)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

def append_csv(path: str, header: list, row: list):
    p = Path(path)
    ensure_parent(p)
    write_header = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(header)
        w.writerow(row)

def tail_csv_as_dicts(path: str, n: int = 50):
    p = Path(path)
    if not p.exists(): return []
    lines = p.read_text(encoding="utf-8").splitlines()
    if not lines: return []
    header = lines[0].split(",")
    out = []
    for line in lines[-min(len(lines)-1, n):]:
        if line == lines[0]:  # skip header
            continue
        vals = line.split(",")
        out.append(dict(zip(header, vals)))
    return out

