# Multilingual Evaluation

This folder contains versioned regression datasets for J2 multilingual core
validation.

The core detector is deterministic and does not require API keys or network access.

Run `python scripts/evaluate_multilingual.py --dataset evaluation/multilingual/challenge_dataset.jsonl`
from the repository root to execute the default golden-style threshold check.
Use `--profile challenge` to execute the stricter CI challenge gate. The
challenge gate requires at least 95% overall accuracy, 95% for French, English,
and standard Arabic, and 90% for both Darija variants.

The golden and challenge JSONL files are regression benchmarks. They are not, by
themselves, an external validation of open-ended generalization; that validation
must come from an independent re-audit with unseen examples.

## Training and External Evaluation Sources

`scripts/prepare_multilingual_training_data.py` prepares local, unversioned
training splits from `MBZUAI-Paris/DODa-10K`
(`https://huggingface.co/datasets/MBZUAI-Paris/DODa-10K`) via the Hugging Face
dataset viewer API. The dataset is licensed `cc-by-nc-4.0`; it is used here for
academic PFA training and internal held-out validation. The script splits source
indices before expanding the parallel language columns to avoid parallel-index
leakage.

`scripts/train_language_detector.py` trains two local character TF-IDF +
Logistic Regression classifiers, one for `fr/en/ary-latin` and one for
`ar/ary-arabic`, and exports `backend/app/multilingual/artifacts/language_detector.joblib`.

`scripts/evaluate_external_moroccan_codeswitching.py` measures a limited
out-of-distribution Darija Arabic signal from `samihyounes/Moroccan-Codeswitching`
(`https://huggingface.co/datasets/samihyounes/Moroccan-Codeswitching`), licensed
`apache-2.0`. It reconstructs Arabic-script Darija candidate sentences from the
public `test.tsv` and reports the result separately from internal training
metrics.

Future benchmark work can add comparison files for Gemini, Gemini with Darija few-shot examples, and Atlas-Chat-9B. Do not download or run model benchmarks from this folder unless explicitly requested.
