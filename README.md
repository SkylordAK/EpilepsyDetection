# EpilepsyDetection — Real-Time Multi-Pattern Seizure Detector

Real-time EEG analysis system that concurrently monitors six distinct seizure patterns using Welch Power Spectral Density estimation. No deep learning required — pure signal processing for low-latency detection.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python) ![SciPy](https://img.shields.io/badge/SciPy-1.12-8CAAE6) ![BrainFlow](https://img.shields.io/badge/BrainFlow-5.x-00A86B)

---

## Detected Seizure Patterns

| Pattern | Key Signal Feature |
|---------|-------------------|
| `HIGH_AMPLITUDE_SPIKE` | RMS amplitude > 3 sigma above baseline |
| `SPIKE_WAVE_3HZ` | 2.5–3.5 Hz PSD power dominant |
| `DELTA_DOMINANCE` | Delta (0.5–4 Hz) > 60% of total band power |
| `BETA_GAMMA_BURST` | Sudden power surge in 20–80 Hz range |
| `RHYTHMIC_THETA` | Sustained coherent theta (4–8 Hz) across channels |
| `HFO` | High-Frequency Oscillations in the 80–200 Hz band |

---

## Architecture

```
EEG headset (BrainFlow / OSC)
        |
epilepsy_detector.py
        |
  Welch PSD per channel (scipy.signal.welch)
        |
  Six parallel pattern detectors (per epoch)
        |
  Alert callback when pattern detected
```

---

## Getting Started

### Installation

```bash
git clone https://github.com/SkylordAK/EpilepsyDetection.git
cd EpilepsyDetection
pip install -r requirements.txt
```

### Run — Live Detection

```bash
python epilepsy_detector.py
```

### Run — Offline File Analysis

```bash
python epilepsy_detector.py --file recording.csv
```

---

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WINDOW_SEC` | `2.0` | Welch PSD epoch window in seconds |
| `OVERLAP` | `0.5` | Window overlap fraction |
| `AMPLITUDE_SIGMA` | `3.0` | Spike amplitude threshold (std deviations above baseline) |
| `DELTA_POWER_RATIO` | `0.60` | Delta dominance threshold (fraction of total power) |
| `HFO_MIN_HZ` | `80` | Lower bound of HFO band in Hz |
| `SAMPLE_RATE` | `256` | EEG sample rate in Hz |

---

## Signal Processing

- **Welch PSD** — `scipy.signal.welch` with Hann window reduces spectral leakage vs. raw FFT
- **Band power** — `np.trapezoid` integration over PSD within each frequency band
- **Z-score amplitude** — rolling mean/std baseline for hardware-agnostic spike detection
- **Multi-channel** — all channels processed independently; detections aggregated per pattern

---

## Requirements

```
numpy>=1.24
scipy>=1.12
brainflow>=5.0
python-osc>=1.8
```

---

## Related Projects

- [SeizureDetectionProject](https://github.com/SkylordAK/SeizureDetectionProject) — CNN + LSTM deep learning on the CHB-MIT dataset
- [SSVEPControl](https://github.com/SkylordAK/SSVEPControl) — SSVEP-based BCI control

---

## Disclaimer

Research and educational project. Not a certified medical device and must not be used for clinical diagnosis.

## License

MIT
