#!/usr/bin/env python3
"""Generate validation answers for a base, SFT or DPO config into <output_dir>/predictions.json."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, generation, predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = config.load_config(args.config)

    out = config.prepare_output_dir(cfg)
    setup = config.model_setup(cfg)
    rows = generation.run_generation(setup, cfg["seed"])
    # Models are named by their run directory, e.g. "sft/1b".
    model = Path(cfg["output_dir"]).relative_to("experiments").as_posix()
    predictions.save_predictions(out / "predictions.json", model, setup, rows, cfg["seed"])


if __name__ == "__main__":
    main()
