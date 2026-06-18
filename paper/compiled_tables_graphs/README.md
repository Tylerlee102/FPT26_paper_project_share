# IEEE Tables Artifact

This folder contains a standalone IEEE-style LaTeX file:

- `ieee_tables_graphs.tex`

To compile it with MiKTeX or TeX Live, run:

```powershell
pdflatex -interaction=nonstopmode ieee_tables_graphs.tex
pdflatex -interaction=nonstopmode ieee_tables_graphs.tex
```

Expected output:

- `ieee_tables_graphs.pdf`

The current environment did not expose `pdflatex`, `xelatex`, `lualatex`,
`latexmk`, or `tectonic` on PATH, so the PDF could not be generated here.
