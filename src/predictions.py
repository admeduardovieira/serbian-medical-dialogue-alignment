from __future__ import annotations

from pathlib import Path

from .artifacts import save_json_atomic, utc_timestamp


def save_predictions(path: Path, model: str, setup: dict, rows: list[dict], seed: int) -> None:
    payload = {
        "created_at": utc_timestamp(),
        "model": model,
        "weights": setup["model"]["weights"],
        "adapter": str(setup["adapter"]) if setup["adapter"] else None,
        "seed": seed,
        "num_samples": len(rows),
        "predictions": rows,
    }
    save_json_atomic(payload, path)
    print("Saved to:", path)


def pred_ref_lists(rows: list[dict]) -> tuple[list[str], list[str], list[int]]:
    """Return predictions, references and row indices, excluding missing predictions and empty references."""
    predictions, references, valid_idx = [], [], []
    for i, row in enumerate(rows):
        pred = row.get("prediction")
        ref = row.get("ground_truth")
        if pred is None:
            continue
        if ref is None or str(ref).strip() == "":
            continue
        predictions.append(str(pred).strip())
        references.append(str(ref).strip())
        valid_idx.append(i)
    return predictions, references, valid_idx
