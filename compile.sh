#!/bin/bash
set -euo pipefail

OUTPUT_DIR="build"
SRC_FILE="main.tex"
SCRIPT_DIR="scripts"

mkdir -p "$OUTPUT_DIR" "chemdraw/out"

command -v python3 >/dev/null || { echo "Error: python3 is required." >&2; exit 1; }
command -v osascript >/dev/null || { echo "Error: osascript is required (macOS only)." >&2; exit 1; }
command -v pdflatex >/dev/null || { echo "Error: pdflatex is required." >&2; exit 1; }

# Relabel CDXML files and export changed files as PDFs.
echo "Running ChemDraw relabelling utility..."
python3 "$SCRIPT_DIR/relabel_cdxmls.py"
osascript "$SCRIPT_DIR/cdxml2pdf.applescript"

# Run the LaTeX compilation passes required by the example document.
for pass in 1 2 3; do
    echo "Running pdflatex pass $pass/3..."
    pdflatex -halt-on-error -output-directory="$OUTPUT_DIR" -interaction=nonstopmode "$SRC_FILE"
done

echo "Build complete: $OUTPUT_DIR/main.pdf"
