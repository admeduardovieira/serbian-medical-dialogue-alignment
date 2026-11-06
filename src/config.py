from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import judge

REPO_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = REPO_ROOT / "dataset" / "json_ser"
DATASET_DIR = REPO_ROOT / "dataset" / "hf_ser"
SPLIT_PATH = REPO_ROOT / "dataset" / "split.json"


@dataclass(frozen=True)
class EmbeddingSpec:
    key: str  # Result field prefix, e.g. e5_cosine.
    model_name: str
    pooling: str = "mean"
    prefix: str = ""  # Prepended before encoding each text.
    max_length: int = 512
    batch_size: int = 32


def load_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def prepare_output_dir(cfg: dict) -> Path:
    """Keep the config, its prompts and SFT adapter hash next to the run; refuse to mix runs whose inputs differ."""
    out = REPO_ROOT / cfg["output_dir"]
    saved = out / "config.yaml"
    if saved.exists() and load_config(saved) != cfg:
        raise ValueError(f"{out} was created with a different config; use a new output_dir")
    out.mkdir(parents=True, exist_ok=True)
    saved.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    prompts = {"system_prompt.md": cfg["system_prompt"]} if "system_prompt" in cfg else {}
    if cfg.get("judge"):
        rubric_dir = cfg["judge"]["rubric_prompts"]
        prompts.update({f"judge/{r.prompt_filename}": f"{rubric_dir}/{r.prompt_filename}" for r in judge.RUBRICS})
        if "pairwise_prompt" in cfg["judge"]:
            prompts["judge/pairwise.md"] = cfg["judge"]["pairwise_prompt"]
    copies = {name: (source, (REPO_ROOT / source).read_text(encoding="utf-8").strip())
              for name, source in prompts.items()}
    if "sft_dir" in cfg:
        # The SFT run can be retrained under the same path, so record the adapter itself.
        adapter = f"{cfg['sft_dir']}/adapter_model.safetensors"
        copies["sft_adapter.sha256"] = (adapter, hashlib.sha256((REPO_ROOT / adapter).read_bytes()).hexdigest())
    for name, (source, content) in copies.items():
        copy = out / name
        if copy.exists() and copy.read_text(encoding="utf-8") != content:
            raise ValueError(f"{source} changed since {out} was created; use a new output_dir")
        copy.parent.mkdir(exist_ok=True)
        copy.write_text(content, encoding="utf-8")
    return out


def model_setup(cfg: dict) -> dict:
    """Model, assistant prompt, decoding and adapter for a base, SFT or DPO config."""
    out = REPO_ROOT / cfg["output_dir"]
    if "sft_dir" in cfg:  # DPO continues the SFT run: same model, prompt and decoding.
        sft_dir = REPO_ROOT / cfg["sft_dir"]
        sft = load_config(sft_dir / "config.yaml")
        return {"model": sft["model"], "generation": sft["generation"], "adapter": out,
                "system_prompt": (sft_dir / "system_prompt.md").read_text(encoding="utf-8")}
    return {"model": cfg["model"], "generation": cfg["generation"],
            "adapter": out if "lora" in cfg else None,
            "system_prompt": (out / "system_prompt.md").read_text(encoding="utf-8")}
