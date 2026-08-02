# ECG Screening Toolkit

A machine learning system that reads an ECG and flags what warrants a
clinician's attention. Version one detects atrial fibrillation from the
irregularity of intervals between heartbeats, built end to end from raw
PhysioNet waveforms through feature engineering, patient-level validation, and a
trained model, to a Streamlit dashboard served from a VPS.

**Live application:** [ecg.bentileo.tech](https://ecg.bentileo.tech)
**Project write-up:** [bentileo.tech/projects/ecg-screening-toolkit](https://bentileo.tech/projects/ecg-screening-toolkit/)

> Educational project, **not a medical device**. Do not use for diagnosis.

---

## Pipeline

```
PTB-XL Waveform Extraction
        ↓
R-peak Detection
        ↓
RR-Interval Feature Engineering
        ↓
Signal-Quality Filtering
        ↓
Patient-Grouped Cross-Validation
        ↓
Random Forest Training
        ↓
Results Saved to Supabase
        ↓
Streamlit Dashboard Hosted on Hostinger VPS
```

## What atrial fibrillation looks like in data

Atrial fibrillation is common, often silent, and carries a stroke risk that
anticoagulation can substantially reduce. The diagnosis hinges on a pattern that
is visually obvious once you know it: the intervals between beats become
irregularly irregular, with no underlying periodicity at all.

That pattern is measurable. Across the cleaned dataset, the coefficient of
variation of the RR interval has a median of 0.197 in atrial fibrillation against
0.026 otherwise, and the 25th percentile of the AFib group sits above the 75th
percentile of everything else.

## Results

Patient-grouped, label-stratified five-fold cross-validation across 21,576
recordings, of which 1,480 are atrial fibrillation (6.9%):

| Metric | Value |
| --- | --- |
| AUPRC | 0.70 |
| AUROC | 0.97 |
| Recall at operating threshold | 0.96 |
| Precision at operating threshold | 0.34 |

Accuracy is not reported. On a dataset with 6.9% positives, a model that never
predicts atrial fibrillation scores 93%.

A random forest with balanced class weights was selected over a logistic
baseline, which reached only 0.41 AUPRC on identical folds.

### The operating threshold is a clinical decision

The threshold is set at 0.10 rather than the conventional 0.50, because the two
errors are not equally costly. A missed case leaves a patient at unmonitored
stroke risk; a false positive costs a confirmatory review.

| Threshold | Recall | Precision |
| --- | --- | --- |
| 0.10 (operating point) | 0.96 | 0.34 |
| 0.20 | 0.92 | 0.41 |
| 0.30 | 0.87 | 0.46 |
| 0.50 (default) | 0.74 | 0.58 |

Maximizing recall is defensible only because flagged recordings receive human
confirmation. A fully autonomous system would need a higher-precision operating
point to avoid alert fatigue.

## Design decisions

**Patient-level splitting.** The dataset holds multiple recordings per patient. A
random split would place one patient's recordings on both sides of the train and
test boundary, letting the model score by recognizing the person rather than the
pathology. All splitting and cross-validation is grouped by `patient_id`, and
every fold is verified to share zero patients across train and test.

**Wave delineation was measured and rejected.** PR, QRS, and QT features were
attempted first. Against a recording with a directly verified 94 ms QRS, the
delineator returned per-beat values from 78 to 208 ms across a single regular
rhythm — detector failure, not physiology. R-peak detection, by contrast, was
exact. Features requiring wave boundaries were therefore excluded from v1.

**Labels were verified against the source.** The atrial fibrillation label was
confirmed against the dataset's published record count of 1,514 and against the
cardiologists' free-text reports, which resolved an apparent contradiction:
records carrying both a "normal" and an "AFib" code mean *otherwise* normal.

**Signal-quality exclusion is label-biased.** 223 records (~1%) were removed for
failed R-peak detection. 15% of them are atrial fibrillation against a 6.9%
baseline, because fibrillatory baselines are harder to delineate. Reported
metrics are therefore modestly optimistic relative to deployment.

## Limitations

- Version one detects rhythm irregularity, so it cannot separate atrial
  fibrillation from atrial flutter, frequent ectopy, or sinus arrhythmia. That
  requires P-wave and QRS morphology, and it bounds precision by design.
- Ten-second recordings are shorter than the rhythm strip a clinician would use.
- Not clinically validated; not a medical device.

## Roadmap

**Image digitization.** Accept a photograph or scan of a paper ECG, recover the
signal, and classify it — the version usable outside a research dataset.

**Morphology features.** Revisit delineation with a delineator validated against
annotated boundaries, using the dataset's own bundle branch block and AV block
labels as ground truth. This is what extends the toolkit beyond rhythm to
ischemic ST changes and conduction disease.

**Explainability.** Surface which features drove a prediction, so a clinician
sees why a recording was flagged rather than trusting a probability.

## Dataset

[PTB-XL](https://physionet.org/content/ptb-xl/) — 21,799 clinical 12-lead ECGs
from 18,869 patients (Wagner et al., *Scientific Data*, 2020). Lead II at 100 Hz
is used. The data is not included in this repository; `scripts/download_data.sh`
fetches it.

## Requirements

- Python 3.12, installed through [pyenv](https://github.com/pyenv/pyenv)
- [Poetry](https://python-poetry.org/docs/basic-usage/)
- `wget`, for the dataset download
- A [Supabase](https://supabase.com) project (optional, for prediction history)
- A VPS (optional, for hosting)

## Installation

```bash
make install-dev
make data              # downloads PTB-XL into data/ptbxl (about 500 MB)
```

## Usage

Train the model end to end:

```bash
make train
```

Launch the dashboard:

```bash
make samples           # one-off: writes demo ECGs
make dashboard
```

Screen an ECG programmatically:

```python
from ecg_afib import extractor, main

signal = extractor.load_signal_csv("samples/afib_1.csv")
result = main.screen(signal)

print(result["probability"])   # 0.98
print(result["flagged"])       # True
print(result["heart_rate"])    # 150.0
```

## Configuration

Edit `src/ecg_afib/settings.py`:

- `THRESHOLD` — operating point; lower catches more cases, raises false alarms
- `N_ESTIMATORS`, `CLASS_WEIGHT` — model parameters
- `MIN_BEATS`, `MAX_RR_MS` — signal-quality limits
- `SAMPLING_RATE`, `LEAD_INDEX` — signal parameters

## Deployment

1. Create the Supabase table with `scripts/schema.sql`.
2. Copy `.env.example` to `.env` and fill in the credentials.
3. Clone onto the VPS at `/opt/ecg-afib` and create a systemd unit running
   `make dashboard`.
4. Run `scripts/deploy.sh` on the server to pull, install, and restart.

The trained model is not committed. Copy it to the server once with `scp`, or
attach it to a GitHub release.

## Project structure

```
.circleci/          lint and test on every push
.github/workflows/  deploy to the VPS
scripts/            data download, sample generation, deployment, schema
src/ecg_afib/
    settings.py     all configuration
    extractor.py    metadata, labels, and waveform loading
    processor.py    R-peak detection, features, quality filtering
    model.py        build, evaluate, train, save, predict
    database.py     Supabase persistence
    main.py         pipeline orchestration
    streamlit_app.py dashboard
tests/              one test module per source module
```

## Author

Leonardo Bentivoglio — ACSM Certified Clinical Exercise Physiologist,
M.S. Information Management (Data Science) in progress.
[bentileo.tech](https://bentileo.tech) ·
[LinkedIn](https://linkedin.com/in/leonardo-bentivoglio)
