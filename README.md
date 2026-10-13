# Hexagon LLM analysis

Which LLM / AI assistants are behind works in the [Hexagon](https://hexagonmath.org/)
mathematics archive? A reproducible scan of its public API, counting models from both
the structured tool declarations and the free-text provenance statements.

Read the report: **[winstoncheong.github.io/hexagon-llm-analysis](https://winstoncheong.github.io/hexagon-llm-analysis/)** (`hexagon-llm-models.html` also works standalone).

## Reproduce

Stdlib-only Python, no dependencies.

```sh
python scan_hexagon.py        # catalogue + per-work detail records -> data/
python analyze_hexagon.py     # normalize + count -> data/hexagon_analysis.json
python render_hexagon_report.py   # rewrite the report body from the analysis JSON
```

Headline (snapshot 2026-10-13, 139 works): 89 works (64.0%) name an LLM in the
structured tools field; mining provenance prose raises this to 120 (86.3%).
OpenAI ChatGPT 56 structured / 96 combined, Codex 28 / 35, Anthropic Claude
Opus 24 / 36. The `modelMaker`-style free text uses 101 distinct spellings for
13 canonical families; matched spans are kept per work (`prov_spans`) for audit.

## Layout

- `scan_hexagon.py` — paginated `/api/v1/works` fetch + per-work detail records.
- `analyze_hexagon.py` — normalization, counts, co-occurrence, subject cross-tabs,
  provenance mining (`PROV_PATTERNS`).
- `render_hexagon_report.py` — rebuilds only the report body from the analysis JSON.
- `data/` — committed snapshots + analysis so figures reproduce offline.
- `hexagon-llm-models.html` — the report. Every number is generated; don't hand-edit.

## Data and license

Code: MIT (see `LICENSE`). Data: titles, abstracts, and tool metadata belong to
their depositors via the [Hexagon](https://hexagonmath.org/about) record pages
(works carry CC BY 4.0 / CC BY-SA 4.0 / CC0 1.0 licenses); snapshots are
attributed to the Hexagon Mathematics Foundation and link each work to its
record. Re-run `scan_hexagon.py` for a fresh snapshot.
