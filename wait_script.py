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
import argparse
import sys
import os

# Parse command line arguments
parser = argparse.ArgumentParser(description='Wait script with countdown')
parser.add_argument('--config', type=str, help='Path to config file')
args = parser.parse_args()

# Determine config file path
if args.config:
    config_path = Path(args.config)
else:
    # Fallback to default location
    config_path = Path(__file__).parent / 'wait_script_config.yml'

print(f"Loading config from: {config_path}", flush=True)
print(f"Config exists: {config_path.exists()}", flush=True)

# Load configuration
try:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if config is None:
        print("Warning: Config file is empty, using defaults", flush=True)
        config = {}
        
    print(f"Config loaded successfully: {config}", flush=True)
except Exception as e:
    print(f"Error loading config: {e}", flush=True)
    print(f"Using default values", flush=True)
    config = {}

countdown_seconds = int(float(config.get('countdown_seconds', 10)))  # Convert to float first, then int

print(f"Starting {countdown_seconds}-second countdown...", flush=True)

for i in range(1, countdown_seconds + 1):
    print(f"Alert: {i} second(s) elapsed", flush=True)
    time.sleep(1)

print(f"{countdown_seconds} seconds completed. Exiting...", flush=True)
