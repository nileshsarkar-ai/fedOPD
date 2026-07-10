# Build the fedOPD EDA report PDF.
#
# The .tex is self-contained and uses only standard packages, so any LaTeX
# toolchain works. Two easy routes:
#
#   1) tectonic (single static binary, no system TeX install, no root):
#        make pdf
#   2) a full TeX Live / MiKTeX install:
#        make pdf-pdflatex
#   3) zero-install: upload eda_report.tex + the figures/ folder to Overleaf.
#
REPORT = eda_report

pdf:
	tectonic $(REPORT).tex

# pdflatex needs two passes so cleveref/hyperref cross-references resolve.
pdf-pdflatex:
	pdflatex -interaction=nonstopmode -halt-on-error $(REPORT).tex
	pdflatex -interaction=nonstopmode -halt-on-error $(REPORT).tex

clean:
	rm -f $(REPORT).aux $(REPORT).log $(REPORT).out $(REPORT).toc $(REPORT).lof $(REPORT).lot

.PHONY: pdf pdf-pdflatex clean
