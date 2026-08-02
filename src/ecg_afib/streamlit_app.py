"""Streamlit dashboard for the ECG screening toolkit.

Launch:  make dashboard
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from ecg_afib import database, extractor, main, settings

DISCLAIMER = (
    "Educational project, **not a medical device**. Do not use for diagnosis. "
    "Flagged rhythms require confirmation by a clinician."
)

st.set_page_config(
    page_title="ECG Screening Toolkit",
    page_icon="~",
    layout="centered",
)


def inject_styles() -> None:
    """Refine typography and spacing on top of the theme in .streamlit/config.toml."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

        /* ECG paper grid, softened by a wash so it reads as texture rather
           than as a drawn grid. Without the overlay it dominates the page. */
        .stApp {
            background-image:
                linear-gradient(rgba(242,198,192,.30) .5px, transparent .5px),
                linear-gradient(90deg, rgba(242,198,192,.30) .5px, transparent .5px);
            background-size: 26px 26px, 26px 26px;
        }
        .stApp::before {
            content: '';
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background: linear-gradient(180deg,
                rgba(253,252,250,.78) 0%,
                rgba(253,252,250,.94) 55%,
                #FDFCFA 100%);
        }
        .stApp > header { background: transparent; }
        .block-container { position: relative; z-index: 1; }
        .block-container { max-width: 800px; padding-top: 2.2rem; }

        h1, h2, h3, p, li, .stMarkdown {
            font-family: 'Source Serif 4', Georgia, serif !important;
        }
        h1 {
            font-weight: 700 !important;
            letter-spacing: -.018em;
            font-size: 2.5rem !important;
            margin-bottom: .2rem !important;
        }

        /* Metrics: readable, not shouting. */
        [data-testid="stMetricValue"] {
            font-family: 'Source Serif 4', Georgia, serif !important;
            font-weight: 700 !important;
            font-size: 1.75rem !important;
            line-height: 1.2 !important;
        }
        [data-testid="stMetricLabel"] {
            font-family: 'Inter', system-ui, sans-serif !important;
            text-transform: uppercase;
            letter-spacing: .09em;
            font-size: .66rem !important;
            opacity: .7;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 1.6rem;
            border-bottom: 1px solid #E4E1DC;
        }
        .stTabs [data-baseweb="tab"] {
            font-family: 'Inter', system-ui, sans-serif !important;
            padding: 0 0 .6rem 0;
            font-size: .9rem;
        }

        /* Segmented control: legible, with the selection in signal red. */
        [data-baseweb="segmented-control"] button,
        .stButtonGroup button {
            font-family: 'Inter', system-ui, sans-serif !important;
            font-size: .82rem !important;
        }

        /* Upload area and the v2 notice, styled to match.
           No font-family is set anywhere inside the dropzone: Streamlit draws
           the upload icon with a ligature font, and overriding it renders the
           ligature name as literal text next to the icon. */
        [data-testid="stFileUploaderDropzone"] {
            background: rgba(200, 52, 43, .03) !important;
            border: 1px solid rgba(200, 52, 43, .25) !important;
            border-radius: 3px;
        }

        .caption-mono {
            font-family: 'Inter', system-ui, sans-serif;
            font-size: .68rem;
            letter-spacing: .1em;
            text-transform: uppercase;
            opacity: .68;
        }

        .coming-soon {
            border: 1px solid rgba(200, 52, 43, .25);
            border-radius: 3px;
            padding: .85rem 1.1rem;
            margin-top: .8rem;
            background: rgba(200, 52, 43, .03);
            font-family: 'Inter', system-ui, sans-serif;
            font-size: .82rem;
            color: #5C5C64;
        }
        .coming-soon strong { color: #C8342B; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def list_samples() -> dict:
    """Bundled sample ECGs, so the hosted app needs no dataset."""
    if not settings.SAMPLES_DIR.exists():
        return {}
    return {path.stem: path for path in sorted(settings.SAMPLES_DIR.glob("*.csv"))}


def sample_label(name: str) -> str:
    """Turn a filename stem into something readable."""
    kind, _, number = name.partition("_")
    pretty = {"normal": "Normal", "afib": "AFib"}.get(kind, kind.title())
    return f"{pretty} {number}"


def plot_signal(signal, r_peaks):
    """Draw the waveform with detected R-peaks marked."""
    seconds = np.arange(len(signal)) / settings.SAMPLING_RATE

    figure, axes = plt.subplots(figsize=(11, 3.1))
    figure.patch.set_facecolor("#FDFCFA")
    axes.set_facecolor("#FDFCFA")

    axes.plot(seconds, signal, linewidth=1.0, color="#16161A")

    peaks = np.asarray(r_peaks)
    peaks = peaks[peaks < len(signal)]
    if len(peaks):
        axes.scatter(
            peaks / settings.SAMPLING_RATE,
            signal[peaks],
            color="#C8342B",
            s=22,
            zorder=5,
        )

    axes.set_xlabel("Seconds", fontsize=9, color="#5C5C64")
    axes.set_ylabel("mV", fontsize=9, color="#5C5C64")
    axes.tick_params(labelsize=8, colors="#5C5C64")
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color("#E4E1DC")
    axes.grid(True, color="#F2C6C0", linewidth=.4, alpha=.7)

    figure.tight_layout()
    return figure


def show_result(result: dict) -> None:
    """Render the screening outcome."""
    if result["probability"] is None:
        st.warning(result["message"])
        return

    left, middle, right = st.columns(3)
    left.metric("Probability of AFib", f"{result['probability']:.0%}")
    middle.metric("Heart rate", f"{result['heart_rate']:.0f} bpm")
    right.metric("Rhythm variability", f"{result['features']['rr_cv']:.3f}")

    if result["flagged"]:
        st.error(f"**Flagged.** {result['message']}")
    else:
        st.success(result["message"])

    features = result["features"]
    st.markdown(
        f"<p class='caption-mono'>Threshold {result['threshold']:.0%} &middot; "
        f"RMSSD {features['rmssd_ms']:.0f} ms &middot; "
        f"{features['n_beats']:.0f} beats detected</p>",
        unsafe_allow_html=True,
    )


def screening_tab() -> None:
    """Select or upload an ECG, then screen it."""
    samples = list_samples()

    source_kind = st.radio(
        "Input",
        ["Sample recording", "Upload a signal"],
        horizontal=True,
        label_visibility="collapsed",
    )

    signal, source = None, None

    if source_kind == "Sample recording":
        if not samples:
            st.info("No samples found. Run `make samples` to create them.")
            return
        names = list(samples)
        chosen = st.segmented_control(
            "Recording",
            names,
            format_func=sample_label,
            default=names[0],
            label_visibility="collapsed",
        )
        if chosen:
            signal, source = extractor.load_signal_csv(samples[chosen]), chosen
    else:
        upload = st.file_uploader(
            f"Signal file — one column of lead-{settings.LEAD_NAME} voltages "
            f"at {settings.SAMPLING_RATE} Hz",
            type=["csv"],
        )
        st.markdown(
            "<div class='coming-soon'><strong>Coming in v2:</strong> upload a "
            "photograph of a printed ECG. The signal is recovered from the "
            "image, then screened the same way.</div>",
            unsafe_allow_html=True,
        )
        if upload is not None:
            signal, source = extractor.load_signal_csv(upload), "upload"

    if signal is None:
        return

    result = main.screen_and_store(signal, source)
    st.pyplot(plot_signal(signal, result["r_peaks"]))
    st.markdown(
        f"<p class='caption-mono'>Lead {settings.LEAD_NAME} &middot; "
        f"{settings.SAMPLING_RATE} Hz &middot; R-peaks marked</p>",
        unsafe_allow_html=True,
    )
    st.write("")
    show_result(result)


def history_tab() -> None:
    """Show previously screened recordings, behind an admin password.

    Screening results contain no identifying information, but they are
    operational data rather than something a visitor needs, so the view is
    private. Reading uses the secret key, which never leaves the server.
    """
    if not st.session_state.get("admin_unlocked"):
        st.caption("Screening history is private.")
        entered = st.text_input(
            "Admin password", type="password", label_visibility="collapsed",
            placeholder="Admin password",
        )
        if entered:
            if entered == settings.ADMIN_PASSWORD:
                st.session_state["admin_unlocked"] = True
                st.rerun()
            else:
                st.error("Incorrect.")
        return

    rows = database.fetch_predictions()
    if not rows:
        st.info("No recordings screened yet.")
        return

    history = pd.DataFrame(rows)
    left, middle, right = st.columns(3)
    left.metric("Recordings screened", len(history))
    right.metric("Flagged", int(history["flagged"].sum()))
    if "probability" in history:
        middle.metric("Median probability", f"{history['probability'].median():.0%}")

    display = history.drop(columns=["id"], errors="ignore")
    st.dataframe(display, use_container_width=True, hide_index=True)


def about_tab() -> None:
    """Explain the method, the evidence behind it, and its limits."""
    st.markdown("""
### What this does

Atrial fibrillation is common, often silent, and carries a stroke risk that
anticoagulation can substantially reduce. Its signature is a rhythm that is
*irregularly irregular* — the intervals between beats vary with no underlying
periodicity at all.

This tool measures that. It detects R-peaks, computes nine features describing
the intervals between them, and scores the result with a random forest trained on
21,576 clinical recordings.
""")

    st.divider()

    st.markdown("""
### The features

Every feature derives from R-peak positions, which are the tall, unmistakable
spikes of ventricular depolarization. Nothing here depends on measuring the
boundaries of the P wave or the QRS complex, for reasons given below.

The feature that carries the most weight is the **coefficient of variation of the
RR interval** — the standard deviation of the intervals divided by their mean.
Dividing by the mean matters more than it looks. A 40 ms spread means something
very different at 40 beats per minute than at 150. Normalizing by rate is what
allows detection of atrial fibrillation with a *controlled* ventricular
response — irregular at 70 bpm, in a patient on a beta blocker — which mean heart
rate alone would call normal.
""")

    variability = pd.DataFrame(
        {
            "Median": [0.197, 0.026],
            "25th percentile": [0.151, 0.014],
            "75th percentile": [0.254, 0.059],
        },
        index=["Atrial fibrillation", "Everything else"],
    )
    st.dataframe(variability, use_container_width=True)

    st.markdown("""
The 25th percentile of the AFib group sits above the 75th percentile of
everything else. The distributions barely touch, which is why a relatively simple
model performs well.
""")

    st.divider()

    st.markdown("""
### Why there are no PR, QRS, or QT measurements

Wave-boundary features were attempted first and rejected on evidence.

Against a recording with a directly verified 94 ms QRS, the delineator returned
per-beat values ranging from 78 to 208 ms across a single regular rhythm. That is
not physiological variation between beats; it is boundary detection failing.

Physiological bounds cannot rescue this. A 168 ms QRS is anatomically possible in
bundle branch block, so no sanity check rejects it — even when the true value is
94 ms. Bounds catch the impossible, not the merely wrong.

R-peak detection, by contrast, was exact on the same recording. So the feature
set was restricted to what could be measured reliably, and morphology was scoped
as future work.
""")

    st.divider()

    st.markdown("""
### How it was validated

**Split by patient, not by recording.** Several patients contribute more than one
recording. A random split would place one patient's recordings on both sides of
the train and test boundary, letting the model score well by recognizing the
person rather than the pathology. Every cross-validation fold is grouped by
patient identifier and verified to share zero patients across train and test.

**Accuracy is not reported.** With 6.9% positives, a model that never predicts
atrial fibrillation is 93% accurate and clinically useless. Performance is
reported on precision, recall, and area under the precision-recall curve.
""")

    metrics = pd.DataFrame(
        {"Value": ["0.70", "0.97", "0.96", "0.34"]},
        index=[
            "AUPRC",
            "AUROC",
            "Recall at operating threshold",
            "Precision at operating threshold",
        ],
    )
    st.dataframe(metrics, use_container_width=True)

    st.markdown("""
A random forest with balanced class weights was chosen over a logistic baseline,
which reached only 0.41 AUPRC on identical folds.
""")

    st.divider()

    st.markdown("""
### Why the threshold is 10%, not 50%

A classifier outputs a probability; somebody has to decide where to draw the line.
The conventional 50% is an arbitrary default, and it is the wrong one here,
because the two errors are not equally costly. A missed case leaves a patient at
unmonitored stroke risk. A false positive costs a confirmatory review.
""")

    thresholds = pd.DataFrame(
        {
            "Recall": [0.96, 0.92, 0.87, 0.74],
            "Precision": [0.34, 0.41, 0.46, 0.58],
        },
        index=["10% (in use)", "20%", "30%", "50% (default)"],
    )
    st.dataframe(thresholds, use_container_width=True)

    st.markdown("""
Maximizing recall is defensible **only** because flagged recordings receive human
confirmation. A fully autonomous system would need a higher-precision operating
point, because a tool that cries wolf gets ignored — and alert fatigue costs
sensitivity in practice that no confusion matrix records.
""")

    st.divider()

    st.markdown("""
### What this cannot do

**It detects irregularity, not atrial fibrillation specifically.** Atrial flutter
with variable block, frequent ectopy, and sinus arrhythmia are all irregular, and
telling them apart requires P-wave and QRS morphology. This bounds precision by
design and is the main reason precision sits at 34%.

**Ten seconds is a short look.** Clinical diagnosis conventionally uses a longer
rhythm strip, so this makes a lower-confidence judgment than a clinician would.

**The training data was filtered, and the filtering was biased.** 223 recordings
were excluded because R-peak detection failed on them. Those exclusions are not
random: 15% were atrial fibrillation against a 6.9% baseline, because
fibrillatory baselines are genuinely harder to delineate. Reported metrics are
therefore modestly optimistic relative to what a deployed system would see.

**It has not been clinically validated.** It is not a medical device.
""")

    st.divider()

    st.markdown("""
### What comes next

**Image digitization** — accept a photograph of a paper ECG, recover the
underlying signal, and classify it. This is the version usable outside a research
dataset.

**Morphology features** — revisit delineation with a delineator validated against
annotated boundaries, using the dataset's own bundle branch block and AV block
labels as ground truth. This is what extends the toolkit beyond rhythm to
ischemic ST changes and conduction disease.

**Explainability** — surface which features drove a prediction, so a clinician
sees why a recording was flagged rather than trusting a probability.
""")

    st.divider()

    st.markdown("""
**Data:** [PTB-XL](https://physionet.org/content/ptb-xl/) — 21,799 clinical
12-lead ECGs from 18,869 patients (Wagner et al., *Scientific Data*, 2020).
Lead II at 100 Hz.

**Source:** [github.com/bentileo/ecg-afib](https://github.com/bentileo/ecg-afib)
&nbsp;·&nbsp; **Write-up:** [bentileo.tech](https://bentileo.tech/projects/ecg-screening-toolkit/)
""")


def render() -> None:
    """Draw the application."""
    inject_styles()

    st.title("ECG Screening Toolkit")
    st.markdown(
        "<p class='caption-mono'>Ten seconds of rhythm. One question.</p>",
        unsafe_allow_html=True,
    )
    st.caption(DISCLAIMER)

    if not settings.MODEL_PATH.exists():
        st.error(f"No model at {settings.MODEL_PATH}. Run `make train` first.")
        return

    # The history view only appears when there is somewhere to read it from.
    labels = ["Screen", "Method"]
    if database.admin_available() and settings.ADMIN_PASSWORD:
        labels.insert(1, "History")

    tabs = st.tabs(labels)
    views = {"Screen": screening_tab, "History": history_tab, "Method": about_tab}
    for label, tab in zip(labels, tabs):
        with tab:
            views[label]()


render()
