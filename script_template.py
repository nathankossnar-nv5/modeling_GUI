"""Your Script Description Here

INPUTS:
- List your input parameters

OUTPUTS:
- Describe what outputs are created
"""

import argparse
import sys


def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Your script description")
    
    # Add arguments - must match your YAML config file
    parser.add_argument('--input_folder', required=True, help='Input folder path')
    parser.add_argument('--output_folder', required=True, help='Output folder path')
    parser.add_argument('--threshold', type=float, default=0.5, help='Threshold value')
    parser.add_argument('--use_gpu', action='store_true', help='Enable GPU')
    
    args = parser.parse_args()
    
    # Print progress (appears in GUI)
    print("Starting processing...")
    print(f"Input: {args.input_folder}")
    print(f"Output: {args.output_folder}")
    
    # YOUR CODE HERE
    
    print("Complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
