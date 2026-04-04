# Golden / regression inputs

Place stable sample resumes here for automated checks (e.g. fixed expected scores or API snapshot hashes).

Suggested layout (team adds binaries as needed):

```
tests/golden/
  README.md
  resume1.pdf
  resume2.tex
  resume3.png
```

**Policy:** Changing golden inputs or expected outputs should be intentional and reviewed. CI can later run `assert score_or_hash == expected` with documented tolerance only when approved.
