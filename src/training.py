from __future__ import annotations

from . import config, dataset as ds_mod, conversation


def load_tokenizer(name: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(name, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def load_base_model(model: dict, *, for_training: bool = True):
    import torch
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig

    kwargs = dict(dtype=torch.bfloat16, device_map="auto", attn_implementation="eager")
    if model["quantization"] == "4bit":
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_storage=torch.bfloat16,
        )

    base = AutoModelForCausalLM.from_pretrained(model["weights"], **kwargs)
    if for_training:
        base.config.use_cache = False
    return base


def _prepare_datasets(system_prompt: str):
    train, val = ds_mod.load_split()

    # In prompt-completion form TRL applies the chat template and computes the loss on the answer only.
    def to_prompt_completion(example):
        return {"prompt": conversation.with_system(example["input"], system_prompt),
                "completion": [example["output"]]}

    return (train.map(to_prompt_completion, remove_columns=train.column_names),
            val.map(to_prompt_completion, remove_columns=val.column_names))


def train(cfg: dict) -> None:
    from peft import LoraConfig
    from transformers import set_seed
    from transformers.trainer_utils import get_last_checkpoint
    from trl import SFTConfig, SFTTrainer

    out = config.prepare_output_dir(cfg)
    setup = config.model_setup(cfg)
    set_seed(cfg["seed"])
    tokenizer = load_tokenizer(setup["model"]["tokenizer"])
    train_data, val_data = _prepare_datasets(setup["system_prompt"])
    trainer = SFTTrainer(
        model=load_base_model(setup["model"]),
        args=SFTConfig(**cfg["training"], seed=cfg["seed"], output_dir=str(out)),
        train_dataset=train_data,
        eval_dataset=val_data,
        peft_config=LoraConfig(**cfg["lora"], bias="none", task_type="CAUSAL_LM", target_modules="all-linear"),
        processing_class=tokenizer,
    )
    trainer.train(resume_from_checkpoint=get_last_checkpoint(str(out)))
    trainer.save_model()
    tokenizer.save_pretrained(str(out))
    print("Saved to:", out)
