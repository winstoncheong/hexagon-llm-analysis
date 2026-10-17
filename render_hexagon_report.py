"""Render data/hexagon_analysis.json into hexagon-llm-models.html.

Reproducible: every number, table, and chart on the page is generated from
the analysis JSON. Re-run after re-scanning:

    python scan_hexagon.py      # refresh snapshot
    python analyze_hexagon.py   # rebuild analysis
    python render_hexagon_report.py   # rewrite the note body below

Only the region between the body anchor and the closing article tag is replaced; the
managed scaffold shell (head, theme, KaTeX glue) is never touched. After
rendering, open the HTML file in a browser to verify it renders.
"""

import html
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BODY_ANCHOR = "<!-- NOTE BODY -->"

BAR_COLORS = ["#0969da", "#6e40c9", "#1a7f37", "#9a6700", "#bc4c00",
              "#0e7490", "#59636e", "#d29922", "#4493f8", "#ab7df8",
              "#3fb950", "#db6d28", "#39c5cf"]


def esc(s):
    # Titles carry TeX ($...$); strip the sigils so KaTeX auto-render leaves
    # table cells alone, then escape.
    return html.escape((s or "").replace("$", ""))


def bars(rows, row_h=26, max_w=430, label_x=180, pad_right=56):
    """rows: [(label, value, color_idx)]. Returns an inline SVG bar chart.

    The viewBox grows to fit the longest value label: labels sit just past
    the bar end, so a fixed-width box clips the maximum bar's number.
    """
    top = 8
    h = top * 2 + row_h * len(rows)
    peak = max((v for _, v, _ in rows), default=1)
    # Fit the viewBox to the longest value label: labels sit just past the
    # bar end, so a fixed-width box clips the maximum bar's number.
    pad_right = max(pad_right, 8 * len(str(peak)) + 12)
    width = label_x + max_w + pad_right
    out = [f'<svg viewBox="0 0 {width} {h}" role="img" '
           f'aria-label="Bar chart">']
    for i, (label, value, ci) in enumerate(rows):
        y = top + i * row_h
        w = max(2, round(max_w * value / peak)) if peak else 2
        color = BAR_COLORS[ci % len(BAR_COLORS)]
        out.append(
            f'<text x="0" y="{y + 17}" font-size="13">{esc(label)}</text>'
            f'<rect x="{label_x}" y="{y + 2}" width="{w}" height="18" '
            f'style="fill:{color}"/>'
            f'<text x="{label_x + 4 + w}" y="{y + 17}" font-size="13" '
            f'class="muted">{value}</text>')
    out.append("</svg>")
    return "".join(out)


def main():
    a = json.loads((HERE / "data" / "hexagon_analysis.json").read_text(encoding="utf-8"))
    n = a["snapshot"]["n_works"]
    fetched = a["snapshot"]["fetched_at"]
    cov = a["coverage"]
    n_llm = cov["works_with_llm"]
    n_none = cov["works_no_tools"]
    n_comb = cov.get("works_with_llm_combined", n_llm)
    prov = a.get("provenance", {})
    gap = a.get("disclosure_gap", {})

    fam = a["family_works"]
    fams = {f["family"]: f for f in fam}
    top_fam = fam[:8]
    models = a["model_works"][:12]

    auth = a["authorshipMode"]
    und = a["humanUnderstanding"]
    co = a["cooccurrence"][:8]
    subj = a["subjects"]
    tools = a["non_llm_tools"]
    raw = a["raw_triples"]
    fam_map = {f["family"]: f for f in fam}
    co_lookup = {}
    for c in a.get("cooccurrence", []):
        co_lookup[(c["a"], c["b"])] = c["works"]
        co_lookup[(c["b"], c["a"])] = c["works"]
    co_oc = co_lookup.get(("Anthropic Claude Opus", "OpenAI ChatGPT"), 0)
    co_cc = co_lookup.get(("OpenAI ChatGPT", "OpenAI Codex"), 0)
    lean_works = tools["by_works"].get("Lean/Mathlib", 0)
    lean_llm = tools.get("works_also_listing_llm", {}).get("Lean/Mathlib", 0)
    bolzano = fam_map.get("Bolzano", {}).get("works", 0)
    harmonic = fam_map.get("Harmonic", {}).get("works", 0)
    claude_code = fam_map.get("Anthropic Claude Code", {}).get("works", 0)
    poe = fam_map.get("Quora Poe (aggregator)", {}).get("works", 0)
    danus_prov = fam_map.get("Danus", {}).get("prov_works", 0)
    axiom = fam_map.get("AxiomMath", {}).get("works", 0)
    xai = fam_map.get("xAI", {}).get("works", 0)
    google = fam_map.get("Google", {}).get("works", 0)
    local = fam_map.get("Local/open", {}).get("works", 0)
    moonshot = fam_map.get("Moonshot", {}).get("works", 0)
    meta = fam_map.get("Meta", {}).get("works", 0)
    blank_works = sum(
        1 for w in a.get("per_work", [])
        if any((r.rsplit("/", 1)[-1].strip() == "") for r in (w.get("raw_tools") or []))
    )
    big_labs = {"OpenAI ChatGPT", "OpenAI Codex", "Anthropic Claude Opus",
                "Anthropic Claude Fable", "Anthropic Claude Sonnet", "Anthropic Claude Code"}
    big_cover = sum(
        1 for w in a.get("per_work", [])
        if (set(w.get("llm_families", [])) | set(w.get("prov_llm_families", []))) & big_labs
    )
    any_model = sum(1 for w in a.get("per_work", [])
                    if w.get("llm_families") or w.get("prov_llm_families"))
    qa = next((s for s in subj if s["subject"] == "math.QA"),
              {"works": 0, "llm_works": 0, "prov_llm_works": 0})

    chatgpt = fams.get("OpenAI ChatGPT", {}).get("works", 0)
    codex = fams.get("OpenAI Codex", {}).get("works", 0)
    opus = fams.get("Anthropic Claude Opus", {}).get("works", 0)
    qa = next((s for s in subj if s["subject"] == "math.QA"),
              {"works": 0, "prov_llm_works": 0})

    def share(k):
        return f"{100.0 * k / n:.1f}" if n else "0.0"

    fam_rows = "".join(
        f"<tr><td>{esc(f['family'])}</td><td>{f['works']}</td>"
        f"<td>{f['pct_of_all']:.1f}</td><td>{f.get('prov_works', 0)}</td>"
        f"<td>{f.get('combined_works', f['works'])}</td>"
        f"<td>{f.get('combined_pct', f['pct_of_all']):.1f}</td></tr>"
        for f in fam)
    model_rows = "".join(
        f"<tr><td>{esc(m['model'])}</td><td>{esc(m['family'])}</td>"
        f"<td>{m['works']}</td><td>{m['pct_of_all']:.1f}</td>"
        f"<td>{m['mentions']}</td></tr>"
        for m in models)
    subj_rows = "".join(
        f"<tr><td><code class=\"no-katex\">{esc(s['subject'])}</code></td>"
        f"<td>{s['works']}</td><td>{s['llm_works']}</td>"
        f"<td>{s['llm_share_pct']:.1f}</td><td>{s.get('prov_llm_works', 0)}</td></tr>"
        for s in subj)
    co_rows = "".join(
        f"<tr><td>{esc(c['a'])}</td><td>{esc(c['b'])}</td>"
        f"<td>{c['works']}</td></tr>"
        for c in co)
    tool_with = tools.get("works_also_listing_llm", {})
    tool_prov = tools.get("prov_by_works", {})
    tool_rows = "".join(
        f"<tr><td>{esc(t)}</td><td>{c}</td>"
        f"<td>{tool_with.get(t, 0)}</td>"
        f"<td>{tool_prov.get(t, 0)}</td></tr>"
        for t, c in sorted(tools["by_works"].items(), key=lambda kv: -kv[1]))

    per_rows = "".join(
        f"<tr><td><a href=\"https://hexagonmath.org/abs/{esc(w['id'])}\">"
        f"{esc(w['id'])}</a></td>"
        f"<td><code class=\"no-katex\">{esc(w['subject'])}</code></td>"
        f"<td>{esc(w['authorshipMode'])}</td>"
        f"<td>{esc(w['humanUnderstanding'])}</td>"
        f"<td>{esc(', '.join(w['llm_families']) or '—')}</td>"
        f"<td>{esc(', '.join(w['prov_llm_families']) or '—')}</td>"
        f"<td>{esc(w['title'])}</td></tr>"
        for w in a["per_work"])

    body = f"""<h1>Hexagon archive: which AI models are used</h1>

<p class="meta"><span>snapshot {esc(fetched)}</span><span>{n} works</span><span>tags: math, ai-for-math</span><span>created: 2026-10-13</span><span>last updated {esc(fetched[:10])}</span></p>

<aside class="callout callout-note"><span class="callout-title">What this is</span>
<p>Hexagon (<a href="https://hexagonmath.org/">hexagonmath.org</a>) requires depositors to
declare the computational tools behind each work as free-text provider, name, and version
triples. This page scans the full public catalogue through the read-only
<code class="no-katex">/api/v1/works</code> endpoint and counts which LLM and AI assistants
show up. Work-share means the fraction of works listing a family at least once, with
\\(s = 100 \\cdot w / n\\) and \\(n = {n}\\). Re-run the three scripts in
the three scripts in this repo to refresh every
number below.</p></aside>

<h2 id="coverage">1. Coverage</h2>

<p>{n_llm} of {n} works ({share(n_llm)}%) name at least one LLM or AI assistant in the
structured tools field. Mining the free-text provenance statements (per-work detail
records) for the same canonical families raises this to {n_comb} works
({share(n_comb)}%): {gap.get("prov_llm_but_no_structured_llm", 0)} works name a model only
in prose. {n_none} works ({share(n_none)}%) disclose no tools at all. The raw declarations
use {a["n_raw_triples"]} distinct spellings, normalized here to {len(fam)} canonical
families; version strings alone cannot be trusted (see §4).</p>

<p><strong>Structured vs. prose.</strong> <em>Structured</em> counts come from the
depositor-supplied tool triples (provider, name, version) in each work's
<code class="no-katex">tools</code> field. <em>Prose</em> counts come from
regex-mining the free-text provenance statement of each work's detail record
for the same canonical families. <em>Combined</em> is the union of the two:
a work counts once even if it names a family in both places, or twice in one.
A work can therefore appear in the prose column but not the structured column
when a model is mentioned only in narrative, and vice versa when a model is
listed as a tool but never discussed in prose.</p>

<figure>{bars([(f["family"], f.get("combined_works", f["works"]), i) for i, f in enumerate(top_fam)])}
<figcaption>Works per AI family, top eight, counting structured declarations plus
provenance-prose mentions (combined). Work-level counts: one work naming a family twice
still counts once.</figcaption></figure>

<h3 id="stance">Text origin and human understanding</h3>

<table><thead><tr><th>Declaration</th><th>Works</th><th>Share (%)</th></tr></thead><tbody>
<tr><td>Primarily AI-generated</td><td>{auth.get("no-human-author-claimed", 0)}</td><td>{share(auth.get("no-human-author-claimed", 0))}</td></tr>
<tr><td>Mixed human / AI</td><td>{auth.get("mixed", 0)}</td><td>{share(auth.get("mixed", 0))}</td></tr>
<tr><td>Primarily human-written</td><td>{auth.get("human", 0)}</td><td>{share(auth.get("human", 0))}</td></tr>
<tr><td>Human understanding: all parts</td><td>{und.get("all", 0)}</td><td>{share(und.get("all", 0))}</td></tr>
<tr><td>Human understanding: some parts</td><td>{und.get("some", 0)}</td><td>{share(und.get("some", 0))}</td></tr>
<tr><td>Human understanding: no parts</td><td>{und.get("none", 0)}</td><td>{share(und.get("none", 0))}</td></tr>
</tbody></table>

<h2 id="counts">2. Counts</h2>

<h3 id="families">Families (structured works, %, prose works, combined, %)</h3>

<table><thead><tr><th>Family</th><th>Structured</th><th>%</th><th>Prose</th><th>Combined</th><th>%</th></tr></thead>
<tbody>{fam_rows}</tbody></table>

<h3 id="models">Top models</h3>

<figure>{bars([(m["model"], m["works"], i) for i, m in enumerate(models[:8])])}
<figcaption>Works per normalized model, top eight.</figcaption></figure>

<table><thead><tr><th>Model</th><th>Family</th><th>Works</th><th>%</th><th>Mentions</th></tr></thead>
<tbody>{model_rows}</tbody></table>

<h2 id="significance">3. Significance</h2>

<ul>
<li><strong>Two labs dominate.</strong> OpenAI ChatGPT appears on {chatgpt} works
({share(chatgpt)}%) in the structured field and {fams.get("OpenAI ChatGPT", {}).get("combined_works", chatgpt)} combined
({share(fams.get("OpenAI ChatGPT", {}).get("combined_works", chatgpt))}%); OpenAI Codex on {codex} structured,
{fams.get("OpenAI Codex", {}).get("combined_works", codex)} combined; Anthropic Claude Opus on {opus} structured,
{fams.get("Anthropic Claude Opus", {}).get("combined_works", opus)} combined. Together the
two labs cover {big_cover} of the {any_model} works that name any model.</li>
<li><strong>Multi-model workflows are normal.</strong> Claude Opus and ChatGPT co-occur on
{co_oc} works in the structured field; ChatGPT and Codex on {co_cc}. Depositors routinely draft with one system and code or
formalize with another.</li>
<li><strong>Lean rarely walks alone.</strong> {lean_works} works list Lean or Mathlib, and {lean_llm} of them
also list an LLM assistant. Machine-checked proof on Hexagon currently arrives bundled with AI
assistance, not instead of it.</li>
<li><strong>One subject hides in prose.</strong> Only {qa["llm_works"]} of {qa["works"]} quantum-algebra works list
an LLM in the structured field, yet {qa["prov_llm_works"]} of them name GPT-6-Astra,
OpenAI Codex, or a Danus verification system in their free-text provenance; the other
{qa["works"] - qa["prov_llm_works"]} describe generic AI assistance. Most are
quantum-cluster-algebra manuscripts from a small depositor group. Structured-only counting
understates this subject; it is among the heaviest per-work AI users in the archive.</li>
<li><strong>Disclosure is incomplete.</strong> {cov['works_no_tools']} works name no tools; {gap.get("prov_llm_but_no_structured_llm", 0)}
works name a specific system only in prose. Absence from the structured tables does
not mean absence of AI use — the combined {share(n_comb)}% figure is still a lower bound.</li>
<li><strong>Long tail, thin signal.</strong> Past the big three sit Bolzano ({bolzano}),
Harmonic Aristotle ({harmonic}), Claude Code ({claude_code}), Quora Poe ({poe}, an aggregator that hides the real model),
Danus ({danus_prov}, prose only), AxiomProver ({axiom}), then singletons:
xAI Grok ({xai}), Google Gemini variants ({google}), a local Qwen run ({local}),
Moonshot Kimi ({moonshot}), and Meta Muse Spark ({meta}).
Poe-style aggregators make exact model attribution impossible.</li>
</ul>

<h3 id="pairs">Frequent pairs</h3>

<table><thead><tr><th>Family A</th><th>Family B</th><th>Works together</th></tr></thead>
<tbody>{co_rows}</tbody></table>

<h3 id="subjects">Subjects</h3>

<table><thead><tr><th>Subject</th><th>Works</th><th>With LLM</th><th>LLM share (%)</th><th>Prose LLM</th></tr></thead>
<tbody>{subj_rows}</tbody></table>

<h3 id="nonllm">Non-LLM tooling (works, of which also list an LLM, prose works)</h3>

<table><thead><tr><th>Tool family</th><th>Works</th><th>Also LLM</th><th>Prose works</th></tr></thead>
<tbody>{tool_rows}</tbody></table>

<h2 id="caveats">4. Caveats</h2>

<ul>
<li>Declarations are depositor-supplied free text: “GPT-6 Astra”, “Astra 6”, and
“gpt-6-astra (pinned …)” are one model spelled three ways, and {len(raw)} raw spellings
collapse to {len(fam)} families only through the normalization table in
<code class="no-katex">analyze_hexagon.py</code>, which is itself a judgment call. {blank_works}
works leave the version blank for at least one declared tool.</li>
<li>Prose mining is regex-based (<code class="no-katex">PROV_PATTERNS</code> in
<code class="no-katex">analyze_hexagon.py</code>): {prov.get("works_naming_specific_system", 0)}
works name a specific system in prose, {prov.get("works_unspecified_ai_only", 0)} describe AI
use only generically (boilerplate declarations excluded). Every hit's matched spans are kept
per work as <code class="no-katex">prov_spans</code> in the analysis JSON, so a false
positive is auditable. The Danus verification system appears only in prose ({fam_map.get('Danus', {}).get('prov_works', 0)} works) and
has no structured counterpart.</li>
<li>Hexagon is in public beta with {n} works at snapshot time; shares will move as the
archive grows. Re-run <code class="no-katex">scan_hexagon.py</code>,
<code class="no-katex">analyze_hexagon.py</code>,
<code class="no-katex">render_hexagon_report.py</code> in that order.</li>
</ul>

<details><summary>Per-work table ({n} rows)</summary>
<table><thead><tr><th>ID</th><th>Subject</th><th>Origin</th><th>Understood</th><th>LLM families</th><th>Prose families</th><th>Title</th></tr></thead>
<tbody>{per_rows}</tbody></table>
</details>

<p class="footnote">Snapshot {esc(fetched)} from
<code class="no-katex">https://hexagonmath.org/api/v1/works</code> ({n} works);
detail records {esc(a["snapshot"].get("details_fetched_at") or "absent")} carry the mined
provenance. Pipeline: <code class="no-katex">scan_hexagon.py</code>,
<code class="no-katex">analyze_hexagon.py</code>,
<code class="no-katex">render_hexagon_report.py</code>; raw snapshots and analysis JSON
in <code class="no-katex">data/</code>. AI disclaimer: drafted with
<code class="no-katex">opencode-go/muse-spark-1.3-contributor</code> (2026-10-13); re-run and re-rendered with
<code class="no-katex">opencode-go/beam-free</code> ({esc(fetched[:10])}).</p>
"""

    full = (HERE / "hexagon-llm-models.html").read_text(encoding="utf-8")
    a_idx = full.index(BODY_ANCHOR) + len(BODY_ANCHOR)
    end_idx = full.index("</article>")
    out = full[:a_idx] + "\n" + body + "\n" + full[end_idx:]
    (HERE / "hexagon-llm-models.html").write_text(out, encoding="utf-8")
    print(f"rendered body ({len(body)} chars)")


if __name__ == "__main__":
    main()
