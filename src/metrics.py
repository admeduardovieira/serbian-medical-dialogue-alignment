from __future__ import annotations

from . import config, predictions as pred_mod

_METRIC_CACHE: dict = {}
_EMBEDDING_CACHE: dict = {}


def _get_metric(name: str):
    if name not in _METRIC_CACHE:
        import evaluate
        _METRIC_CACHE[name] = evaluate.load(name)
    return _METRIC_CACHE[name]


def compute_rouge_bleu(predictions: list[str], references: list[str]) -> dict:
    if not any(predictions):
        return dict.fromkeys(("rouge1", "rouge2", "rougeL", "bleu"), 0.0)
    rouge = _get_metric("rouge")
    bleu = _get_metric("bleu")

    rouge_out = rouge.compute(predictions=predictions, references=references)
    bleu_out = bleu.compute(predictions=predictions, references=[[r] for r in references])

    return {
        "rouge1": float(rouge_out["rouge1"]),
        "rouge2": float(rouge_out["rouge2"]),
        "rougeL": float(rouge_out["rougeL"]),
        "bleu": float(bleu_out["bleu"]),
    }


def compute_bertscore(predictions: list[str], references: list[str], settings: dict) -> dict[str, list[float]]:
    bertscore = _get_metric("bertscore")
    out = bertscore.compute(
        predictions=predictions,
        references=references,
        **settings,
    )
    return {
        "precision": [float(x) for x in out["precision"]],
        "recall": [float(x) for x in out["recall"]],
        "f1": [float(x) for x in out["f1"]],
    }


def text_lengths(text: str) -> tuple[int, int]:
    """Return character and whitespace-delimited word counts."""
    text = text or ""
    return len(text), len(text.split())


class EmbeddingScorer:

    def __init__(self, spec: config.EmbeddingSpec) -> None:
        import torch
        from transformers import AutoTokenizer, AutoModel

        self.spec = spec
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(spec.model_name)
        self.model = AutoModel.from_pretrained(spec.model_name).to(self.device)
        self.model.eval()

    @staticmethod
    def _mean_pool(last_hidden_states, attention_mask):
        masked = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
        return masked.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

    def _pool(self, outputs, attention_mask):
        if self.spec.pooling != "mean":
            raise ValueError(f"Unknown pooling '{self.spec.pooling}' for '{self.spec.key}'.")
        return self._mean_pool(outputs.last_hidden_state, attention_mask)

    def encode(self, texts: list[str]):
        """Return L2-normalized embeddings as a NumPy array."""
        import torch
        import torch.nn.functional as F

        embeddings = []
        with torch.no_grad():
            for start in range(0, len(texts), self.spec.batch_size):
                batch = [f"{self.spec.prefix}{t}" for t in texts[start:start + self.spec.batch_size]]
                enc = self.tokenizer(
                    batch,
                    max_length=self.spec.max_length,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                ).to(self.device)
                out = self.model(**enc)
                emb = self._pool(out, enc["attention_mask"])
                emb = F.normalize(emb, p=2, dim=1)
                embeddings.append(emb.cpu())
        return torch.cat(embeddings, dim=0).numpy()

    def cosine(self, predictions: list[str], references: list[str]) -> list[float]:
        import numpy as np

        pred_emb = self.encode(predictions)
        ref_emb = self.encode(references)
        return [float(x) for x in np.sum(pred_emb * ref_emb, axis=1)]


def get_embedding_scorer(key: str, settings: dict) -> EmbeddingScorer:
    import json

    cache_key = json.dumps([key, settings], sort_keys=True)
    if cache_key not in _EMBEDDING_CACHE:
        _EMBEDDING_CACHE[cache_key] = EmbeddingScorer(config.EmbeddingSpec(key=key, **settings))
    return _EMBEDDING_CACHE[cache_key]


def evaluate_prediction_rows(rows: list[dict], reference: dict) -> dict:
    """Score available answers; report missing predictions and empty answers separately."""
    import numpy as np

    include_bertscore = reference["bertscore"] is not None
    embedding_keys = reference["embeddings"] or {}

    for row in rows:
        chars, words = text_lengths(str(row.get("prediction") or ""))
        row["pred_len_chars"] = chars
        row["pred_len_words"] = words

    predictions, references, valid_idx = pred_mod.pred_ref_lists(rows)

    nonempty = [i for i, text in enumerate(predictions) if text]
    nonempty_predictions = [predictions[i] for i in nonempty]
    nonempty_references = [references[i] for i in nonempty]
    fields = ["bertscore_precision", "bertscore_recall", "bertscore_f1"] if include_bertscore else []
    fields += [f"{key}_cosine" for key in embedding_keys]
    for row in rows:
        for field in fields:
            row[field] = None

    summary: dict = {
        "expected": len(rows),
        "missing_predictions": sum(row.get("prediction") is None for row in rows),
        "empty_predictions": sum(row.get("prediction") is not None and not str(row["prediction"]).strip() for row in rows),
        "scored": len(valid_idx),
        "pred_len_chars_mean": float(np.mean([r["pred_len_chars"] for r in rows])) if rows else 0.0,
        "pred_len_words_mean": float(np.mean([r["pred_len_words"] for r in rows])) if rows else 0.0,
    }
    for key in embedding_keys:
        summary[f"{key}_cosine_mean"] = None
        summary[f"{key}_cosine_n"] = 0
    if not predictions:
        return summary

    if reference["rouge_bleu"]:
        summary.update(compute_rouge_bleu(predictions, references))

    if include_bertscore:
        bs = {name: [0.0] * len(predictions) for name in ("precision", "recall", "f1")}
        if nonempty:
            computed = compute_bertscore(nonempty_predictions, nonempty_references, reference["bertscore"])
            for name, values in computed.items():
                for i, value in zip(nonempty, values):
                    bs[name][i] = value
        for local_i, row_i in enumerate(valid_idx):
            rows[row_i]["bertscore_precision"] = bs["precision"][local_i]
            rows[row_i]["bertscore_recall"] = bs["recall"][local_i]
            rows[row_i]["bertscore_f1"] = bs["f1"][local_i]
        summary["bertscore_precision_mean"] = float(np.mean(bs["precision"]))
        summary["bertscore_recall_mean"] = float(np.mean(bs["recall"]))
        summary["bertscore_f1_mean"] = float(np.mean(bs["f1"]))

    for key in embedding_keys:
        field = f"{key}_cosine"
        cos = get_embedding_scorer(key, embedding_keys[key]).cosine(nonempty_predictions, nonempty_references) if nonempty else []
        for local_i, value in zip(nonempty, cos):
            rows[valid_idx[local_i]][field] = value
        summary[f"{field}_mean"] = float(np.mean(cos)) if cos else None
        summary[f"{field}_n"] = len(cos)

    return summary
