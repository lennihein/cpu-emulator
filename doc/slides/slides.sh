#!/bin/bash

set -eu
cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

pandoc -o slides.pdf slides.md -t beamer --highlight-style=tango --pdf-engine xelatex --slide-level 2

# Metropolis theme: https://github.com/matze/mtheme
