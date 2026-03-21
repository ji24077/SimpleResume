# Optional LaTeX project files

Place extra files that `\input{...}` or `\includegraphics` need **in the same directory as `resume.tex`** during compile.

Examples:

- `glyphtounicode.tex` — only if your TeX install does not ship it (TeX Live full Docker includes it in texmf).
- Custom `.sty`, `.cls`, images (`.png`, `.jpg`), `.bib`

The API copies non-hidden files with these extensions into the compile temp directory before running `latexmk` / fallback engines.
