"""Analyse a Hexagon snapshot: which LLM/AI models are used, counts, significance.

Reads:  data/hexagon_works_latest.json  (from scan_hexagon.py)
Writes: data/hexagon_analysis.json

Stdlib only. Run:  python analyze_hexagon.py [--in data/hexagon_works_latest.json]

Two counting bases matter and both are reported:
  * mentions  = raw tool entries (one work can mention several models)
  * works     = works listing at least one tool of that family (deduplicated)

Raw (provider, name, version) strings are noisy — "GPT-6 Astra", "Astra 6",
"gpt-6-astra (pinned ...)" are one model — so every entry is mapped to a
canonical (family, model) pair. Anything that is a proof assistant, CAS, or
numerical library (Lean, Mathlib, Magma, SageMath, PARI/GP, GAP, Python
stack, ...) is classed as non-LLM tooling and counted separately; the
`llm_*` fields cover conversational/code AI only.
"""

import argparse
import collections
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent

# Free-text provenance mining. Each entry maps a regex hit to a canonical
# (kind, family) pair shared with classify(). Case-insensitive unless marked
# with (?-i:...). Patterns favour precision: bare "opus"/"sage"/"singular"
# are ordinary English/math words, so those require their system context.
PROV_PATTERNS = [
    ("llm", "OpenAI ChatGPT", r"chatgpt|gpt[\s-]*[56](?:[\s.]*\d)?(?:[\s-]*(?:astra|sol))?|astra[\s-]*6|gpt[\s-]*astra"),
    ("llm", "OpenAI Codex", r"(?-i:\bCodex\b)|\bcodex\b"),
    ("llm", "Anthropic Claude Opus", r"claude(?![\w\s-]*?(?:fable|sonnet))|opus[\s-]*5\.5|opus[\s-]*4\.8"),
    ("llm", "Anthropic Claude Fable", r"fable"),
    ("llm", "Anthropic Claude Sonnet", r"sonnet"),
    ("llm", "Anthropic Claude Code", r"claude[\s-]*code"),
    ("llm", "Google", r"gemini"),
    ("llm", "xAI", r"grok"),
    ("llm", "Harmonic", r"aristotle|harmonic"),
    ("llm", "Quora Poe (aggregator)", r"(?-i:\bPoe\b)|\bpoe\b"),
    ("llm", "Meta", r"muse[\s-]*spark"),
    ("llm", "Local/open", r"qwen|llama[\s-]*swap"),
    ("llm", "AxiomMath", r"axiomprover"),
    ("llm", "Danus", r"(?-i:\bDanus\b)|\bdanus\b"),
    ("llm", "Bolzano", r"bolzano"),
    ("llm", "Moonshot", r"moonshot|kimi"),
    ("tool", "Lean/Mathlib", r"(?-i:\bLean\b)|\blean\b|mathlib"),
    ("tool", "Magma", r"(?-i:\bMagma\b)|\bmagma\b"),
    ("tool", "SageMath", r"sagemath|(?-i:\bSage\b)"),
    ("tool", "PARI/GP", r"pari[\s/-]*gp|(?-i:\bPARI\b)"),
    ("tool", "GAP", r"(?-i:\bGAP\b)"),
    ("tool", "Macaulay2", r"macaulay"),
    ("tool", "Wolfram Mathematica", r"wolfram|mathematica"),
    ("tool", "Python/scientific stack", r"(?-i:\bPython\b)|\bpython\b|numpy|scipy|sympy|mpmath|(?-i:\bFLINT\b)|\bflint\b|gmpy|(?-i:\bGMP\b)"),
]
PROV_RES = [(k, f, re.compile(p, re.IGNORECASE)) for k, f, p in PROV_PATTERNS]
AI_PROSE_RE = re.compile(r"\bAI\b|artificial intelligence|generative AI|AI-assisted|AI-generated", re.IGNORECASE)


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def strip_parens(version):
    # "GPT-6.1 (manuscript)" -> "GPT-6.1"; keep the raw form for the raw table.
    v = norm(version)
    v = re.sub(r"\s*\(.*\)\s*", "", v).strip()
    return v


def classify(provider, name, version):
    """Return (kind, family, model) where kind is 'llm' or 'tool'."""
    p = norm(provider).lower()
    n = norm(name).lower()
    v = strip_parens(version)
    vl = v.lower().replace("_", "-")

    blob = f"{p} {n} {vl}"

    # --- non-LLM tooling first (they must not inflate AI counts) ---
    if "mathlib" in blob and "lean" not in blob:
        return ("tool", "Lean/Mathlib", "Mathlib")
    if "lean" in blob:
        return ("tool", "Lean/Mathlib", "Lean 4")
    if any(k in blob for k in ("magma", "sagemath", "sage", "pari", "gap",
                               "singular", "macaulay", "mace4", "prover9",
                               "sl2reps", "curvearith")):
        fam = "CAS/other"
        for k, name in (("magma", "Magma"), ("sage", "SageMath"),
                        ("pari", "PARI/GP"), ("gap", "GAP")):
            if k in blob:
                fam = name
                break
        if "singular" in blob:
            fam = "Singular"
        if "macaulay" in blob:
            fam = "Macaulay2"
        if "mace4" in blob or "prover9" in blob:
            fam = "Mace4/Prover9"
        if "sl2reps" in blob or "curvearith" in blob:
            fam = "Domain package"
        return ("tool", fam, norm(name) or norm(provider))
    if "wolfram" in blob or "mathematica" in blob:
        return ("tool", "Wolfram Mathematica", norm(name) or norm(provider))
    if any(k in blob for k in ("numpy", "scipy", "sympy", "mpmath", "flint",
                               "gmp", "gmpy", "python", "z3", "smt",
                               "horn clause")):
        return ("tool", "Python/scientific stack", norm(name) or norm(provider))
    if "rethlas" in blob:
        return ("tool", "Rethlas", "Rethlas")
    if "osverify" in blob:
        return ("tool", "OSVerify", "OSVerify")
    if "tau" in blob and "ceti" in blob:
        return ("tool", "TauCeti", "TauCeti")

    # --- LLM / AI assistants ---
    if "quora" in p or n.strip() == "poe" or "poe" in blob:
        return ("llm", "Quora Poe (aggregator)", "Poe (model unspecified)")
    if "harmonic" in p or "aristotle" in n:
        return ("llm", "Harmonic", "Aristotle")
    if "axiom" in p or "axiomprover" in n:
        return ("llm", "AxiomMath", "AxiomProver")
    if "meta" in p or "muse" in n:
        return ("llm", "Meta", "Muse Spark")
    if "bolzano" in blob:
        return ("llm", "Bolzano", "Bolzano")
    if "moonshot" in blob or "kimi" in blob:
        return ("llm", "Moonshot", "Kimi")
    if "xai" in p or "grok" in n:
        return ("llm", "xAI", "Grok " + v if v else "Grok")
    if "google" in p or "gemini" in n:
        return ("llm", "Google", "Gemini " + v if v else "Gemini")
    if "qwen" in blob or "llama-swap" in blob:
        return ("llm", "Local/open", "Qwen (local)")
    if "anthropic" in p or "claude" in n:
        if "fable" in blob:
            fam = "Anthropic Claude Fable"
        elif "sonnet" in blob:
            fam = "Anthropic Claude Sonnet"
        elif "code" in n and "opus" not in blob:
            return ("llm", "Anthropic Claude Code", "Claude Code")
        else:
            fam = "Anthropic Claude Opus"
        ver = v
        ver = re.sub(r"(?i)^opus\s*", "", ver)
        ver = {"5": "5", "5.1": "5.1", "5.5": "5.5", "4.8": "Opus 4.8"}.get(ver, ver)
        return ("llm", fam, (fam.split()[-1] + " " + ver) if ver else fam.split()[-1])
    if "openai" in p or "codex" in n or "chatgpt" in blob or re.search(r"\bgpt\b", blob):
        if "codex" in n or ("codex" in blob and "chatgpt" not in n):
            fam = "OpenAI Codex"
            ver = v
            ver = re.sub(r"(?i)^(gpt-?|chatgpt\s*)", "", ver).strip("- ")
            ver = {"6-astra": "6 Astra", "6-luna": "6 Luna",
                   "6.1": "6.1", "6": "6", "5": "5"}.get(ver.lower(), ver)
            ver = re.sub(r"(?i)^astra\s*6(\.1)?$", r"6 Astra\1", ver)
            ver = re.sub(r"(?i)^6\s*astra$", "6 Astra", ver)
            ver = re.sub(r"(?i)^sol\s*5\.6$", "5.6 Sol", ver)
            ver = re.sub(r"(?i)^5\.6\s*sol$", "5.6 Sol", ver)
            return ("llm", fam, ("Codex " + ver) if ver else "Codex")
        fam = "OpenAI ChatGPT"
        ver = v
        ver = re.sub(r"(?i)^(gpt-?|chatgpt\s*5\.6\s*sol\s*/?\s*)", "", ver)
        low = ver.lower().replace("-", " ").strip()
        mapping = {
            "6 astra": "6 Astra", "astra 6": "6 Astra", "astra": "6 Astra",
            "astra 6 pro": "6 Astra Pro", "6 astra pro": "6 Astra Pro",
            "6 1 manuscript": "6.1", "6.1": "6.1", "6": "6",
            "5 6 sol": "5.6 Sol", "5.6 sol": "5.6 Sol", "sol 5 6": "5.6 Sol",
            "5 6": "5.6", "5 5": "5.5", "5 4": "5.4",
            "gpt6": "6", "pro": "Pro", "6 pro": "6 Pro",
        }
        ver = mapping.get(low, ver)
        return ("llm", fam, ("ChatGPT " + ver) if ver else "ChatGPT")

    return ("llm", norm(provider) or "Unknown", norm(name) or "Unknown")


def mine_provenance(text):
    """Return (families, spans): canonical (kind, family) hits in free text.

    families: set of (kind, family). spans: matched substrings (capped),
    kept so hits are auditable — a false positive is visible, not silent.
    """
    fams, spans = set(), []
    for kind, fam, rx in PROV_RES:
        for m in rx.finditer(text or ""):
            fams.add((kind, fam))
            if len(spans) < 8:
                spans.append(m.group(0))
    return fams, spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/hexagon_works_latest.json")
    ap.add_argument("--details", default="data/hexagon_details_latest.json")
    ap.add_argument("--out", default="data/hexagon_analysis.json")
    args = ap.parse_args()

    snap = json.loads((HERE / args.inp).read_text(encoding="utf-8"))
    works = snap["works"]
    n = len(works)

    details = {}
    dsnap = None
    try:
        dsnap = json.loads((HERE / args.details).read_text(encoding="utf-8"))
        for d in dsnap["works"]:
            if d.get("identifier"):
                details[d["identifier"]] = d
        print(f"loaded {len(details)} detail records ({dsnap.get('fetched_at')})")
    except FileNotFoundError:
        print("no detail records; provenance mining skipped")

    fam_works = collections.Counter()      # works mentioning family (>=1 entry)
    fam_mentions = collections.Counter()   # raw entries per family
    model_works = collections.Counter()
    model_mentions = collections.Counter()
    raw_table = collections.Counter()
    tool_fam_works = collections.Counter()
    tool_fam_mentions = collections.Counter()
    authorship = collections.Counter()
    understanding = collections.Counter()
    subject_total = collections.Counter()
    subject_llm = collections.Counter()
    subject_prov_llm = collections.Counter()
    llm_by_authorship = collections.Counter()
    cooccur = collections.Counter()
    prov_fam_works = collections.Counter()
    prov_fam_mentions = collections.Counter()
    n_with_provenance = 0
    n_specific_system = 0
    n_unspecified_ai_only = 0
    gap_ids = []
    tool_with_llm = collections.Counter()
    tool_total = collections.Counter()
    prov_tool_fam_works = collections.Counter()
    prov_tool_fam_mentions = collections.Counter()
    per_work = []
    llm_work_ids = []
    no_tool_ids = []

    for w in works:
        wid = w.get("identifier")
        tools = w.get("tools") or []
        authorship[w.get("authorshipMode") or "?"] += 1
        understanding[w.get("humanUnderstanding") or "?"] += 1
        subject_total[w.get("subject") or "?"] += 1

        fams, models, llm_fams = set(), set(), set()
        tool_fams = set()
        raw_labels = []
        for t in tools:
            p, nm, v = t.get("provider"), t.get("name"), t.get("version")
            raw_table[(norm(p), norm(nm), norm(v))] += 1
            kind, fam, model = classify(p, nm, v)
            if kind == "llm":
                fam_mentions[fam] += 1
                model_mentions[(fam, model)] += 1
                fams.add(fam)
                models.add((fam, model))
                llm_fams.add(fam)
            else:
                tool_fam_mentions[fam] += 1
                fams.add(f"tool:{fam}")
                tool_fams.add(fam)
            raw_labels.append(f"{norm(p)} / {norm(nm)} / {norm(v)}")
        for f in fams:
            if f.startswith("tool:"):
                tool_fam_works[f[5:]] += 1
            else:
                fam_works[f] += 1
        for m in models:
            model_works[m] += 1

        has_llm = bool(llm_fams)
        for tf in tool_fams:
            tool_total[tf] += 1
            if has_llm:
                tool_with_llm[tf] += 1
        if has_llm:
            subject_llm[w.get("subject") or "?"] += 1
            llm_work_ids.append(wid)
            llm_by_authorship[w.get("authorshipMode") or "?"] += 1
        if not tools:
            no_tool_ids.append(wid)
        for a in sorted(llm_fams):
            for b in sorted(llm_fams):
                if a < b:
                    cooccur[(a, b)] += 1

        # Provenance free text (detail projection). Independent of the
        # structured triples above: depositors often name models in prose
        # while leaving the tools field empty, or vice versa.
        prov_llm_fams = set()
        prov_tool_fams = set()
        prov_spans = []
        ai_prose = False
        d = details.get(wid)
        if d and d.get("provenance"):
            n_with_provenance += 1
            hits, prov_spans = mine_provenance(d["provenance"])
            for kind, fam in hits:
                if kind == "llm":
                    prov_fam_mentions[fam] += 1
                    prov_llm_fams.add(fam)
                else:
                    prov_tool_fam_mentions[fam] += 1
                    prov_tool_fams.add(fam)
            # Generic-AI signal must come from the depositor's own words, not
            # the mandatory declaration boilerplate.
            body = "\n".join(
                ln for ln in d["provenance"].splitlines()
                if not ln.startswith(("Text declaration:",
                                      "Human-understanding declaration:")))
            ai_prose = bool(AI_PROSE_RE.search(body))
            for f in prov_llm_fams:
                prov_fam_works[f] += 1
            for f in prov_tool_fams:
                prov_tool_fam_works[f] += 1
        if prov_llm_fams:
            n_specific_system += 1
            subject_prov_llm[w.get("subject") or "?"] += 1
        elif ai_prose:
            n_unspecified_ai_only += 1
        if prov_llm_fams and not has_llm:
            gap_ids.append(wid)

        per_work.append({
            "id": wid,
            "title": w.get("title"),
            "subject": w.get("subject"),
            "authorshipMode": w.get("authorshipMode"),
            "humanUnderstanding": w.get("humanUnderstanding"),
            "llm_families": sorted(llm_fams),
            "prov_llm_families": sorted(prov_llm_fams),
            "prov_spans": prov_spans,
            "ai_prose": ai_prose,
            "n_tool_entries": len(tools),
            "raw_tools": raw_labels,
        })

    def pct(x, base=n):
        return round(100.0 * x / base, 1) if base else 0.0

    combined_ids = set(llm_work_ids) | {
        w["id"] for w in per_work if w["prov_llm_families"]}
    fam_rows = []
    for f in sorted(set(fam_works) | set(prov_fam_works),
                    key=lambda f: -len({w["id"] for w in per_work
                                        if f in w["llm_families"]
                                        or f in w["prov_llm_families"]})):
        sw = fam_works.get(f, 0)
        pw = prov_fam_works.get(f, 0)
        cw = len({w["id"] for w in per_work
                  if f in w["llm_families"] or f in w["prov_llm_families"]})
        fam_rows.append({"family": f, "works": sw, "pct_of_all": pct(sw),
                         "mentions": fam_mentions.get(f, 0),
                         "prov_works": pw,
                         "prov_mentions": prov_fam_mentions.get(f, 0),
                         "combined_works": cw, "combined_pct": pct(cw)})

    analysis = {
        "snapshot": {"fetched_at": snap.get("fetched_at"),
                     "total_reported": snap.get("total_reported"),
                     "n_works": n,
                      "details_fetched_at": dsnap.get("fetched_at") if dsnap else None,
                      "n_detail_records": len(details)},
        "coverage": {
            "n_works": n,
            "works_with_any_tools": n - len(no_tool_ids),
            "works_with_llm": len(llm_work_ids),
            "works_no_tools": len(no_tool_ids),
            "pct_with_llm": pct(len(llm_work_ids)),
            "pct_no_tools": pct(len(no_tool_ids)),
            "works_with_llm_combined": len(combined_ids),
            "pct_with_llm_combined": pct(len(combined_ids)),
        },
        "authorshipMode": dict(authorship),
        "humanUnderstanding": dict(understanding),
        "llm_by_authorship": dict(llm_by_authorship),
        "provenance": {
            "works_with_provenance": n_with_provenance,
            "works_naming_specific_system": n_specific_system,
            "works_unspecified_ai_only": n_unspecified_ai_only,
        },
        "disclosure_gap": {
            "prov_llm_but_no_structured_llm": len(gap_ids),
            "ids": sorted(gap_ids),
        },
        "family_works": fam_rows,
        "model_works": [{"family": f, "model": m, "works": c,
                         "pct_of_all": pct(c), "mentions": model_mentions[(f, m)]}
                        for (f, m), c in model_works.most_common()],
        "raw_triples": [{"provider": p, "name": nm, "version": v, "mentions": c}
                        for (p, nm, v), c in raw_table.most_common()],
        "n_raw_triples": len(raw_table),
        "non_llm_tools": {
            "by_works": dict(tool_fam_works),
            "by_mentions": dict(tool_fam_mentions),
            "works_also_listing_llm": dict(tool_with_llm),
            "prov_by_works": dict(prov_tool_fam_works),
            "prov_by_mentions": dict(prov_tool_fam_mentions),
        },
        "cooccurrence": [{"a": a, "b": b, "works": c}
                         for (a, b), c in cooccur.most_common(20)],
        "subjects": [{"subject": s, "works": c,
                      "llm_works": subject_llm.get(s, 0),
                      "llm_share_pct": round(100.0 * subject_llm.get(s, 0) / c, 1),
                      "prov_llm_works": subject_prov_llm.get(s, 0)}
                     for s, c in subject_total.most_common()],
        "per_work": per_work,
    }
    out = HERE / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(analysis, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"works={n} with_llm={len(llm_work_ids)} no_tools={len(no_tool_ids)}")
    print(f"families={len(fam_works)} raw_triples={len(raw_table)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
