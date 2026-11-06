#!/usr/bin/env bash
# Runs the given experiments in order and evaluates them together, e.g. `bash run.sh sft/1b dpo/1b`.
# A run is named by its config under configs/ and writes to experiments/<run>/; without arguments
# the main experiment runs: base models, SFT and DPO for 1B, 12B-PT and 12B-IT.
# Steps that call the judge (score_candidates, rank_candidates, judge) need a running Ollama server.
set -euo pipefail
cd "$(dirname "$0")"
export WANDB_PROJECT=serbian-medical-dialogue

runs=("$@")
if [ ${#runs[@]} -eq 0 ]; then
    runs=(base/1b base/12b base/27b sft/1b sft/12b-pt sft/12b-it dpo/1b dpo/12b-pt dpo/12b-it)
fi

# Check every name first, so a typo does not stop the script after hours of training.
for run in "${runs[@]}"; do
    case $run in
        base/* | sft/* | dpo/*) [ -f "configs/$run.yaml" ] || { echo "No config configs/$run.yaml" >&2; exit 1; } ;;
        *) echo "Unknown run '$run'; expected base/<name>, sft/<name> or dpo/<name>" >&2; exit 1 ;;
    esac
done

python3 scripts/prepare_data.py

predictions=()
for run in "${runs[@]}"; do
    config=configs/$run.yaml
    case $run in
        sft/*)
            python3 scripts/sft.py --config "$config"
            ;;
        dpo/*)
            python3 scripts/generate_candidates.py --config "$config"
            python3 scripts/score_candidates.py --config "$config"
            python3 scripts/rank_candidates.py --config "$config"
            python3 scripts/build_dpo_dataset.py --config "$config"
            python3 scripts/dpo.py --config "$config"
            ;;
    esac
    python3 scripts/generate.py --config "$config"
    predictions+=("experiments/$run/predictions.json")
done

python3 scripts/merge_predictions.py --config configs/eval.yaml --inputs "${predictions[@]}"
python3 scripts/eval_reference.py --config configs/eval.yaml
python3 scripts/judge.py --config configs/eval.yaml
python3 scripts/aggregate_results.py --config configs/eval.yaml
