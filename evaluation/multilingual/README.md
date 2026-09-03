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

`arabic_ad_hoc_dataset.jsonl` is a small J2C smoke benchmark written after
training to exercise unseen Arabic-branch financial prompts. It is not a
replacement for an independent Claude audit.

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
The current artifact keeps the Latin model from the previous DODa-trained
artifact and hardens only the Arabic branch with a weighted combination of DODa
Arabic examples and the Arabic-script `ary`/`msa` subset from
`atlasia/Darija-LID` (`https://huggingface.co/datasets/atlasia/Darija-LID`),
licensed `MIT`. `scripts/prepare_arabic_lid_training_data.py` prepares local,
unversioned splits and excludes Arabizi plus non-MSA Arabic dialects from the
main Arabic training set.

Because the versioned `language_detector.joblib` artifact is derived in part
from DODa (`cc-by-nc-4.0`), it is documented here for the academic/non-commercial
PFA context under the constraints of that source. Darija-LID contributes MIT
licensed Arabic branch examples. This is provenance documentation, not legal
advice.

`scripts/evaluate_external_moroccan_codeswitching.py` measures a limited
out-of-distribution Darija Arabic signal from `samihyounes/Moroccan-Codeswitching`
(`https://huggingface.co/datasets/samihyounes/Moroccan-Codeswitching`), licensed
`apache-2.0`. It reconstructs Arabic-script Darija candidate sentences from the
public `test.tsv` and reports the result separately from internal training
metrics.

Future benchmark work can add comparison files for Gemini, Gemini with Darija few-shot examples, and Atlas-Chat-9B. Do not download or run model benchmarks from this folder unless explicitly requested.
