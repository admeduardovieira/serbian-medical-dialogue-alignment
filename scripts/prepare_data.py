#!/usr/bin/env python3
"""Convert JSON transcripts to a Hugging Face dataset and save one split by call_id."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, dataset
from src.artifacts import save_json_atomic


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default=str(config.RAW_DATA_DIR), help='Transcript directory.')
    parser.add_argument("--seed", type=int, default=42, help="Seed for the call_id split.")
    parser.add_argument("--train-fraction", type=float, default=0.85)
    args = parser.parse_args()

    examples = dataset.build_hf_dataset(raw_dir=args.raw, out_dir=config.DATASET_DIR)
    split = dataset.split_call_ids(examples["call_id"], seed=args.seed, train_fraction=args.train_fraction)
    save_json_atomic(split, config.SPLIT_PATH)
    print(f"Split: {len(split['train'])} train and {len(split['validation'])} validation calls -> {config.SPLIT_PATH}")


if __name__ == "__main__":
    main()
