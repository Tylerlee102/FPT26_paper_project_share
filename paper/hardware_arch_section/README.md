# Hardware Architecture Section Preview

This folder contains a standalone IEEE-style LaTeX file for only the Hardware
Architecture section:

- `hardware_architecture_section.tex`

To compile with MiKTeX or TeX Live:

```powershell
pdflatex -interaction=nonstopmode hardware_architecture_section.tex
pdflatex -interaction=nonstopmode hardware_architecture_section.tex
```

Expected output:

- `hardware_architecture_section.pdf`

The current environment did not expose `pdflatex`, `xelatex`, `lualatex`,
`latexmk`, or `tectonic` on PATH, so a true LaTeX compile could not be completed
here. A PDF preview generated from the same section text is included as
`hardware_architecture_section_preview.pdf`.
