#!/usr/bin/env bash
# macOS / Linux launcher:  ./run.sh   (start the app)   ./run.sh test --quick   ./run.sh pipeline --input file.csv
cd "$(dirname "$0")"
exec python3 run.py "$@"
