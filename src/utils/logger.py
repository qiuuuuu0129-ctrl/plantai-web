# src/utils/logger.py
import logging, sys, os
from pathlib import Path

def build_logger(name, to_file=None, level=logging.INFO):
    logger = logging.getLogger(name)
    if logger.handlers: return logger
    logger.setLevel(level)
    fmt = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
    sh = logging.StreamHandler(sys.stdout); sh.setFormatter(fmt); logger.addHandler(sh)
    if to_file:
        Path(to_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(to_file, encoding="utf-8"); fh.setFormatter(fmt); logger.addHandler(fh)
    return logger
