"""
Wait Script with Interval Alerts

A simple demonstration script that waits for a configurable number of seconds
while displaying progress alerts at 1-second intervals.

Purpose:
    This script serves as a test/demonstration for subprocess execution monitoring
    in GUI applications. It provides real-time output that can be captured and
    displayed to show script progress.

Configuration:
    Reads countdown_seconds from wait_script_config.yml to determine how long
    to count down.

Output:
    Prints an alert message every second until the countdown completes, then exits.
    All print statements use flush=True to ensure immediate output buffering
    for real-time display in parent processes.
"""
import time
import yaml
from pathlib import Path

# Load configuration
config_path = Path(__file__).parent / 'wait_script_config.yml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

countdown_seconds = int(config.get('countdown_seconds', 10))  # Default to 10 if not specified, convert to int

print(f"Starting {countdown_seconds}-second countdown...", flush=True)

for i in range(1, countdown_seconds + 1):
    print(f"Alert: {i} second(s) elapsed", flush=True)
    time.sleep(1)

print(f"{countdown_seconds} seconds completed. Exiting...", flush=True)
