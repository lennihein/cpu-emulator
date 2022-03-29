#!/bin/bash

cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

set -u

# all *.md files
SOURCES=(*.md)
# output file for thesis
OUT="lab.pdf"
# directory to build in
BUILD="build"

# options for pandoc
FLAGS_PANDOC=(--template tpl/pandoc_template.tex \
    --listings --top-level-division chapter --columns 1000 \
    --filter pandoc-crossref \
    --metadata listings --metadata codeBlockCaptions \
    --bibliography bibliography.bib --biblatex)
# options for latexmk
FLAGS_LATEXMK=(-silent -Werror -outdir="$BUILD" -lualatex -halt-on-error)

# location of tex file in build/
BUILD_TEX="$BUILD/main.tex"
# location of pdf file in build/
BUILD_PDF="${BUILD_TEX/%.tex/.pdf}"

main () {
    # build tex from markdown using pandoc
    mkdir -p "$BUILD"
    run_log pandoc "${FLAGS_PANDOC[@]}" -o "$BUILD_TEX" "${SOURCES[@]}"

    # center tables and restore default spacing
    run_log sed -i 's/\\begin{longtable}\[\]{@{}\([^}]*\)@{}}/\\begin{longtable}\[c\]{\1}/g' "$BUILD_TEX"

    # float tables
    #run_log sed -i 's/\\begin{longtable}/\\begin{table}\[tbp\]\\begin{longtable}/g' "$BUILD_TEX"
    #run_log sed -i 's/\\end{longtable}/\\end{longtable}\\end{table}/g' "$BUILD_TEX"

    # build pdf from tex using latexmk
    run_log latexmk "${FLAGS_LATEXMK[@]}" "$BUILD_TEX"
 
    # copy pdf to output
    run_log cp "$BUILD_PDF" "$OUT"
}

run_log () {
    # print command and execute it

    echo "$*" >&2
    "$@" || exit
}

main "$@"
