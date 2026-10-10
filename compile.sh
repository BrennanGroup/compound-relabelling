#!/bin/bash

OUTPUT_DIR="build"
SRC_FILE="main.tex"
OUT_FILE="main.pdf"
SCRIPT_DIR="scripts"

mkdir -p "$OUTPUT_DIR"

# Relabel all .cdxmls and export them as pdfs
echo "Running ChemDraw relabelling utility..."
python3 "$SCRIPT_DIR/relabel_cdxmls.py"
osascript "$SCRIPT_DIR/cdxml2pdf.applescript"

# Run latex compilation passes
pdflatex -output-directory="$OUTPUT_DIR" -interaction=nonstopmode "$SRC_FILE"
pdflatex -output-directory="$OUTPUT_DIR" -interaction=nonstopmode "$SRC_FILE"
pdflatex -output-directory="$OUTPUT_DIR" -interaction=nonstopmode "$SRC_FILE"
