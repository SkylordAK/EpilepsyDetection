import sys
import os
import csv
from datetime import datetime
import numpy as np
from scipy.signal import butter, filtfilt, welch, find_peaks, iirnotch
from scipy.stats import zscore

# ──────────────────────── CONFIG ────────────────────────
FS = 256
CHANNELS = 4
CH_NAMES = ['TP9', 'AF7', 'AF8', 'TP10']
WINDOW_SEC = 2
OVERLAP = 0.5
WINDOW_SAMPLES = int(FS * WINDOW_SEC)
STEP_SAMPLES = int(WINDOW_SAMPLES * (1 - OVERLAP))

SPIKE_Z_THRESH = 5.0  # Increased from 3.5 to reduce sensitivity to small transients
SPIKE_WAVE_HZ = 3.0
SPIKE_WAVE_TOL = 0.5
ALERT_THRESHOLD = 4   # Increased from 3 to require more evidence
HFO_POWER_THRESH = 10.0 # Significantly increased from 0.5 based on observed noise
DELTA_RATIO_THRESH = 5.0 # Increased from 2.0

# Band definitions (Hz)
BANDS = {
    'delta': (0.5, 4),
    'theta': (4, 8),
    'alpha': (8, 13),
    'beta':  (13, 30),
    'gamma': (30, 100),
    'hfo':   (80, 125),  # limited by Nyquist at 256 Hz
}


def bandpass(data, low, high, fs=FS, order=4):
    nyq = fs / 2.0
    low_n = max(low / nyq, 0.001)
    high_n = min(high / nyq, 0.999)
    b, a = butter(order, [low_n, high_n], btype='band')
    return filtfilt(b, a, data, axis=0)


def notch_filter(data, f0=60.0, fs=FS, Q=30.0):
    b, a = iirnotch(f0, Q, fs)
    return filtfilt(b, a, data, axis=0)


def band_power(data, low, high, fs=FS):
    freqs, psd = welch(data, fs=fs, nperseg=min(len(data), 256), axis=0)
    mask = (freqs >= low) & (freqs <= high)
    return np.trapezoid(psd[mask], freqs[mask], axis=0)


def analyze_window(window):
    """
    Analyze a (WINDOW_SAMPLES, CHANNELS) EEG window.
    Returns dict of detected patterns and band powers.
    """
    results = {
        'patterns': [],
        'band_powers': {},
        'severity': 0,
    }

    # ── Band Powers ──
    for name, (lo, hi) in BANDS.items():
        if hi >= FS / 2:
            hi = FS / 2 - 1
        results['band_powers'][name] = band_power(window, lo, hi)

    bp = results['band_powers']

    # ── 1. High-Amplitude Spike Detection (Z-score) ──
    z = zscore(window, axis=0)
    spike_mask = np.abs(z) > SPIKE_Z_THRESH
    spike_count = spike_mask.sum()
    if spike_count > 0:
        results['patterns'].append(f'HIGH_AMPLITUDE_SPIKE (count={spike_count})')
        results['severity'] += 1

    # ── 2. Spike-and-Wave (3 Hz) Detection ──
    for ch in range(CHANNELS):
        filtered = bandpass(window[:, ch], 1, 7)
        peaks, _ = find_peaks(filtered, height=np.std(filtered) * 1.0, distance=int(FS * 0.15))
        if len(peaks) >= 3:
            intervals = np.diff(peaks) / FS
            mean_freq = 1.0 / np.mean(intervals) if np.mean(intervals) > 0 else 0
            if abs(mean_freq - SPIKE_WAVE_HZ) < SPIKE_WAVE_TOL:
                results['patterns'].append(f'SPIKE_WAVE_3HZ (ch={CH_NAMES[ch]}, freq={mean_freq:.1f}Hz)')
                results['severity'] += 2
                break

    # ── 3. Delta Dominance (post-ictal slowing) ──
    delta_p = np.mean(bp['delta'])
    alpha_beta_p = np.mean(bp['alpha']) + np.mean(bp['beta'])
    if alpha_beta_p > 0:
        ratio = delta_p / alpha_beta_p
        if ratio > DELTA_RATIO_THRESH:
            results['patterns'].append(f'DELTA_DOMINANCE (ratio={ratio:.1f})')
            results['severity'] += 1

    # ── 4. Beta/Gamma Burst ──
    gamma_p = np.mean(bp['gamma'])
    beta_p = np.mean(bp['beta'])
    baseline_power = np.mean(bp['alpha']) + np.mean(bp['theta'])
    if baseline_power > 0 and (gamma_p + beta_p) / baseline_power > 8.0 and (gamma_p + beta_p) > 200:
        results['patterns'].append('BETA_GAMMA_BURST')
        results['severity'] += 1

    # ── 5. Rhythmic Theta Burst ──
    for ch in range(CHANNELS):
        theta_sig = bandpass(window[:, ch], 4, 8)
        peaks_t, _ = find_peaks(theta_sig, height=np.std(theta_sig) * 1.5, distance=int(FS * 0.1))
        if len(peaks_t) >= 4:
            intervals_t = np.diff(peaks_t) / FS
            cv = np.std(intervals_t) / np.mean(intervals_t) if np.mean(intervals_t) > 0 else 999
            if cv < 0.3:
                results['patterns'].append(f'RHYTHMIC_THETA (ch={CH_NAMES[ch]})')
                results['severity'] += 1
                break

    # ── 6. HFO Detection ──
    hfo_p = np.mean(bp.get('hfo', [0]))
    if hfo_p > HFO_POWER_THRESH:
        results['patterns'].append(f'HFO_DETECTED (power={hfo_p:.3f})')
        results['severity'] += 2

    return results


def print_dashboard(results, window_num):
    """Print a color-coded console dashboard."""
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    sev = results['severity']
    if sev >= ALERT_THRESHOLD:
        color = RED
        status = '⚠  ALERT — ABNORMAL ACTIVITY'
    elif sev >= 1:
        color = YELLOW
        status = '⚡ ELEVATED — Patterns Detected'
    else:
        color = GREEN
        status = '✓  NORMAL'

    print(f"\n{BOLD}{'═' * 55}{RESET}")
    print(f"{BOLD} Window #{window_num} {color}{status}{RESET}")
    print(f"{'─' * 55}")

    bp = results['band_powers']
    print(f" {CYAN}Band Powers (avg across channels):{RESET}")
    for name in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
        val = np.mean(bp[name])
        print(f"   {name:<8} {val:>10.2f} µV²/Hz")

    if results['patterns']:
        print(f"\n {color}{BOLD}Detected Patterns (severity={sev}):{RESET}")
        for p in results['patterns']:
            print(f"   {color}● {p}{RESET}")
    else:
        print(f"\n {GREEN}No abnormal patterns detected.{RESET}")

    print(f"{'═' * 55}")


# ──────────────── SELF-TEST WITH SYNTHETIC DATA ─────────────────
def run_smoke_test():
    """Generate synthetic EEG with known patterns and verify detection."""
    print("=" * 55)
    print("  SMOKE TEST — Synthetic Epilepsy Patterns")
    print("=" * 55)

    t = np.linspace(0, WINDOW_SEC, WINDOW_SAMPLES, endpoint=False)
    window = np.random.randn(WINDOW_SAMPLES, CHANNELS) * 5  # baseline noise

    # Inject 3 Hz spike-and-wave on channel 0
    spike_wave = np.zeros(WINDOW_SAMPLES)
    for freq_comp in [3.0]:
        spike_wave += 80 * np.sin(2 * np.pi * freq_comp * t)
        spike_wave += 40 * np.sign(np.sin(2 * np.pi * freq_comp * t))
    window[:, 0] += spike_wave

    # Inject high-amplitude spikes on channel 1
    spike_positions = [100, 200, 350, 450]
    for pos in spike_positions:
        if pos < WINDOW_SAMPLES:
            window[pos, 1] += 300

    results = analyze_window(window)
    print_dashboard(results, 0)

    patterns_str = ' '.join(results['patterns'])
    passed = True

    if 'HIGH_AMPLITUDE_SPIKE' not in patterns_str:
        print("\n❌ FAIL: HIGH_AMPLITUDE_SPIKE not detected!")
        passed = False
    else:
        print("\n✅ PASS: HIGH_AMPLITUDE_SPIKE detected")

    if 'SPIKE_WAVE' not in patterns_str:
        print("❌ FAIL: SPIKE_WAVE_3HZ not detected!")
        passed = False
    else:
        print("✅ PASS: SPIKE_WAVE_3HZ detected")

    if results['severity'] >= ALERT_THRESHOLD:
        print("✅ PASS: Alert triggered (severity >= threshold)")
    else:
        print(f"⚠  NOTE: Severity={results['severity']}, threshold={ALERT_THRESHOLD}")

    print(f"\n{'=' * 55}")
    if passed:
        print("  ALL CRITICAL TESTS PASSED ✅")
    else:
        print("  SOME TESTS FAILED ❌")
    print(f"{'=' * 55}")
    return passed


# ──────────────── LIVE OSC MODE ─────────────────
def run_live():
    from pythonosc import dispatcher, osc_server
    from timeit import default_timer as timer

    ip = '0.0.0.0'
    port = 5239

    # State for processing
    buffer = np.empty((0, CHANNELS))
    recording = False
    window_count = [0]
    alert_accumulator = [0]
    
    # State for logging
    log_dir = "Sessions"
    os.makedirs(log_dir, exist_ok=True)
    session_f = [None]  # Using list to make it mutable in nested scope
    csv_writer = [None]
    
    # "Silver Labels" from the detector to be logged with raw data
    active_patterns = ["None"]
    active_severity = [0]

    def eeg_handler(address, *args):
        nonlocal buffer, recording, active_patterns, active_severity
        if not recording:
            return
            
        sample_vals = args[:CHANNELS]
        sample = np.array(sample_vals).reshape(1, CHANNELS)
        buffer = np.vstack([buffer, sample])
        
        # Log to CSV if session is active
        if csv_writer[0]:
            try:
                patterns_str = "|".join(active_patterns) if active_patterns else "None"
                csv_writer[0].writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    *sample_vals,
                    patterns_str,
                    active_severity[0]
                ])
            except Exception as e:
                print(f"Logging error: {e}")

        if buffer.shape[0] >= WINDOW_SAMPLES:
            window = buffer[:WINDOW_SAMPLES]
            buffer = buffer[STEP_SAMPLES:]
            
            # Apply Notch and Bandpass pre-processing
            processed_window = notch_filter(window, f0=60.0)
            processed_window = notch_filter(processed_window, f0=50.0) # Catch both 50/60Hz
            
            window_count[0] += 1

            results = analyze_window(processed_window)
            
            # Update labels for logging
            active_patterns = results['patterns'] if results['patterns'] else ["None"]
            active_severity[0] = results['severity']
            
            print_dashboard(results, window_count[0])

            if results['severity'] >= ALERT_THRESHOLD:
                alert_accumulator[0] += 1
                if alert_accumulator[0] >= 3:
                    print(f"\n\033[91m\033[1m{'!' * 55}")
                    print("  SUSTAINED ALERT — MULTIPLE ABNORMAL WINDOWS")
                    print(f"{'!' * 55}\033[0m\n")
            else:
                alert_accumulator[0] = max(0, alert_accumulator[0] - 1)

    def marker_handler(address, i):
        nonlocal recording, buffer, active_patterns, active_severity
        marker = address[-1]
        if marker == "1":
            recording = True
            buffer = np.empty((0, CHANNELS))
            window_count[0] = 0
            alert_accumulator[0] = 0
            active_patterns = ["None"]
            active_severity[0] = 0
            
            # Start a new logging session
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(log_dir, f"session_{timestamp}.csv")
            session_f[0] = open(filename, 'w', newline='')
            csv_writer[0] = csv.writer(session_f[0])
            csv_writer[0].writerow(['timestamp', 'TP9', 'AF7', 'AF8', 'TP10', 'patterns', 'severity'])
            
            print(f"\n🟢 Monitoring STARTED — Logging to: {filename}\n")
            
        elif marker == "2":
            recording = False
            if session_f[0]:
                session_f[0].close()
                session_f[0] = None
                csv_writer[0] = None
            print("\n🔴 Monitoring STOPPED.\n")
            server.shutdown()

    disp = dispatcher.Dispatcher()
    disp.map("/muse/eeg", eeg_handler)
    disp.map("/eeg", eeg_handler)
    disp.map("/Marker/*", marker_handler)

    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print("=" * 55)
    print("  EPILEPSY DETECTION — Real-Time Pattern Monitor")
    print("=" * 55)
    print(f"Listening on UDP port {port}")
    print("Send Marker 1 to START, Marker 2 to STOP.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting...")


# ──────────────── ENTRY POINT ─────────────────
if __name__ == "__main__":
    if '--test' in sys.argv:
        success = run_smoke_test()
        sys.exit(0 if success else 1)
    else:
        run_live()
