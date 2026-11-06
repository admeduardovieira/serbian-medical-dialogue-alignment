from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import HTML


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.judge import RUBRICS, normalize_label, LABELS_ORDERED, LABEL_SCORE

FIG_DIR = REPO_ROOT / "notebooks" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.dpi"] = 150

# Output of scripts/judge.py over all models of the main experiment (see run.sh).
EVALUATIONS_PATH = REPO_ROOT / "experiments" / "eval" / "evaluations.json"


def load_items(path: Path | None = None) -> list[dict]:
    source = Path(path) if path is not None else EVALUATIONS_PATH
    return json.loads(source.read_text(encoding="utf-8"))


GT = "ground_truth"
MODEL_LABELS = {
    GT: "Reference response",
    "base/1b": "1B IT baseline",
    "base/12b": "12B IT baseline",
    "base/27b": "27B IT baseline",
    "sft/1b": "1B IT → SFT",
    "dpo/1b": "1B IT → SFT → DPO",
    "sft/12b-pt": "12B PT → SFT",
    "dpo/12b-pt": "12B PT → SFT → DPO",
    "sft/12b-it": "12B IT → SFT",
    "dpo/12b-it": "12B IT → SFT → DPO",
}


def model_label(name: str) -> str:
    return MODEL_LABELS.get(name, name)


BASELINE = ["base/1b", "base/12b", "base/27b"]
SFT = ["sft/1b", "sft/12b-pt", "sft/12b-it"]
DPO = ["dpo/1b", "dpo/12b-pt", "dpo/12b-it"]
SIZE_GROUPS = {
    "1b": [BASELINE[0], SFT[0], DPO[0]],
    "12b": [BASELINE[1], SFT[1], DPO[1]],
    "12b_it": [BASELINE[1], SFT[2], DPO[2]],
}
ALL_ORDER = SIZE_GROUPS["1b"] + SIZE_GROUPS["12b"] + [SFT[2], DPO[2], BASELINE[2]]

SEM_METRICS = ["bertscore_f1"]
LEX_METRICS = ["rougeL", "bleu"]
METRIC_LABELS = {
    "rouge1": "ROUGE-1", "rouge2": "ROUGE-2", "rougeL": "ROUGE-L", "bleu": "BLEU",
    "bertscore_precision": "BERTScore P", "bertscore_recall": "BERTScore R",
    "bertscore_f1": "BERTScore F1", "e5_cosine": "E5 cosine",
    "modernbertic_cosine": "ModernBERTić cosine",
    "pred_len_chars": "Length (characters)", "pred_len_words": "Length (words)",
}

RUBRIC_ORDER = [r.key for r in RUBRICS]
RUBRIC_LABELS = {
    "bezbednost_i_pridrzavanje_uloge": "Safety and role adherence",
    "klinicka_korisnost_za_prosledjivanje": "Clinical usefulness for handoff",
    "uskladjenost_sa_kontekstom_i_fazom_razgovora": "Contextual relevance",
    "jasnoca_i_ekonomicnost_komunikacije": "Clarity and conciseness",
}

LABEL_DISPLAY = {
    "nezadovoljavajuce": "Poor",
    "zadovoljavajuce": "Adequate",
    "veoma_dobro": "Good",
}
LABEL_COLORS = {
    "nezadovoljavajuce": "#d62728",
    "zadovoljavajuce": "#ff7f0e",
    "veoma_dobro": "#2ca02c",
}


def present_models(items) -> list[str]:
    present = {m for it in items for m in it["predictions"]}
    order = [s for s in ALL_ORDER if s in present]
    order += sorted(present - set(order))
    return order


def build_df_metrics(items) -> pd.DataFrame:
    rows = []
    for it in items:
        cid, tid = it["call_id"], it["turn_id"]
        for slug in it["predictions"]:
            ev = it["evaluations"].get(slug, {})
            row = {"call_id": cid, "turn_id": tid, "model": slug}
            for k, v in ev.items():
                if k != "rubrics" and isinstance(v, (int, float)):
                    row[k] = v
            rows.append(row)
    df = pd.DataFrame(rows)
    order = present_models(items)
    df["model"] = pd.Categorical(df["model"], categories=order, ordered=True)
    return df


def build_df_rubrics(items) -> pd.DataFrame:
    rows = []
    for it in items:
        cid, tid = it["call_id"], it["turn_id"]
        for target, ev in it["evaluations"].items():
            for rkey, r in (ev.get("rubrics") or {}).items():
                lab = normalize_label(r.get("label"))
                rows.append({"call_id": cid, "turn_id": tid,
                             "model": target, "rubric": rkey,
                             "label": lab, "score": LABEL_SCORE.get(lab, np.nan)})
    df = pd.DataFrame(rows)
    order = present_models(items) + ([GT] if (df["model"] == GT).any() else [])
    df["model"] = pd.Categorical(df["model"], categories=order, ordered=True)
    df["label"] = pd.Categorical(df["label"], categories=LABELS_ORDERED, ordered=True)
    return df


def find_item(items, call_id, turn_id=None) -> dict:
    cands = [it for it in items
             if it["call_id"] == call_id and (turn_id is None or it["turn_id"] == turn_id)]
    if not cands:
        raise KeyError(f"No example with call_id={call_id!r} turn_id={turn_id}")
    return cands[0]


def _esc(s) -> str:
    return html.escape(str(s if s is not None else "")).replace("\n", "<br>")


def rubric_chip(raw) -> str:
    lab = normalize_label(raw)
    color = LABEL_COLORS.get(lab, "#adb5bd")
    disp = LABEL_DISPLAY.get(lab, "—" if not raw else str(raw))
    return (f'<span style="background:{color};color:#fff;padding:1px 8px;'
            f'border-radius:10px;font-size:11px;white-space:nowrap">{html.escape(disp)}</span>')


_ROLE_TAGS = {
    "system": ("SYSTEM", "#adb5bd"),
    "user": ("PARENT", "#6b7280"),
    "assistant": ("ASSISTANT", "#1864ab"),
}


def render_conversation(input_messages, highlight_last_user=True) -> str:
    last_user = max((i for i, m in enumerate(input_messages) if m.get("role") == "user"),
                    default=-1)
    rows = []
    for i, m in enumerate(input_messages):
        role = m.get("role")
        tag, color = _ROLE_TAGS.get(role, (str(role).upper(), "#6b7280"))
        content = m.get("content") or ""
        if role == "system":
            short = content if len(content) <= 140 else content[:140].rstrip() + "…"
            rows.append(
                f'<div style="color:#adb5bd;font-size:11px;font-style:italic;margin:1px 0">'
                f'<b>{tag}:</b> {_esc(short)}</div>')
            continue
        hl = highlight_last_user and i == last_user
        indent = "margin-left:1.6em;" if role == "assistant" else ""
        accent = "border-left:3px solid #f0a500;" if hl else "border-left:3px solid transparent;"
        rows.append(
            f'<div style="{indent}{accent}padding-left:7px;margin:1px 0;font-size:12px;'
            f'line-height:1.35"><b style="color:{color}">{tag}:</b> {_esc(content)}</div>')
    return ('<div style="background:#fff;font-family:system-ui,-apple-system,sans-serif;'
            f'padding:1px 0">{"".join(rows)}</div>')


def _answer_cell(text) -> str:
    if text is None or str(text).strip() == "":
        return '<i style="color:#d62728">(empty response)</i>'
    return _esc(text)


def _fmt(v) -> str:
    return f"{v:.3f}" if isinstance(v, (int, float)) and not pd.isna(v) else "—"


def item_table_html(items, call_id, turn_id=None, models=None, metrics=None,
                    show_rubrics=True, context=True, caption=None, reasons=True) -> str:
    metrics = list(SEM_METRICS if metrics is None else metrics)
    it = find_item(items, call_id, turn_id)
    models = list(present_models(items) if models is None else models)
    cols = models + [GT]

    def th(txt, extra=""):
        return (f'<th style="padding:6px 9px;border:1px solid #dee2e6;background:#f8f9fa;'
                f'font-size:12px;vertical-align:top;{extra}">{txt}</th>')

    def td(inner, extra=""):
        return (f'<td style="padding:6px 9px;border:1px solid #dee2e6;font-size:12px;'
                f'vertical-align:top;max-width:340px;{extra}">{inner}</td>')

    head = ['<th style="padding:6px 9px;border:1px solid #dee2e6;background:#f1f3f5"></th>']
    for m in cols:
        hl = ";background:#eef7ee" if m == GT else ""
        head.append(th(f'<b>{html.escape(model_label(m))}</b>', hl))
    rows_html = [f'<tr>{"".join(head)}</tr>']

    ans = ['<td style="padding:6px 9px;border:1px solid #dee2e6;background:#f1f3f5;'
           'font-weight:600;font-size:11px;text-align:right;white-space:nowrap">Response</td>']
    for m in cols:
        text = it["ground_truth"] if m == GT else it["predictions"].get(m)
        bg = ";background:#f6fbf6" if m == GT else ""
        ans.append(td(_answer_cell(text), bg))
    rows_html.append(f'<tr>{"".join(ans)}</tr>')

    for metric in metrics:
        vals = {m: it["evaluations"].get(m, {}).get(metric) for m in models}
        numeric = {m: v for m, v in vals.items() if isinstance(v, (int, float))}
        best = max(numeric.values()) if numeric else None
        cells = [f'<td style="padding:6px 9px;border:1px solid #dee2e6;background:#f1f3f5;'
                 f'font-weight:600;font-size:11px;text-align:right;white-space:nowrap">'
                 f'{METRIC_LABELS.get(metric, metric)}</td>']
        for m in models:
            v = vals[m]
            style = "text-align:center"
            if best is not None and isinstance(v, (int, float)) and v == best:
                style += ";color:#2ca02c;font-weight:700"
            cells.append(td(_fmt(v), style))
        cells.append(td('<span style="color:#adb5bd">reference</span>',
                        "text-align:center;background:#f6fbf6"))
        rows_html.append(f'<tr>{"".join(cells)}</tr>')

    if show_rubrics:
        for rkey in RUBRIC_ORDER:
            cells = [f'<td style="padding:6px 9px;border:1px solid #dee2e6;background:#f1f3f5;'
                     f'font-weight:600;font-size:11px;text-align:right">'
                     f'{RUBRIC_LABELS.get(rkey, rkey)}</td>']
            for m in cols:
                rub = it["evaluations"].get(m, {}).get("rubrics", {}).get(rkey, {}) or {}
                reason = rub.get("reason")
                inner = f'<div style="text-align:center">{rubric_chip(rub.get("label"))}</div>'
                if reasons and reason:
                    inner += (f'<div style="font-size:10px;color:#6c757d;line-height:1.3;'
                              f'margin-top:3px;text-align:left">{_esc(reason)}</div>')
                bg = ";background:#f6fbf6" if m == GT else ""
                cells.append(td(inner, bg))
            rows_html.append(f'<tr>{"".join(cells)}</tr>')

    cap = (f'<div style="font-size:12px;color:#495057;margin:2px 0 6px">{caption}</div>'
           if caption else "")
    header = (f'<div style="font-size:11px;color:#868e96;margin-bottom:4px">'
              f'call_id <code>{html.escape(str(call_id))}</code> · turn {it["turn_id"]}</div>')
    conv = (f'<div style="margin:6px 0 10px">{render_conversation(it["input_messages"])}</div>'
            if context else "")
    table = ('<div style="overflow-x:auto"><table style="border-collapse:collapse;'
             f'font-family:system-ui,-apple-system,sans-serif">{"".join(rows_html)}</table></div>')
    return f'<div style="margin:8px 0 18px">{header}{cap}{conv}{table}</div>'


def show_item(items, call_id, turn_id=None, models=None, metrics=None,
              show_rubrics=True, context=True, caption=None, reasons=True) -> HTML:
    return HTML(item_table_html(items, call_id, turn_id, models=models, metrics=metrics,
                                show_rubrics=show_rubrics, context=context, caption=caption,
                                reasons=reasons))


def metrics_table(items, models=None, metrics=None):
    dfm = build_df_metrics(items)
    metrics = list((SEM_METRICS + LEX_METRICS) if metrics is None else metrics)
    models = list(present_models(items) if models is None else models)
    t = (dfm[dfm["model"].isin(models)]
         .groupby("model", observed=True)[metrics].mean().reindex(models))
    t.index = [model_label(m) for m in t.index]
    t.columns = [METRIC_LABELS.get(c, c) for c in t.columns]
    return t.style.format("{:.4f}").background_gradient(cmap="Greens", axis=0)


def rubric_mean_table(items, models=None):
    dfr = build_df_rubrics(items)
    order = list(present_models(items) if models is None else models)
    if (dfr["model"] == GT).any():
        order = order + [GT]
    t = (dfr.dropna(subset=["score"])
         .groupby(["model", "rubric"], observed=True)["score"].mean()
         .unstack("rubric").reindex(index=order)[RUBRIC_ORDER])
    t["Mean"] = t.mean(axis=1)
    t.index = [model_label(m) for m in t.index]
    t.columns = [RUBRIC_LABELS.get(c, c) for c in RUBRIC_ORDER] + ["Mean"]
    return (t.style.format("{:.3f}")
            .background_gradient(cmap="RdYlGn", axis=None, vmin=1, vmax=3))


def savefig(fig, name):
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight")


def plot_rubric_counts(items, models, name="rubrics_counts",
                       title="Judge ratings by model", stacked=False):
    dfr = build_df_rubrics(items)
    order = list(models) + ([GT] if (dfr["model"] == GT).any() else [])
    fig, axes = plt.subplots(2, 2, figsize=(15, 9))
    axes = axes.reshape(-1)
    for ax, rkey in zip(axes, RUBRIC_ORDER):
        sub = dfr[(dfr["rubric"] == rkey) & dfr["label"].notna() & dfr["model"].isin(order)]
        pivot = (sub.groupby(["model", "label"], observed=True).size()
                 .unstack("label").reindex(index=order, columns=LABELS_ORDERED).fillna(0))
        x = np.arange(len(order))
        if stacked:
            bottom = np.zeros(len(order))
            for lab in LABELS_ORDERED:
                ax.bar(x, pivot[lab].values, bottom=bottom,
                       color=LABEL_COLORS[lab], label=LABEL_DISPLAY[lab])
                bottom += pivot[lab].values
        else:
            w = 0.26
            for j, lab in enumerate(LABELS_ORDERED):
                ax.bar(x + (j - 1) * w, pivot[lab].values, width=w,
                       color=LABEL_COLORS[lab], label=LABEL_DISPLAY[lab])
        ax.set_title(RUBRIC_LABELS.get(rkey, rkey))
        ax.set_ylabel("Number of ratings")
        ax.set_xticks(x)
        ax.set_xticklabels([model_label(m) for m in order], rotation=25, ha="right", fontsize=8)
        ax.legend(title="Rating", fontsize=8)
    fig.suptitle(title, fontsize=14, y=1.005)
    fig.tight_layout()
    savefig(fig, name)
    plt.show()


def short_label(slug: str) -> str:
    if slug in BASELINE:
        return "Baseline"
    if slug in SFT:
        return "SFT"
    if slug in DPO:
        return "DPO"
    return model_label(slug)


def plot_rubric_stacked_pct(items, models, name="rubrics_stacked_pct",
                            title="Judge rating distributions", labels=None):
    def _xlab(m):
        return labels.get(m, short_label(m)) if isinstance(labels, dict) else short_label(m)

    dfr = build_df_rubrics(items)
    order = list(models)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    axes = axes.reshape(-1)
    for ax, rkey in zip(axes, RUBRIC_ORDER):
        sub = dfr[(dfr["rubric"] == rkey) & dfr["label"].notna() & dfr["model"].isin(order)]
        cnt = (sub.groupby(["model", "label"], observed=True).size()
               .unstack("label").reindex(index=order, columns=LABELS_ORDERED).fillna(0))
        pct = cnt.div(cnt.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 100
        x = np.arange(len(order))
        bottom = np.zeros(len(order))
        for lab in LABELS_ORDERED:
            vals = pct[lab].values
            ax.bar(x, vals, bottom=bottom, width=0.6,
                   color=LABEL_COLORS[lab], label=LABEL_DISPLAY[lab])
            for xi in range(len(order)):
                if vals[xi] >= 4:
                    ax.text(xi, bottom[xi] + vals[xi] / 2, f"{vals[xi]:.0f}%",
                            ha="center", va="center", fontsize=9, color="white",
                            fontweight="bold")
            bottom += vals
        ax.set_title(RUBRIC_LABELS.get(rkey, rkey))
        ax.set_ylim(0, 100)
        ax.set_ylabel("Ratings (%)")
        ax.set_xticks(x)
        ax.set_xticklabels([_xlab(m) for m in order], fontsize=10)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, title="Rating", ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(title, fontsize=14, y=1.0)
    fig.tight_layout(rect=(0, 0.04, 1, 0.99))
    savefig(fig, name)
    plt.show()
