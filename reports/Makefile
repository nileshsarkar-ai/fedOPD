# Build the fedOPD EDA report.
#
#   make pdf    -> eda_report.pdf   (tectonic; no system TeX install, no root)
#   make epub   -> eda_report.epub  (pandoc, via build_epub.py)
#   make all    -> both
#
# One-time tooling (both user-space, no root):
#   curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh   # tectonic
#   pip install pypandoc_binary                                                     # pandoc
#
# Note: on glibc < 2.36 the latest tectonic will not run; use the 0.15.0 build,
# which requires only glibc 2.35.
#
# Zero-install alternative for the PDF: upload eda_report.tex + figures/ to Overleaf.
#
REPORT = eda_report

all: pdf epub

pdf:
	tectonic $(REPORT).tex

# pdflatex needs two passes so cleveref/hyperref cross-references resolve.
pdf-pdflatex:
	pdflatex -interaction=nonstopmode -halt-on-error $(REPORT).tex
	pdflatex -interaction=nonstopmode -halt-on-error $(REPORT).tex

# build_epub.py reads LaTeX's .aux for the label->number map, so cleveref refs
# ("Table 4") and float captions survive the conversion. It cleans up after itself.
epub:
	python build_epub.py

clean:
	rm -f $(REPORT).aux $(REPORT).log $(REPORT).out $(REPORT).toc $(REPORT).lof $(REPORT).lot epub.css .$(REPORT)_epub.tex

.PHONY: all pdf pdf-pdflatex epub clean
