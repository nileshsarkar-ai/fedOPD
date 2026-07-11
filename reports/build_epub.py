#!/usr/bin/env python3
"""Build reports/eda_report.epub from the LaTeX source.

Why this script exists rather than a bare `pandoc eda_report.tex -o eda_report.epub`:
pandoc's LaTeX reader drops cleveref's "Table"/"Figure" prefix (so `\\Cref{tab:ledger}`
renders as a bare "4") and it does not number float captions. Both make the flowing EPUB
text read as broken. So we take the authoritative label -> (type, number) map from LaTeX's
own `.aux` file, rewrite every cross-reference and number every caption, and only then hand
the source to pandoc.

Requires tectonic (to emit the .aux) and pandoc:
    pip install pypandoc_binary          # bundles a pandoc binary
Run:
    python reports/build_epub.py         # or: make -C reports epub
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "eda_report.tex")
AUX = os.path.join(HERE, "eda_report.aux")
EPUB = os.path.join(HERE, "eda_report.epub")
CSS = os.path.join(HERE, "epub.css")

WORD = {"table": "Table", "figure": "Figure", "section": "Section",
        "subsection": "Section", "subsubsection": "Section", "appendix": "Appendix"}


def find_pandoc():
    p = shutil.which("pandoc")
    if p:
        return p
    try:
        import pypandoc
        return pypandoc.get_pandoc_path()
    except Exception:
        sys.exit("pandoc not found -- `pip install pypandoc_binary`")


def find_tectonic():
    return shutil.which("tectonic") or os.path.expanduser("~/.local/bin/tectonic")


def ensure_aux():
    """LaTeX must run once so the .aux carries every label's type and number."""
    tectonic = find_tectonic()
    if not os.path.exists(tectonic):
        sys.exit("tectonic not found -- needed to generate the .aux label map")
    subprocess.run([tectonic, "--keep-intermediates", TEX], cwd=HERE, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load_labels():
    """cleveref writes `\\newlabel{lbl@cref}{{[type][n][]printed}...}` -- the type lives there."""
    aux = open(AUX, encoding="utf-8", errors="ignore").read()
    return {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(
        r"\\newlabel\{([^}]+)@cref\}\{\{\[(\w+)\]\[[^\]]*\]\[[^\]]*\]([^}]*)\}", aux)}


def rewrite(tex, labels):
    float_re = re.compile(r"\\begin\{(table|figure|longtable)\}.*?\\end\{\1\}", re.S)

    def number_caption(m):                       # "Table 4. <caption text>"
        blk = m.group(0)
        lm = re.search(r"\\label\{([^}]+)\}", blk)
        if not lm or lm.group(1) not in labels:
            return blk
        typ, num = labels[lm.group(1)]
        return blk.replace("\\caption{",
                           "\\caption{\\textbf{%s %s.} " % (WORD.get(typ, typ.title()), num), 1)

    def xref(m):                                 # \Cref{tab:x} -> "Table 4"
        cmd, lbl = m.group(1), m.group(2)
        if lbl not in labels:
            return m.group(0)
        typ, num = labels[lbl]
        w = WORD.get(typ, typ.title())
        if cmd == "Cref":
            return f"{w}~{num}"
        if cmd == "cref":
            return f"{w.lower()}~{num}"
        return num                               # bare \ref: the prose already says "Section"

    tex, n_caps = float_re.subn(number_caption, tex)
    tex, n_refs = re.subn(r"\\(Cref|cref|ref)\{([^}]+)\}", xref, tex)
    print(f"numbered {n_caps} captions | rewrote {n_refs} cross-references")
    return tex


STYLESHEET = """\
body { font-family: serif; line-height: 1.5; margin: 0.6em; }
h1, h2, h3, h4 { font-family: sans-serif; line-height: 1.25; }
h1 { page-break-before: always; }
code { font-family: monospace; font-size: 0.9em; }
img { max-width: 100%; height: auto; }
figure { margin: 1.2em 0; text-align: center; page-break-inside: avoid; }
figcaption { font-size: 0.85em; text-align: left; margin-top: 0.4em; color: #333; }
table { border-collapse: collapse; margin: 1em auto; font-size: 0.8em; width: 100%; }
caption { font-size: 0.85em; text-align: left; margin-bottom: 0.4em; caption-side: top; }
th, td { padding: 0.28em 0.5em; text-align: left; vertical-align: top; }
thead th { border-top: 1.5px solid #000; border-bottom: 1px solid #000; }
tbody tr:last-child td { border-bottom: 1.5px solid #000; }
"""


def main():
    ensure_aux()
    labels = load_labels()
    print(f"resolved {len(labels)} labels from {os.path.basename(AUX)}")

    src = os.path.join(HERE, ".eda_report_epub.tex")     # transient, gitignored
    open(src, "w", encoding="utf-8").write(rewrite(open(TEX, encoding="utf-8").read(), labels))
    open(CSS, "w").write(STYLESHEET)

    subprocess.run([
        find_pandoc(), src, "-o", EPUB,
        "--standalone", "--toc", "--toc-depth=2", "--mathml",
        f"--resource-path={HERE}", "--css", CSS,
        "--metadata", "title=Exploratory Data Analysis of NHS England Referral-to-Treatment Demand",
        "--metadata", "subtitle=A Data Foundation for Cross-Silo Federated Demand Forecasting",
        "--metadata", "author=Nilesh Sarkar",
        "--metadata", "lang=en",
        "--metadata", "publisher=fedOPD",
    ], check=True)

    # pandoc embeds the stylesheet into the .epub, so none of these need to survive
    for f in ("eda_report.aux", "eda_report.log", "eda_report.out", "eda_report.toc",
              ".eda_report_epub.tex", "epub.css"):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            os.remove(p)

    print(f"wrote {EPUB} ({os.path.getsize(EPUB) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
