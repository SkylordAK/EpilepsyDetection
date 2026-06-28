# EpilepsyDetection — Codebase Audit Report

**Audited by:** Claude Sonnet 4.6 (Senior Software Architect mode)
**Date:** 2026-06-28

---

## 1. Project Overview

**Purpose:** Real-time EEG epilepsy pattern detector for Muse S headset via OSC. Detects high-amplitude spikes, 3 Hz spike-and-wave complexes, delta dominance, beta/gamma bursts, rhythmic theta, and high-frequency oscillations (HFOs). Includes a smoke test with synthetic data.

**Tech Stack:** Python / SciPy / NumPy / pythonosc

**Files:** `epilepsy_detector.py`, `eeg_recorder.py` (separate recorder), `README.md`, `.gitignore`

---

## 2. Issues Found

### HIGH

#### H-1: `np.trapz` deprecated in NumPy 2.0
**File:** `epilepsy_detector.py` (line 52)

```python
return np.trapz(psd[mask], freqs[mask], axis=0)
```

`numpy.trapz` was deprecated in NumPy 2.0 and renamed `numpy.trapezoid`. Code will produce `DeprecationWarning` on NumPy 1.25+ and will break on NumPy 2.0+.

**Fix:** Replace with `np.trapezoid(...)` and add a compat shim for older NumPy:
```python
_trapezoid = getattr(np, 'trapezoid', np.trapz)
```

---

#### H-2: `bandpass` filter with `filtfilt` requires `len(data) > 3 * filter_order`
**File:** `epilepsy_detector.py` (line 41)

```python
return filtfilt(b, a, data, axis=0)
```

`filtfilt` requires the data length to be significantly larger than the filter order (typically `> 3 * padlen` which defaults to `3 * max(len(b), len(a))`). With a 4th-order Butterworth filter, `len(b) = len(a) = 5`, so the minimum data length is ~15 samples. For a 2-second window at 256 Hz (512 samples) this is fine, but if called with shorter windows it will raise a `ValueError` silently caught by caller logic.

---

#### H-3: `HFO` band upper limit exceeds Nyquist — silently clamped
**File:** `epilepsy_detector.py` (lines 28–33, 67–69)

```python
'hfo': (80, 125),  # limited by Nyquist at 256 Hz
```

Nyquist for 256 Hz sampling is 128 Hz. The upper bound of 125 Hz is within Nyquist, but the comment is slightly misleading. More critically, in `analyze_window`:

```python
for name, (lo, hi) in BANDS.items():
    if hi >= FS / 2:
        hi = FS / 2 - 1
```

This clamp uses `>= FS / 2` (128.0), so 125 < 128 is NOT clamped. This is correct but the code structure implies HFO was originally out of range and was later adjusted. The real concern is that at 256 Hz, the actual HFO band (>80 Hz) has poor resolution in a 2-second window.

---

### MEDIUM

#### M-1: `eeg_handler` nested inside `run_live` — `nonlocal` on list reassignment is correct but `active_patterns` initialization is error-prone
**File:** `epilepsy_detector.py` (lines 250–270)

`active_patterns = ["None"]` is a mutable list that is reassigned (not mutated) inside `eeg_handler` using `nonlocal`. This pattern is correct Python but fragile — adding any mutating operation (`.append`) without the `nonlocal` declaration would silently create a local variable. Using a simple class or named tuple for shared state would be cleaner.

---

#### M-2: Alert accumulator decrements on normal windows but never resets to zero fully
**File:** `epilepsy_detector.py` (line 298)

```python
alert_accumulator[0] = max(0, alert_accumulator[0] - 1)
```

The accumulator decrements by 1 per normal window but increments by 1 per alert window, and only triggers the sustained alert at `>= 3`. This is intentional hysteresis, but there is no upper bound on the accumulator — prolonged seizure activity could accumulate a large value that takes many normal windows to drain. Consider a fixed window (ring buffer) approach for more accurate sustained detection.

---

#### M-3: CSV file handle is never flushed during recording
**File:** `epilepsy_detector.py` (lines 313–316)

The CSV writer writes directly to a file opened with `open(filename, 'w', newline='')`. Without explicit `flush()` calls, the OS write buffer may hold several seconds of data. If the program is interrupted (power loss, SIGKILL), the last several seconds of EEG data are lost.

**Fix:** Flush periodically: `session_f[0].flush()` every N windows.

---

### LOW

#### L-1: Smoke test checks `'SPIKE_WAVE' not in patterns_str` but pattern is `SPIKE_WAVE_3HZ`
**File:** `epilepsy_detector.py` (line 207)

```python
if 'SPIKE_WAVE' not in patterns_str:
```

This substring check works correctly for `'SPIKE_WAVE_3HZ'`, but it's fragile. If the pattern name changes to e.g. `'3HZ_SPIKE_WAVE'`, the test would fail unexpectedly.

---

#### L-2: No `requirements.txt`

Dependencies (`scipy`, `numpy`, `pythonosc`) are not listed. Add a `requirements.txt`.

---

## 3. Fixes Applied

None — no automated fixes applied (all issues require careful domain-specific decisions).

---

## 4. Recommendations

1. Replace `np.trapz` with `np.trapezoid` / compat shim immediately (H-1).
2. Add periodic CSV flush during recording sessions (M-3).
3. Add `requirements.txt`.
4. Consider clamping the alert accumulator to a maximum value (e.g., 10) for predictable drain time.
