#!/usr/bin/env python3
"""Train DPO from an SFT run, configured by configs/dpo/<name>.yaml."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, dpo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    dpo.train_dpo(config.load_config(args.config))
