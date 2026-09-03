# Multilingual Evaluation

This folder contains the local golden dataset for J2 multilingual core validation.

The core detector is deterministic and does not require API keys or network access.

Run `python scripts/evaluate_multilingual.py --dataset evaluation/multilingual/challenge_dataset.jsonl`
from the repository root to execute the CI challenge benchmark. The challenge
gate requires at least 95% overall accuracy, 95% for French, English, and
standard Arabic, and 90% for both Darija variants.

Future benchmark work can add comparison files for Gemini, Gemini with Darija few-shot examples, and Atlas-Chat-9B. Do not download or run model benchmarks from this folder unless explicitly requested.
