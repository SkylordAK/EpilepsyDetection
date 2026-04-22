"""
EEG Recorder for Epilepsy Detection
Records labelled raw EEG from the Muse S during different states.
Reuses the OSC recording pattern from MotorImagery_OSC_Record.py.

Usage:
  1. Connect Muse S via Mind Monitor / MuseLSL
  2. Run this script
  3. Send Marker 1 to start recording, Marker 2 to stop
"""

from datetime import datetime
from pythonosc import dispatcher
from pythonosc import osc_server
from timeit import default_timer as timer
import os

# ──────────────────────── CONFIG ────────────────────────
ip = '0.0.0.0'
port = 5239
filePath = r'Recordings/'
WARMUP_SECS = 5

# Recording schedule: label → duration (seconds)
rec_dict = {
    "break0":  10,
    "NORMAL":  60,
    "break1":  10,
    "SEIZURE": 60,
    "break2":  10,
    "EPILEPSY": 60,
    "break3":  10,
    "NORMAL2": 60,
    "break4":  10,
}

# ──────────────────────── STATE ─────────────────────────
recording = False
initial_reading = 1
row = 1
current_event = 0
start = timer()
end = timer()
secs = WARMUP_SECS
lock = False
header = 'timestamp,RAW_TP9,RAW_AF7,RAW_AF8,RAW_TP10\n'
filename_array = []

# Ensure output directory exists
os.makedirs(filePath, exist_ok=True)

# Initial warmup file
dateTimeObj = datetime.now()
timestampStr = dateTimeObj.strftime("%Y-%m-%d %H_%M_%S.%f")
ev = 'Warmup'
current_file = filePath + ev + '.' + timestampStr + '.csv'
try:
    f = open(current_file, 'a+')
except Exception:
    f = open(current_file, 'w')
    f = open(current_file, 'a+')


def eeg_handler(address: str, *args):
    global recording, initial_reading, row, header, current_event
    global start, end, secs, f, lock, filename_array

    if recording:
        if initial_reading == 1:
            initial_reading = 0
            start = timer()
            f.write(header)
            print(f"Warmup \t{secs}  seconds")
        else:
            end = timer()
            if (end - start) >= secs and lock is False:
                lock = True
                f.close()
                row = 1

                dateTimeObj = datetime.now()
                timestampStr = dateTimeObj.strftime("%Y-%m-%d %H_%M_%S.%f")
                ev = list(rec_dict.items())[current_event][0]
                secs = list(rec_dict.items())[current_event][1]
                current_file = filePath + ev + '.' + timestampStr + '.csv'
                filename_array.append(current_file)
                f = open(current_file, 'a+')
                f.write(header)
                start = timer()
                print(f"Recording:\t {ev}   \t\t{secs}  seconds")

                dict_length = len(rec_dict)
                if current_event < dict_length - 1:
                    current_event += 1
                else:
                    current_event = 0

                lock = False
            else:
                if lock is False:
                    fileString = str(row)
                    row += 1
                    for i in range(0, 4):
                        fileString += "," + str(args[i])
                    fileString += "\n"
                    f.write(fileString)


def marker_handler(address: str, i):
    global recording, start, f, server

    markerNum = address[-1]

    if markerNum == "1":
        recording = True
        start = timer()
        print("Recording Started.")

    if markerNum == "2":
        f.close()
        recording = False
        server.shutdown()
        print("Recording Stopped.")
        print(f"Files saved: {filename_array}")


if __name__ == "__main__":
    disp = dispatcher.Dispatcher()
    disp.map("/muse/eeg", eeg_handler)
    disp.map("/eeg", eeg_handler)
    disp.map("/Marker/*", marker_handler)

    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print("=" * 60)
    print("  EPILEPSY DETECTION — EEG Recorder")
    print("=" * 60)
    print(f"Listening on UDP port {port}")
    print("Send Marker 1 to START recording, Marker 2 to STOP.")
    print(f"\nRecording schedule:")
    for label, duration in rec_dict.items():
        print(f"  {label:<15} {duration}s")
    print()
    server.serve_forever()
