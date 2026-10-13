# AGENTS.md — hexagon-llm-analysis

Reproducible scan of LLM/AI model use in the Hexagon math archive
(https://hexagonmath.org/). Stdlib-only Python; no dependencies.

## Pipeline (in order)

```sh
python scan_hexagon.py        # catalogue + per-work detail records -> data/
python analyze_hexagon.py     # normalize + count -> data/hexagon_analysis.json
python render_hexagon_report.py   # rewrite the report body from the analysis JSON
```

## Rules

- Every number in `hexagon-llm-models.html` is generated. Never hand-edit figures;
  change `analyze_hexagon.py` or `render_hexagon_report.py` and re-render.
- `render_hexagon_report.py` replaces only the region between `<!-- NOTE BODY -->`
  and `</article>`. Never touch the managed head (stylesheet, theme, KaTeX glue).
- After rendering, open the HTML in a browser: all math must render (no red
  literal `\commands`, no `.katex-error`). Math lives in text nodes as
  `$…$`/`\(…\)`, never inside `<code>` (use `<code class="no-katex">` for literals).
- Bar charts: the SVG `viewBox` must fit the longest value label — labels sit past
  the bar end, and a fixed-width box clips the maximum bar's number (seen before).
- The API rejects bare requests (HTTP 403); `scan_hexagon.py` sends a browser-like
  `User-Agent`. It paginates with `cursor`, then fetches each work's detail record
  for its provenance statement (~139 requests, be patient).
- Data discipline: the dated snapshot (`data/hexagon_works_<date>.json`,
  `data/hexagon_details_<date>.json`) is the artifact of record — commit it, never
  edit it. `*_latest.json` is the pipeline's working copy.
- Provenance mining is regex-based (`PROV_PATTERNS` in `analyze_hexagon.py`).
  Matched spans are kept per work as `prov_spans` — audit them after any pattern
  change; bare words like "opus"/"sage" are false-positive traps and need context.
- Commit messages: short summary line; no secrets in repo (`.gitignore` covers
  `__pycache__`).
