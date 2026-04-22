# Epilepsy Detection — Real-Time EEG Monitor

This project provides a real-time EEG monitoring and analysis system designed for the Muse S (and other Muse headbands). it utilizes OSC (Open Sound Control) to receive raw EEG data and applies signal processing to detect abnormal neural patterns associated with epileptic activity.

## Features
- **Real-time Detection**: Identifies spikes, spike-and-wave patterns, and rhythmic bursts.
- **Multi-Band Power Analysis**: Monitors Delta, Theta, Alpha, Beta, and Gamma bands.
- **HFO Detection**: Detects High-Frequency Oscillations (HFOs) which are often biomarkers for epileptogenic zones.
- **Labelled Recording**: Records raw EEG data with automated "silver labels" based on the detector's findings.
- **Visual Dashboard**: Color-coded console output for immediate state awareness.

## Patterns Detected
- `HIGH_AMPLITUDE_SPIKE`: Rapid, high-voltage transients.
- `SPIKE_WAVE_3HZ`: Classic 3Hz spike-and-wave patterns often seen in absence seizures.
- `DELTA_DOMINANCE`: Post-ictal slowing detection.
- `BETA_GAMMA_BURST`: Fast activity often seen at the onset of seizures.
- `RHYTHMIC_THETA`: Rhythmic discharges in the theta range.
- `HFO_DETECTED`: High-frequency oscillations (80-125Hz).

## Requirements
- **Hardware**: Muse S, Muse 2, or Muse (2014/2016).
- **Software**: 
  - [Mind Monitor](https://mind-monitor.com/) (Mobile App) or [MuseLSL](https://github.com/alexandrebarachant/muse-lsl).
  - Python 3.8+
  - Dependencies: `numpy`, `scipy`, `python-osc`

## Usage
1. Connect your Muse headband to your mobile device via Mind Monitor.
2. Set the OSC Stream IP in Mind Monitor to your computer's local IP and port `5239`.
3. Run the detector:
   ```bash
   python epilepsy_detector.py
   ```
4. Send **Marker 1** to start monitoring/recording and **Marker 2** to stop.

## Configuration
Edit `epilepsy_detector.py` to adjust thresholds:
- `SPIKE_Z_THRESH`: Sensitivity for spike detection.
- `ALERT_THRESHOLD`: Number of concurrent patterns required to trigger a high-level alert.
