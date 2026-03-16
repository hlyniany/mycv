#!/bin/bash
# Extract CV data from HTML file and convert to JSONResume format
# Initial extraction - adds IT domain to all entries by default

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python not found"
    exit 1
fi

echo "Running HTML to JSONResume extraction..."
$PYTHON_CMD scripts/read_html_initial.py

echo ""
echo "✓ Extraction complete!"
echo "✓ Review the output in: review/cv.resume.json"
echo "✓ Modify domains as needed, then use the data/cv.resume.json for generation"
