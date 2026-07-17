#!/usr/bin/env python3
"""Codebase-mapper bundle -> a hyper-polished, multipage, bilingual PDF report.

Consumes the ``.tar`` bundle a codebase-mapper run emits (``run_manifest.json``,
``concepts.json``, ``enrichments.jsonl``, plus an ``inventory.ttl`` RDF graph and
raw content blobs this script never touches) and renders it as a numbered,
multi-chapter FrameForge book: repository overview, AST coverage, dependency
graph, concept landscape, a sampled file digest, and a provenance/integrity
appendix.

SCALE. The bundle format is the same at 541 source files (fastapi) or at
Linux-kernel scale (tens of thousands of files, a multi-gigabyte
``inventory.ttl``, a concepts vocabulary that can run into the hundreds of
thousands of entries). This script's report shape stays constant across that
range because it never reads ``inventory.ttl``, ``embeddings.npz`` or
``concepts_embeddings.npz`` — the aggregate statistics a report needs already
live in ``run_manifest.json`` (bounded by vocabulary/language cardinality, not
by repo size). The only two artifacts it does read are handled specifically to
stay bounded:
  - ``concepts.json`` is parsed as a streaming top-K selection (a size-K min-heap
    over a single pass; ``pip install ijson`` lets that pass skip the file's
    ``cooccurrence``/``per_path_concepts`` payloads entirely — with plain
    ``json.load`` as a slower, memory-heavier fallback).
  - ``enrichments.jsonl`` is read once, line by line; ``file_summary`` rows are
    reservoir-sampled to a fixed count so a kernel-sized corpus with hundreds of
    thousands of summaries costs the same O(sample size) memory as fastapi's 532.
The tar itself is opened in random-access mode and only the three named members
above are ever extracted — ``blobs/`` content is never read.

PALS'S LAW. ``enrichments.jsonl`` is LLM output (see its ``model`` field) —
untrusted, unverified commentary, not fact. Every section of the report that
surfaces it is visually flagged with a warning badge and an explicit disclaimer
paragraph; it is never presented as equivalent to the deterministic, computed
statistics (counts, coverage percentages) that make up the rest of the report.

I18N. ``--locale`` accepts ``en_US``, ``pt_BR``, a comma-separated list of
either, or ``all``; one full book is built per locale from the ``STRINGS``
table below (chapter titles, captions, disclaimers) plus locale-aware number/
date formatting. Add a locale by adding one more column to ``STRINGS`` and
``FILETYPE_LABELS`` and one more entry to ``SUPPORTED_LOCALES``/``_MONTHS``.

Usage:
    uv run python static/examples/codebase_analysis_report.py _tmp/fastapi.tar
    uv run python static/examples/codebase_analysis_report.py _tmp/fastapi.tar \\
        --locale all --pdf --top-concepts 60 --file-sample 20

MCP contract: ``build()`` returns one ``en_US`` book from
``$CODEBASE_REPORT_BUNDLE`` (default: ``_tmp/fastapi.tar``) for interactive
iteration via ``run_sdk_client``; real runs go through ``main()``.
"""
import argparse
import heapq
import json
import os
import random
import subprocess
import sys
import tarfile
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from dataclasses import replace as _dc_replace

from frameforge.sdk import (  # noqa: E402
    BookBuilder,
    Frame,
    badge,
    closed_palette,
    contrast_ratio,
    default_theme,
    harmony_of_scale,
    render_page_svgs,
    serialize,
    tone_scale,
)
from frameforge.sdk.metrics import text_height  # noqa: E402
from frameforge.sdk.model import validate_document  # noqa: E402

# ---------------------------------------------------------------------------
# Palette & type scale — see the typeface-and-colour skill. One closed
# palette (ground/ink/accent + quiet greys derived from ink's own scale),
# reused everywhere; a second hue (warn) is admitted only because it carries
# real meaning (the PALS's-Law "unverified LLM content" flag), never as
# decoration. No chart in this report picks colour by array index — rank is
# carried by one accent's tone ladder, per "never encode rank by hue alone."
# ---------------------------------------------------------------------------

GROUND = "#FBF9F4"    # warm paper, ~62% of every page
INK = "#22201C"       # near-black, not pure #000 (harsher than any real ink)
ACCENT = "#A6432E"    # rust/terracotta — one hue, one duty: structure & emphasis (operator-chosen
                      # over indigo/petrol via rendered options, 2026-07-09; 5.76:1 on GROUND)
WARN = "#9A6324"      # admitted only for the LLM-provenance badge — meaningful, not decorative;
                      # kept visually distinct from the warmer/redder ACCENT (browner, more yellow)

_PALETTE_TOKENS = closed_palette(ground=GROUND, ink=INK, accent=ACCENT, quiet_steps=3).tokens()
PALETTE = {**_PALETTE_TOKENS, "warn": WARN}
# quiet2 (tone_scale index 2, "#797979") measures 4.14:1 on GROUND — below the
# 4.5:1 body-text floor (typeface-and-colour skill, WCAG small-text gate). It is
# used for real caption/label TEXT throughout this report, not decoration, so
# it is promoted to quiet3's darker tone ("#4d4d4d", 8.03:1) rather than kept
# at a value that fails its own use. Verified with contrast_ratio(), not eyeballed.
assert contrast_ratio(PALETTE["quiet3"], GROUND) >= 4.5, "quiet3 no longer clears the body floor"
PALETTE["quiet2"] = PALETTE["quiet3"]
# The masthead is a solid ACCENT band with GROUND-coloured (paper) text on
# it (operator-chosen "accent band" option, 2026-07-09) — contrast is
# symmetric, so the same ACCENT/GROUND ratio verified above applies in
# reverse; still checked explicitly since the two ratios only coincide for
# a symmetric contrast formula, and this asserts that assumption rather
# than silently relying on it.
assert contrast_ratio(GROUND, ACCENT) >= 4.5, "ground text no longer clears the accent-band floor"

REPORT_THEME = _dc_replace(default_theme(), ink=INK, accent=ACCENT, warn=WARN,
                           surface=GROUND, muted=PALETTE["quiet2"], sub=PALETTE["quiet3"],
                           line=PALETTE["quiet1"])

# Modular scale, base 10.5pt, ratio 1.25 ("assertive" — a data report earns
# strong stat numbers). Every custom text size below is one of these steps —
# no ad-hoc font_size literals (Scale-discipline gate).
SIZE_CAPTION = 9.0
SIZE_LABEL = 10.5
SIZE_BODY = 13.0
SIZE_SUBHEAD = 16.5
SIZE_STAT = 32.0
SIZE_HEADLINE = 41.0

# Two verified families (fontconfig-checked via list_fonts, not assumed):
# Inter for display/data/labels — a humanist grotesque built for this exact
# duty (UI, numerals, tracked caps); Bitstream Charter for quoted prose in
# the verbatim receipts — a genuine Carter-drawn book face, paired with the
# flow engine's own serif body text by CLASS (serif reads, sans structures)
# rather than left to an unspecified renderer default.
FONT_SANS = ["Inter", "Archivo", "Arimo", "sans-serif"]
FONT_SERIF = ["Bitstream Charter", "Georgia", "serif"]

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------

SUPPORTED_LOCALES = ("en_US", "pt_BR")

STRINGS: dict[str, dict[str, str]] = {
    "book_title": {"en_US": "Codebase Analysis Report — {repo}",
                   "pt_BR": "Relatório de Análise de Código — {repo}"},
    "book_author": {"en_US": "FrameForge Codebase Reporter",
                    "pt_BR": "Repórter de Código FrameForge"},
    "masthead_eyebrow": {"en_US": "STRUCTURAL ANALYSIS", "pt_BR": "ANÁLISE ESTRUTURAL"},
    "masthead_meta": {
        "en_US": "commit {commit} · {date} · codebase-mapper report generator {tool}",
        "pt_BR": "commit {commit} · {date} · gerador de relatório codebase-mapper {tool}",
    },
    "chapter_kicker": {"en_US": "CHAPTER {n} OF {total}", "pt_BR": "CAPÍTULO {n} DE {total}"},
    "receipt_title": {"en_US": "One receipt, verbatim", "pt_BR": "Um recibo, na íntegra"},
    "receipt_note": {
        "en_US": "A handful of sampled enrichments quoted exactly as generated, each with its "
                 "full provenance — the standard every other AI-generated line in this report "
                 "is held to, even where it isn't quoted in full.",
        "pt_BR": "Alguns enriquecimentos amostrados, citados exatamente como gerados, cada um "
                 "com sua proveniência completa — o mesmo padrão que toda outra linha gerada "
                 "por IA neste relatório segue, mesmo quando não citada na íntegra.",
    },

    "ch1_title": {"en_US": "Repository Overview", "pt_BR": "Visão Geral do Repositório"},
    "ch1_intro": {
        "en_US": "This report was generated from a codebase-mapper analysis of "
                 "{repo} at commit {commit}, run on {date} with tool version "
                 "{tool}. Every figure below is a deterministic count from that "
                 "run's manifest unless explicitly marked otherwise.",
        "pt_BR": "Este relatório foi gerado a partir de uma análise codebase-mapper "
                 "de {repo} no commit {commit}, executada em {date} com a versão "
                 "{tool} da ferramenta. Todo número abaixo é uma contagem "
                 "determinística do manifesto dessa execução, salvo indicação "
                 "explícita em contrário.",
    },
    "overview_kpi_caption": {"en_US": "Headline counts", "pt_BR": "Números-chave"},
    "kpi_total_files": {"en_US": "Total files", "pt_BR": "Arquivos totais"},
    "kpi_source_code": {"en_US": "Source code", "pt_BR": "Código-fonte"},
    "kpi_test_code": {"en_US": "Test code", "pt_BR": "Código de teste"},
    "kpi_documentation": {"en_US": "Documentation", "pt_BR": "Documentação"},
    "lang_chart_title": {"en_US": "Languages", "pt_BR": "Linguagens"},
    "lang_chart_caption": {"en_US": "Source files by language",
                            "pt_BR": "Arquivos-fonte por linguagem"},
    "filetype_chart_title": {"en_US": "File Types", "pt_BR": "Tipos de Arquivo"},
    "filetype_chart_caption": {"en_US": "Files by role in the repository",
                                "pt_BR": "Arquivos por papel no repositório"},
    "other": {"en_US": "other", "pt_BR": "outros"},

    "ch2_title": {"en_US": "AST Coverage & Code Health",
                  "pt_BR": "Cobertura de AST e Saúde do Código"},
    "ch2_intro": {
        "en_US": "AST coverage measures how much of the source tree the "
                 "extraction pipeline could actually parse into a structured "
                 "symbol table, as opposed to treating a file as an opaque blob.",
        "pt_BR": "A cobertura de AST mede quanto da árvore de código-fonte o "
                 "pipeline de extração conseguiu de fato analisar como uma "
                 "tabela de símbolos estruturada, em vez de tratar o arquivo "
                 "como um blob opaco.",
    },
    "ast_kpi_caption": {"en_US": "Extraction totals", "pt_BR": "Totais de extração"},
    "kpi_ast_coverage": {"en_US": "AST coverage", "pt_BR": "Cobertura AST"},
    "kpi_parse_errors": {"en_US": "Parse errors", "pt_BR": "Erros parsing"},
    "kpi_symbols": {"en_US": "Symbols", "pt_BR": "Símbolos"},
    "kpi_imports": {"en_US": "Imports", "pt_BR": "Imports"},
    "col_language": {"en_US": "Language", "pt_BR": "Linguagem"},
    "col_files": {"en_US": "Files", "pt_BR": "Arquivos"},
    "col_files_with_ast": {"en_US": "With AST", "pt_BR": "Com AST"},
    "col_symbols": {"en_US": "Symbols", "pt_BR": "Símbolos"},
    "col_imports": {"en_US": "Imports", "pt_BR": "Imports"},

    "ch3_title": {"en_US": "Dependency Graph", "pt_BR": "Grafo de Dependências"},
    "ch3_intro": {
        "en_US": "Edge counts extracted from import statements and package "
                 "manifests — the graph itself lives in inventory.ttl and is "
                 "intentionally not loaded here; these totals are its summary.",
        "pt_BR": "Contagens de arestas extraídas de declarações de import e "
                 "manifestos de pacote — o grafo em si vive em inventory.ttl e "
                 "propositalmente não é carregado aqui; estes totais são seu "
                 "resumo.",
    },
    "deps_kpi_caption": {"en_US": "Edge totals", "pt_BR": "Totais de arestas"},
    "kpi_import_edges": {"en_US": "Imports", "pt_BR": "Imports"},
    "kpi_import_external": {"en_US": "External", "pt_BR": "Externos"},
    "kpi_declares_dep": {"en_US": "Declared", "pt_BR": "Declaradas"},
    "kpi_pins_dep": {"en_US": "Pinned", "pt_BR": "Fixadas"},
    "kpi_tests_edges": {"en_US": "Tests", "pt_BR": "Testes"},

    "ch4_title": {"en_US": "Concept Landscape", "pt_BR": "Panorama de Conceitos"},
    "ch4_intro": {
        "en_US": "The top {n} concepts by frequency, selected in a single "
                 "bounded pass over the vocabulary regardless of its total size.",
        "pt_BR": "Os {n} principais conceitos por frequência, selecionados em "
                 "uma única passagem limitada sobre o vocabulário, "
                 "independentemente do seu tamanho total.",
    },
    "concept_chart_caption": {"en_US": "Top concepts by frequency",
                               "pt_BR": "Principais conceitos por frequência"},
    "col_concept": {"en_US": "Concept", "pt_BR": "Conceito"},
    "col_frequency": {"en_US": "Frequency", "pt_BR": "Frequência"},
    "ch4_related_section": {"en_US": "Concept relationships", "pt_BR": "Relações entre conceitos"},
    "ch4_related_intro": {
        "en_US": "Which top concepts co-occur most often in the same chunks — computed as a "
                 "second bounded pass over the same file, filtered to pairs where both concepts "
                 "are already in the top ranking (so cost stays O(K²), never O(all co-occurrence "
                 "edges), independent of corpus size.",
        "pt_BR": "Quais conceitos principais co-ocorrem com mais frequência nos mesmos trechos — "
                 "computado como uma segunda passagem limitada sobre o mesmo arquivo, filtrada a "
                 "pares em que ambos os conceitos já estão no ranking (custo O(K²), nunca O(todas "
                 "as arestas de co-ocorrência), independente do tamanho do corpus.",
    },
    "col_related": {"en_US": "Co-occurs with", "pt_BR": "Co-ocorre com"},
    "progress_concepts": {"en_US": "CONCEPTS {lo}–{hi} OF {total}", "pt_BR": "CONCEITOS {lo}–{hi} DE {total}"},
    "progress_related": {"en_US": "RELATIONSHIPS {lo}–{hi} OF {total}",
                          "pt_BR": "RELAÇÕES {lo}–{hi} DE {total}"},
    "progress_files": {"en_US": "FILES {lo}–{hi} OF {total}", "pt_BR": "ARQUIVOS {lo}–{hi} DE {total}"},
    "ch4_commentary_section": {"en_US": "Selected commentary", "pt_BR": "Comentários selecionados"},
    "llm_generated": {"en_US": "⚠ AI-GENERATED, UNVERIFIED — model: {model}",
                       "pt_BR": "⚠ GERADO POR IA, NÃO VERIFICADO — modelo: {model}"},
    "ch4_disclaimer": {
        "en_US": "The paragraphs below were written by a language model reading "
                 "code excerpts, not computed statistics. Per this project's "
                 "PALS's-Law policy they are unverified by default: read them as "
                 "a lead worth checking against the source, never as fact.",
        "pt_BR": "Os parágrafos abaixo foram escritos por um modelo de linguagem "
                 "lendo trechos de código, não são estatísticas computadas. "
                 "Conforme a política PALS's-Law deste projeto, são não "
                 "verificados por padrão: leia-os como uma pista a conferir na "
                 "fonte, nunca como fato.",
    },

    "ch5_title": {"en_US": "File Digest Sample", "pt_BR": "Amostra de Resumos de Arquivo"},
    "ch5_intro": {
        "en_US": "A {n}-file reservoir sample of per-file summaries, drawn with "
                 "uniform probability across the whole corpus in one streaming "
                 "pass — the sample size, not the corpus size, bounds this "
                 "section's length.",
        "pt_BR": "Uma amostra por reservatório de {n} arquivos com resumos por "
                 "arquivo, sorteada com probabilidade uniforme sobre todo o "
                 "corpus em uma única passagem contínua — o tamanho da amostra, "
                 "não o do corpus, limita a extensão desta seção.",
    },
    "col_path": {"en_US": "Path", "pt_BR": "Caminho"},
    "col_summary": {"en_US": "Summary", "pt_BR": "Resumo"},

    "ch6_title": {"en_US": "Data Provenance & Integrity",
                  "pt_BR": "Proveniência e Integridade dos Dados"},
    "ch6_intro": {
        "en_US": "Every artifact this bundle contains, with its content hash — "
                 "the same fingerprint a consumer would check before trusting "
                 "the file.",
        "pt_BR": "Todo artefato contido neste pacote, com seu hash de "
                 "conteúdo — a mesma impressão digital que um consumidor "
                 "verificaria antes de confiar no arquivo.",
    },
    "col_artifact": {"en_US": "Artifact", "pt_BR": "Artefato"},
    "col_size": {"en_US": "Size", "pt_BR": "Tamanho"},
    "col_sha256": {"en_US": "SHA-256", "pt_BR": "SHA-256"},
    "shacl_pass": {"en_US": "SHACL SELF-CHECK: CONFORMS", "pt_BR": "AUTOVERIFICAÇÃO SHACL: CONFORME"},
    "shacl_fail": {"en_US": "SHACL SELF-CHECK: VIOLATIONS FOUND",
                   "pt_BR": "AUTOVERIFICAÇÃO SHACL: VIOLAÇÕES ENCONTRADAS"},
    "ch6_closing": {
        "en_US": "See DISCLAIMER.md for this project's full methodological "
                 "caveats — no statement in this report should be taken for "
                 "granted without checking it against the source it describes.",
        "pt_BR": "Consulte DISCLAIMER.md para as ressalvas metodológicas "
                 "completas deste projeto — nenhuma afirmação deste relatório "
                 "deve ser considerada garantida sem conferi-la na fonte que "
                 "descreve.",
    },

    "ch7_title": {"en_US": "Risk Register", "pt_BR": "Registro de Riscos"},
    "ch7_intro": {
        "en_US": "{n} named structural risks the recomposer flags as evidence-backed and "
                 "\"not to be replicated blindly\" — real import cycles and coupling patterns "
                 "found by walking the dependency graph, not a heuristic guess.",
        "pt_BR": "{n} riscos estruturais nomeados que o recomposer sinaliza como "
                 "evidenciados e \"a não replicar cegamente\" — ciclos de import e padrões "
                 "de acoplamento reais encontrados ao percorrer o grafo de dependências, "
                 "não uma suposição heurística.",
    },
    "risk_kpi_caption": {"en_US": "Build-plan totals", "pt_BR": "Totais do plano de construção"},
    "kpi_risks": {"en_US": "Named risks", "pt_BR": "Riscos nomeados"},
    "kpi_build_steps": {"en_US": "Build steps", "pt_BR": "Passos de build"},
    "kpi_skipped_phases": {"en_US": "Skipped phases", "pt_BR": "Fases ignoradas"},
    "kpi_open_assumptions": {"en_US": "Open assumptions", "pt_BR": "Suposições abertas"},

    "ch8_title": {"en_US": "Structural Decomposition", "pt_BR": "Decomposição Estrutural"},
    "ch8_intro": {
        "en_US": "{n} architectural parts the decomposer classified by kind, layer, and "
                 "responsibility — each confidence-tagged (certain > strong > probable > "
                 "weak > unknown); this is interpretation grounded in evidence, not a raw count.",
        "pt_BR": "{n} partes arquiteturais que o decomposer classificou por tipo, camada e "
                 "responsabilidade — cada uma com confiança marcada (certain > strong > "
                 "probable > weak > unknown); isto é interpretação fundamentada em "
                 "evidência, não uma contagem bruta.",
    },
    "decomp_kpi_caption": {"en_US": "Decomposition totals", "pt_BR": "Totais da decomposição"},
    "kpi_parts": {"en_US": "Parts", "pt_BR": "Partes"},
    "kpi_relationships": {"en_US": "Relationships", "pt_BR": "Relações"},
    "kpi_quality_gates": {"en_US": "Quality gates", "pt_BR": "Portões de qualidade"},
    "kpi_cycle_resolutions": {"en_US": "Cycle resolutions", "pt_BR": "Resoluções de ciclo"},
    "decomp_kind_title": {"en_US": "Parts by kind", "pt_BR": "Partes por tipo"},
    "decomp_kind_caption": {"en_US": "Structural parts by kind", "pt_BR": "Partes estruturais por tipo"},
    "decomp_catalog_title": {"en_US": "Full catalog", "pt_BR": "Catálogo completo"},
    "col_part": {"en_US": "Part", "pt_BR": "Parte"},
    "col_kind": {"en_US": "Kind", "pt_BR": "Tipo"},
    "col_layer": {"en_US": "Layer", "pt_BR": "Camada"},
    "col_confidence": {"en_US": "Confidence", "pt_BR": "Confiança"},
    "col_responsibility": {"en_US": "Responsibility", "pt_BR": "Responsabilidade"},
    "progress_parts": {"en_US": "PARTS {lo}–{hi} OF {total}", "pt_BR": "PARTES {lo}–{hi} DE {total}"},
}

FILETYPE_LABELS: dict[str, dict[str, str]] = {
    "asset": {"en_US": "Assets", "pt_BR": "Ativos"},
    "ci_cd": {"en_US": "CI/CD", "pt_BR": "CI/CD"},
    "configuration": {"en_US": "Config", "pt_BR": "Config"},
    "dependency_manifest": {"en_US": "Dep. manifest", "pt_BR": "Manifesto"},
    "documentation": {"en_US": "Docs", "pt_BR": "Docs"},
    "license": {"en_US": "License", "pt_BR": "Licença"},
    "lockfile": {"en_US": "Lockfile", "pt_BR": "Lockfile"},
    "source_code": {"en_US": "Source", "pt_BR": "Fonte"},
    "test_code": {"en_US": "Tests", "pt_BR": "Testes"},
}

_MONTHS = {
    "en_US": ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"],
    "pt_BR": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
              "agosto", "setembro", "outubro", "novembro", "dezembro"],
}


def T(locale: str):
    loc = locale if locale in SUPPORTED_LOCALES else "en_US"

    def t(key: str, **kw: Any) -> str:
        entry = STRINGS.get(key)
        if entry is None:
            return key
        s = entry.get(loc, entry.get("en_US", key))
        return s.format(**kw) if kw else s

    return t


def fmt_int(n: Any, locale: str) -> str:
    s = f"{int(n):,}"
    if locale == "pt_BR":
        s = s.translate(str.maketrans(",.", ".,"))
    return s


def fmt_bytes(n: Any, locale: str) -> str:
    size = float(n)
    unit = "B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            break
        size /= 1024
    s = f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
    return s.replace(".", ",") if locale == "pt_BR" else s


def fmt_date(iso_ts: str, locale: str) -> str:
    try:
        y, m, d = iso_ts[:10].split("-")
        y, m, d = int(y), int(m), int(d)
    except (ValueError, AttributeError):
        return iso_ts or "?"
    months = _MONTHS.get(locale, _MONTHS["en_US"])
    if locale == "pt_BR":
        return f"{d} de {months[m - 1]} de {y}"
    return f"{months[m - 1]} {d}, {y}"


def truncate(text: str, n: int) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def filetype_label(key: str, locale: str) -> str:
    return FILETYPE_LABELS.get(key, {}).get(locale, key)


def pct(n: Any, d: Any) -> float:
    n, d = float(n or 0), float(d or 0)
    return (100.0 * n / d) if d else 0.0


# ---------------------------------------------------------------------------
# Bundle ingestion — bounded memory regardless of corpus size (see module
# docstring's SCALE section). Only these three top-level members are ever
# read; blobs/, inventory.ttl, embeddings*.npz, shapes.shacl.ttl and
# ontology-mapping.ttl are skipped without extraction.
# ---------------------------------------------------------------------------

WANTED_MEMBERS = {"run_manifest.json", "concepts.json", "enrichments.jsonl"}


@dataclass
class Bundle:
    repo_name: str
    manifest: dict[str, Any]
    top_concepts: list[dict[str, Any]] = field(default_factory=list)
    concept_descriptions: dict[str, str] = field(default_factory=dict)
    file_samples: list[dict[str, str]] = field(default_factory=list)
    enrichment_model: str | None = None
    concept_stream_used_ijson: bool = False
    related_concepts: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    risks: list[dict[str, str]] = field(default_factory=list)
    parts: list[dict[str, Any]] = field(default_factory=list)
    decomposition_meta: dict[str, Any] = field(default_factory=dict)
    buildplan_meta: dict[str, Any] = field(default_factory=dict)


def _top_k_from_items(items: Any, k: int) -> list[dict[str, Any]]:
    heap: list[tuple[int, str, dict[str, Any]]] = []
    for label, entry in items:
        if not isinstance(entry, dict):
            continue
        freq = int(entry.get("frequency", 0) or 0)
        rec = {
            "label": str(entry.get("label", label)),
            "frequency": freq,
            "file_count": int(entry.get("file_count", 0) or 0),
            "alt_labels": list(entry.get("alt_labels") or [])[:3],
        }
        if len(heap) < k:
            heapq.heappush(heap, (freq, str(label), rec))
        elif freq > heap[0][0]:
            heapq.heapreplace(heap, (freq, str(label), rec))
    return sorted((rec for _, _, rec in heap), key=lambda r: (-r["frequency"], r["label"]))


def _load_top_concepts(fileobj: Any, k: int) -> tuple[list[dict[str, Any]], bool]:
    try:
        import ijson  # optional: streaming top-K without materializing the file
    except ImportError:
        data = json.load(fileobj)
        return _top_k_from_items((data.get("concepts") or {}).items(), k), False
    return _top_k_from_items(ijson.kvitems(fileobj, "concepts"), k), True


def _load_related_concepts(fileobj: Any, top_labels: set[str],
                            per_concept: int = 4) -> dict[str, list[tuple[str, int]]]:
    """A second bounded pass over the same ``concepts.json`` member (the tar
    is opened random-access, so re-extracting is cheap) — filters the
    co-occurrence edge list down to pairs where BOTH endpoints are already in
    the selected top-K, so memory stays O(K^2) worst case, never O(all
    co-occurrence edges) regardless of corpus size."""
    try:
        import ijson
        items = ijson.items(fileobj, "cooccurrence.item")
    except ImportError:
        data = json.load(fileobj)
        items = data.get("cooccurrence") or []
    related: dict[str, list[tuple[str, int]]] = {}
    for entry in items:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue
        a, b, count = entry[0], entry[1], entry[2]
        if a in top_labels and b in top_labels and a != b:
            related.setdefault(a, []).append((b, int(count)))
            related.setdefault(b, []).append((a, int(count)))
    return {k: sorted(v, key=lambda p: -p[1])[:per_concept] for k, v in related.items()}


def _stream_enrichments(
    fileobj: Any, sample_n: int,
) -> tuple[dict[str, str], list[dict[str, str]], str | None]:
    """Single sequential pass. ``concept_description`` rows are naturally few
    (the pipeline curates them); ``file_summary`` rows are reservoir-sampled to
    ``sample_n`` so this stays O(sample_n) regardless of corpus size."""
    concept_desc: dict[str, str] = {}
    model: str | None = None
    reservoir: list[dict[str, str]] = []
    seen = 0
    rng = random.Random(0)  # fixed seed: a report is reproducible for one bundle
    for raw in fileobj:
        line = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        model = model or rec.get("model")
        kind = rec.get("kind")
        if kind == "concept_description":
            target = rec.get("target")
            if target:
                concept_desc[target] = rec.get("text", "")
        elif kind == "file_summary":
            seen += 1
            item = {"path": rec.get("target", ""), "text": rec.get("text", ""),
                     "prompt_sha": rec.get("prompt_sha", ""), "generated_at": rec.get("generated_at", "")}
            if len(reservoir) < sample_n:
                reservoir.append(item)
            else:
                j = rng.randint(0, seen - 1)
                if j < sample_n:
                    reservoir[j] = item
    reservoir.sort(key=lambda r: r["path"])
    return concept_desc, reservoir, model


def _load_sidecar_analysis(tar_path: str, repo_name: str) -> dict[str, Any]:
    """Best-effort, optional enrichment: a codebase-mapper recomposer/decomposer
    run can drop ``<repo>.buildplan.yaml`` (risk register, build steps) and
    ``<repo>.decomposition.yaml`` (confidence-tagged architectural parts) next
    to the bundle tar. Neither is part of the tar's own scale contract — these
    are pre-scoped, single-repo artifacts (not a Linux-kernel-scale hazard the
    way inventory.ttl is), so this loads them whole when present and is a
    silent no-op when absent (the report reads identically either way, just
    without the risk register / decomposition chapters)."""
    out: dict[str, Any] = {"risks": [], "parts": [], "decomposition_meta": {}, "buildplan_meta": {}}
    base_dir = os.path.dirname(os.path.abspath(tar_path))
    buildplan_path = os.path.join(base_dir, f"{repo_name}.buildplan.yaml")
    decomposition_path = os.path.join(base_dir, f"{repo_name}.decomposition.yaml")
    if os.path.isfile(buildplan_path):
        with open(buildplan_path, "r", encoding="utf-8") as fh:
            bp = yaml.safe_load(fh) or {}
        intent = bp.get("architecture_intent") or {}
        out["risks"] = list(intent.get("known_violations_to_not_replicate_blindly") or [])
        out["buildplan_meta"] = {
            "n_steps": len(bp.get("steps") or []),
            "n_skipped_phases": len(bp.get("skipped_phases") or []),
            "n_open_assumptions": len(bp.get("open_assumptions") or []),
            "style": intent.get("style"), "style_confidence": intent.get("confidence"),
        }
    if os.path.isfile(decomposition_path):
        with open(decomposition_path, "r", encoding="utf-8") as fh:
            dc = yaml.safe_load(fh) or {}
        out["parts"] = list(dc.get("parts") or [])
        out["decomposition_meta"] = {
            "n_relationships": len(dc.get("relationships") or []),
            "n_quality_gates": len(dc.get("quality_gates") or []),
            "n_cycle_resolutions": len(dc.get("cycle_resolutions") or []),
        }
    return out


def load_bundle(tar_path: str, *, top_concepts: int = 150, file_sample: int = 50,
                 related_scope: int = 150) -> Bundle:
    manifest: dict[str, Any] | None = None
    concepts: list[dict[str, Any]] = []
    used_ijson = False
    concept_desc: dict[str, str] = {}
    file_samples: list[dict[str, str]] = []
    enrichment_model: str | None = None
    related: dict[str, list[tuple[str, int]]] = {}

    with tarfile.open(tar_path, mode="r:*") as tar:
        members: dict[str, tarfile.TarInfo] = {}
        for m in tar.getmembers():  # header-only scan; blob *content* is never read
            if not m.isfile() or "/blobs/" in m.name:
                continue
            base = os.path.basename(m.name)
            if base in WANTED_MEMBERS and base not in members:
                members[base] = m
        if "run_manifest.json" in members:
            fh = tar.extractfile(members["run_manifest.json"])
            if fh is not None:
                manifest = json.load(fh)
        if "concepts.json" in members:
            fh = tar.extractfile(members["concepts.json"])
            if fh is not None:
                concepts, used_ijson = _load_top_concepts(fh, top_concepts)
            if concepts:
                fh2 = tar.extractfile(members["concepts.json"])  # 2nd pass: same member, re-extracted
                if fh2 is not None:
                    # bounded independent of top_concepts: a full-vocabulary appendix
                    # (top_concepts in the thousands) must not turn the O(K^2)
                    # co-occurrence pass into an O(vocab^2) one
                    seed = {c["label"] for c in concepts[:min(len(concepts), related_scope)]}
                    related = _load_related_concepts(fh2, seed)
        if "enrichments.jsonl" in members:
            fh = tar.extractfile(members["enrichments.jsonl"])
            if fh is not None:
                concept_desc, file_samples, enrichment_model = _stream_enrichments(fh, file_sample)

    if manifest is None:
        raise ValueError(f"{tar_path}: no run_manifest.json found — not a codebase-mapper bundle")

    repo_name = manifest.get("repo_name") or os.path.splitext(os.path.basename(tar_path))[0]
    sidecar = _load_sidecar_analysis(tar_path, repo_name)
    return Bundle(
        repo_name=repo_name, manifest=manifest, top_concepts=concepts, related_concepts=related,
        concept_descriptions=concept_desc, file_samples=file_samples,
        enrichment_model=enrichment_model, concept_stream_used_ijson=used_ijson,
        risks=sidecar["risks"], parts=sidecar["parts"],
        decomposition_meta=sidecar["decomposition_meta"], buildplan_meta=sidecar["buildplan_meta"],
    )


# ---------------------------------------------------------------------------
# Visual builders — every figure is a plain FrameForge group sized to fit
# the report's A4 content width (see REPORT_CONTENT_W below).
# ---------------------------------------------------------------------------

REPORT_CONTENT_W = 480.0


def _balanced_rows(entries: list[Any], max_per_row: int) -> list[list[Any]]:
    """Chunk into evenly-sized rows (5 items @ max=4 -> [3, 2], not [4, 1]) —
    a lopsided last row reads as a layout bug, not intentional grouping."""
    n = len(entries)
    if n <= max_per_row:
        return [entries] if entries else []
    rows_n = -(-n // max_per_row)  # ceil
    per_row = -(-n // rows_n)
    return [entries[i:i + per_row] for i in range(0, n, per_row)]


_STAT_PAD = 14.0
_STAT_GAP_V = 8.0


def _stat_card_height(label: str, value: str, *, value_size: float, content_w: float) -> tuple[float, float, float]:
    """Real SDK-measured height (frameforge.sdk.metrics.text_height), not a
    guessed constant — a fixed 16px single-line label box is exactly what
    silently dropped "PHASES"/"ASSUMPTIONS"/"RESOLUTIONS" off real stat
    cards before this fix: multi-word tracked-caps labels wrap to 2 lines
    at narrow (4-per-row) card widths, and a box sized for 1 line clips
    the 2nd. Returns (card_h, value_h, label_h)."""
    value_h = text_height(value, width=content_w, font_family=FONT_SANS, font_size=value_size,
                          line_height=1.15, bold=True)
    label_h = text_height(label.upper(), width=content_w, font_family=FONT_SANS, font_size=SIZE_CAPTION,
                          line_height=1.3, bold=True)
    return _STAT_PAD + value_h + _STAT_GAP_V + label_h + _STAT_PAD, value_h, label_h


def _stat(x: float, y: float, w: float, label: str, value: str, *, ink: str, quiet: str,
          value_size: float = SIZE_STAT, card_h: float | None = None) -> tuple[list[dict], float]:
    """A bordered stat card (operator-chosen over the borderless typographic
    tick treatment via rendered options, 2026-07-09): a thin quiet-toned
    outline, the number top-left, the tracked-caps label bottom-left.
    Returns (objects, card_h) — card_h may be supplied by the caller so every
    card in one row shares the same (tallest-needed) height."""
    card_w = max(40.0, w - 10.0)
    content_w = card_w - 2 * _STAT_PAD
    computed_h, value_h, label_h = _stat_card_height(label, value, value_size=value_size,
                                                      content_w=content_w)
    card_h = card_h if card_h is not None else computed_h
    objs = [
        {"type": "rect", "box": [x, y, card_w, card_h], "fill": "none", "stroke": PALETTE["quiet1"],
         "stroke_style": {"stroke_width": 1.0}, "radius": 6, "decorative": True},
        {"type": "text", "box": [x + _STAT_PAD, y + _STAT_PAD, content_w, value_h], "text": value,
         "style": {"font_family": FONT_SANS, "font_size": value_size, "font_weight": 800,
                   "color": ink, "letter_spacing": -0.6, "vertical_align": "top"}},
        {"type": "text", "box": [x + _STAT_PAD, y + _STAT_PAD + value_h + _STAT_GAP_V, content_w, label_h],
         "text": label.upper(),
         "style": {"font_family": FONT_SANS, "font_size": SIZE_CAPTION, "font_weight": 600,
                   "color": quiet, "letter_spacing": 1.1, "vertical_align": "top"}},
    ]
    return objs, card_h


def _stat_row(entries: list[tuple[str, str]], *, avail_w: float = REPORT_CONTENT_W,
              row_gap: float = 22.0, gap: float = 20.0, max_per_row: int = 3,
              ink: str = PALETTE["ink"], quiet: str = PALETTE["quiet2"],
              value_size: float = SIZE_STAT) -> dict:
    """Stats laid out with real air between columns (steelyard, not a packed
    grid) — generous gaps read as composed; tight equal-width tiles read as
    a dashboard, regardless of what sits inside them. Card height is
    measured (max needed across the row), not assumed, so every card in a
    row lines up and none clips its own label."""
    if not entries:
        return {"type": "group", "box": [0, 0, 10, 10], "children": []}
    objs: list[dict] = []
    y = 0.0
    total_w = 0.0
    for row in _balanced_rows(entries, max_per_row):
        n = len(row)
        col_w = (avail_w - (n - 1) * gap) / n
        content_w = max(40.0, col_w - 10.0) - 2 * _STAT_PAD
        row_card_h = max(_stat_card_height(l, v, value_size=value_size, content_w=content_w)[0]
                         for l, v in row)
        x = 0.0
        for label, value in row:
            card_objs, _ = _stat(x, y, col_w, label, value, ink=ink, quiet=quiet,
                                 value_size=value_size, card_h=row_card_h)
            objs.extend(card_objs)
            x += col_w + gap
        total_w = max(total_w, x - gap)
        y += row_card_h + row_gap
    return {"type": "group", "box": [0, 0, total_w, y - row_gap], "children": objs}


def _language_headline(files_by_language: dict[str, int], locale: str, *,
                        top_n: int = 8, w: float = REPORT_CONTENT_W) -> dict:
    """fastapi is ~98% Python; a donut over data this lopsided is one giant
    slice and seven invisible slivers — a chart shape fighting its own data.
    State the dominant language as a headline stat (the honest, legible
    reading of a power-law distribution), then rank the remainder as a quiet
    tick list — no colour is spent distinguishing categories the text labels
    already name."""
    items = sorted(((k, v) for k, v in files_by_language.items() if k != "(none)" and v > 0),
                    key=lambda kv: -kv[1])
    if not items:
        return {"type": "group", "box": [0, 0, 10, 10], "children": []}
    total = sum(v for _, v in items) or 1
    top_lang, top_v = items[0]
    top_pct = 100.0 * top_v / total
    ink, quiet2, quiet1 = PALETTE["ink"], PALETTE["quiet2"], PALETTE["quiet1"]
    objs: list[dict] = [
        {"type": "rect", "box": [0, 0, 22, 2.5], "fill": PALETTE["accent"]},
        {"type": "text", "box": [0, 9, 220, 54], "text": f"{top_pct:.0f}%",
         "style": {"font_family": FONT_SANS, "font_size": SIZE_HEADLINE, "font_weight": 800,
                   "color": PALETTE["accent"], "letter_spacing": -0.8, "vertical_align": "top"}},
        {"type": "text", "box": [0, 64, w, 18],
         "text": f"{top_lang} — {fmt_int(top_v, locale)} of {fmt_int(total, locale)} files",
         "style": {"font_family": FONT_SANS, "font_size": SIZE_BODY, "font_weight": 600,
                   "color": ink, "vertical_align": "top"}},
    ]
    rest = items[1:top_n]
    y = 96.0
    max_rest = max((v for _, v in rest), default=1)
    for lang, v in rest:
        tick_w = 4.0 + 90.0 * (v / max_rest)
        objs.append({"type": "rect", "box": [0, y + 4, tick_w, 5], "fill": quiet1, "radius": 2})
        objs.append({"type": "text", "box": [104, y, 140, 16], "text": lang,
                     "style": {"font_family": FONT_SANS, "font_size": SIZE_LABEL, "color": ink,
                               "vertical_align": "top"}})
        objs.append({"type": "text", "box": [w - 70, y, 70, 16], "text": fmt_int(v, locale),
                     "style": {"font_family": FONT_SANS, "font_size": SIZE_LABEL, "color": quiet2,
                               "align": "right", "vertical_align": "top"}})
        y += 21.0
    tail = items[top_n:]
    if tail:
        objs.append({"type": "text", "box": [104, y, w - 104, 16],
                     "text": f"+ {fmt_int(len(tail), locale)} more", "style": {
                         "font_family": FONT_SANS, "font_size": SIZE_CAPTION, "color": quiet2,
                         "vertical_align": "top"}})
        y += 21.0
    return {"type": "group", "box": [0, 0, w, y], "children": objs}


def _ranked_bars(items: list[tuple[str, float]], locale: str, *,
                  box_w: float = REPORT_CONTENT_W, row_h: float = 22.0,
                  label_w: float = 116.0, value_w: float = 56.0,
                  value_fmt: Any = None) -> dict:
    """One shared ranked-bar treatment for both file types and concepts —
    the deliberate repeat is a rhythm, not duplication (same grammar
    wherever a ranked count appears in this report). Colour carries rank
    alone, via one accent's tone ladder — every bar already has a text
    label, so a rainbow keyed to array index would encode nothing a reader
    can use."""
    n = len(items)
    if n == 0:
        return {"type": "group", "box": [0, 0, 10, 10], "children": []}
    value_fmt = value_fmt or (lambda v: fmt_int(v, locale))
    max_v = max(v for _, v in items) or 1
    box_h = n * row_h
    bar_w = box_w - label_w - value_w
    frame = Frame(domain=(0, 0, max_v * 1.02, n), box=(label_w, 0, bar_w, box_h))
    shades = list(reversed(harmony_of_scale(PALETTE["accent"], n=min(max(n, 2), 7))))
    ink = PALETTE["ink"]
    objs: list[dict] = []
    for i, (label, v) in enumerate(items):
        y = n - i - 0.5
        left = frame.point(0, y)
        right = frame.point(v, y)
        bar_h = row_h * 0.52
        objs.append({"type": "rect",
                     "box": [left.x, left.y - bar_h / 2, max(2.0, right.x - left.x), bar_h],
                     "fill": shades[min(i, len(shades) - 1)]})
        objs.append({"type": "text", "box": [0, left.y - row_h / 2, label_w - 10, row_h], "text": label,
                     "style": {"font_family": FONT_SANS, "font_size": SIZE_LABEL, "align": "right",
                               "vertical_align": "middle", "color": ink}})
        objs.append({"type": "text", "box": [right.x + 8, left.y - row_h / 2, value_w, row_h],
                     "text": value_fmt(v),
                     "style": {"font_family": FONT_SANS, "font_size": SIZE_LABEL, "font_weight": 700,
                               "vertical_align": "middle", "color": ink}})
    return {"type": "group", "box": [0, 0, box_w, box_h], "children": objs}


def _masthead(bundle: "Bundle", locale: str, *, w: float = REPORT_CONTENT_W) -> dict:
    """A solid accent-colour hero band with reversed (paper-coloured) type —
    operator-chosen ("accent band, bold") over a dark-ink band and a
    quiet rule-framed treatment via rendered options, 2026-07-09. Sized to
    its own flow box, not page-bled: a figure's box is wherever the flow
    engine places it (after the chapter's own numbered heading), not the
    page origin — a negative-offset "bleed" rect there overlaps the heading
    above it instead of reaching the page edge."""
    t = T(locale)
    band_h = 168.0
    on_band = PALETTE["ground"]  # symmetric-contrast-verified against ACCENT above
    m = bundle.manifest
    objs: list[dict] = [
        {"type": "rect", "box": [0, 0, w, band_h], "fill": PALETTE["accent"], "decorative": True},
        {"type": "text", "box": [0, 26, w, 16], "text": t("masthead_eyebrow"),
         "style": {"font_family": FONT_SANS, "font_size": SIZE_CAPTION, "font_weight": 700,
                   "color": on_band, "letter_spacing": 2.0, "vertical_align": "top"}},
        {"type": "text", "box": [0, 44, w, 70], "text": bundle.repo_name,
         "style": {"font_family": FONT_SANS, "font_size": 52, "font_weight": 800,
                   "color": on_band, "letter_spacing": -1.2, "vertical_align": "top",
                   "overflow": "clip"}},
        {"type": "text", "box": [0, 120, w, 16],
         "text": t("masthead_meta", commit=str(m.get("commit_sha", "?"))[:12],
                   date=fmt_date(m.get("generated_at", ""), locale), tool=m.get("tool_version", "?")),
         "style": {"font_family": FONT_SANS, "font_size": SIZE_CAPTION, "color": on_band,
                   "vertical_align": "top"}},
    ]
    return {"type": "group", "box": [0, 0, w, band_h], "children": objs}


def _eyebrow(text: str, *, w: float = REPORT_CONTENT_W) -> dict:
    """A tick + small tracked caps ahead of a section — the "PART N" grammar
    that gives a section a threshold instead of just a bigger font."""
    return {"type": "group", "box": [0, 0, w, 16], "children": [
        {"type": "rect", "box": [0, 5, 16, 2.5], "fill": PALETTE["accent"]},
        {"type": "text", "box": [24, 0, w - 24, 16], "text": text.upper(),
         "style": {"font_family": FONT_SANS, "font_size": SIZE_CAPTION, "font_weight": 700,
                   "color": PALETTE["quiet2"], "letter_spacing": 1.6, "vertical_align": "top"}},
    ]}


def _chapter_opener(number: int, total: int, locale: str, *, w: float = REPORT_CONTENT_W) -> dict:
    """A slim accent rule + tracked kicker under every chapter heading — one
    consistent opening beat repeated chapter to chapter (rhythm, not a
    one-off flourish on chapter 1 alone)."""
    t = T(locale)
    return {"type": "group", "box": [0, 0, w, 20], "children": [
        {"type": "rect", "box": [0, 0, w, 3], "fill": PALETTE["accent"]},
        {"type": "text", "box": [0, 8, w, 14], "text": t("chapter_kicker", n=number, total=total),
         "style": {"font_family": FONT_SANS, "font_size": SIZE_CAPTION, "font_weight": 600,
                   "color": PALETTE["quiet2"], "letter_spacing": 1.4, "vertical_align": "top"}},
    ]}


def _verbatim_receipt(sample: dict[str, str], model: str | None, locale: str, *,
                       w: float = REPORT_CONTENT_W) -> dict:
    """Quote exactly one sampled enrichment, byte-for-byte, with its full
    provenance line — the standard every other AI-generated line in this
    report is held to (PALS's Law), made visible once instead of asserted
    once in a disclaimer and then forgotten. Box height is the SDK's own
    measured wrap height (frameforge.sdk.metrics — real glyph advances when
    fontTools is installed, the same proxy the renderer itself falls back to
    otherwise), not a hand-rolled chars-per-line guess: an early version of
    this function estimated wrapping itself and silently dropped a line on
    two of eight real risk descriptions before this fix."""
    ink, quiet2, accent = PALETTE["ink"], PALETTE["quiet2"], PALETTE["accent"]
    quote = f"“{truncate(sample.get('text', ''), 260)}”"
    prompt = (sample.get("prompt_sha") or "")[:12]
    receipt = (f"{sample.get('path', '?')} — {model or '?'} · prompt {prompt}… · "
               f"{fmt_date(sample.get('generated_at', ''), locale)}")
    body_w = w - 18
    quote_h = text_height(quote, width=body_w, font_family=FONT_SERIF, font_size=SIZE_BODY,
                          line_height=1.35) + 6
    receipt_h = text_height(receipt, width=body_w, font_family=FONT_SANS, font_size=SIZE_CAPTION,
                            line_height=1.35) + 4
    total_h = quote_h + 12 + receipt_h
    objs = [
        {"type": "rect", "box": [0, 0, 3, total_h], "fill": accent},
        {"type": "text", "box": [18, 2, w - 18, quote_h], "text": quote,
         "style": {"font_family": FONT_SERIF, "font_size": SIZE_BODY, "font_style": "italic",
                   "color": ink, "vertical_align": "top"}},
        {"type": "text", "box": [18, quote_h + 8, w - 18, receipt_h], "text": receipt,
         "style": {"font_family": FONT_SANS, "font_size": SIZE_CAPTION, "color": quiet2,
                   "vertical_align": "top", "overflow": "clip"}},
    ]
    return {"type": "group", "box": [0, 0, w, total_h], "children": objs}


def _progress_marker(text: str, *, w: float = REPORT_CONTENT_W) -> dict:
    """A quiet 'N–M of TOTAL' orientation line ahead of one table chunk.

    FrameForge's flow renderer has no running-header/footer/page-number
    implementation (``PageMaster.running`` and ``master.fixed`` are declared
    in the schema — docs/models/frameforge.py — but grep across
    src/frameforge/rendering/ turns up zero handling of them; only ``margin``
    is honored). A true running header updating per physical page isn't
    available from the SDK client, so this per-CHUNK marker is the closest
    honest substitute: since a chunk is sized to usually land on one page,
    it reads as a de facto page marker without claiming to be one."""
    return {"type": "text", "box": [0, 0, w, 14], "text": text,
            "style": {"font_family": FONT_SANS, "font_size": SIZE_CAPTION, "font_weight": 600,
                      "color": PALETTE["quiet2"], "letter_spacing": 0.8, "vertical_align": "top"}}


def _chunked_table(ch: Any, columns: list[Any], rows: list[list[Any]], *,
                    chunk: int = 24, row_height: float | None = None,
                    progress_label: str | None = None, locale: str = "en_US") -> None:
    """The flow table doesn't re-emit its header row across a page break
    (renderer.py emit_table/emit_row), so large tables are split into
    header-bearing chunks small enough to usually land on one page. When
    ``progress_label`` is given (a ``{lo}``/``{hi}``/``{total}`` format
    string), each chunk gets a "1–24 of 3,822" marker ahead of it — the
    difference between a wall of undifferentiated tables and a navigable one."""
    if not rows:
        return
    extra: dict[str, Any] = {"row_height": row_height} if row_height else {}
    total = len(rows)
    for i in range(0, total, chunk):
        if progress_label:
            lo, hi = i + 1, min(i + chunk, total)
            label = progress_label.format(lo=fmt_int(lo, locale), hi=fmt_int(hi, locale),
                                          total=fmt_int(total, locale))
            ch.figure(_progress_marker(label), caption=None, keep_with_caption=False)
        ch.table(columns, rows[i:i + chunk], header=True, **extra)


def _risk_callout(kind: str, description: str, index: int, total: int, *,
                   w: float = REPORT_CONTENT_W) -> dict:
    """A named architectural risk as a callout, not a table row: a warn-tone
    rule, a kind tag, the full description — sourced verbatim from the
    recomposer's ``known_violations_to_not_replicate_blindly`` (real,
    evidence-backed structural analysis, not a raw frequency count). Height
    comes from the SDK's own measured wrap (frameforge.sdk.metrics.text_height),
    not an estimate — see _verbatim_receipt's docstring for why that matters."""
    ink, warn = PALETTE["ink"], PALETTE["warn"]
    kind_label = kind.replace("_", " ").upper()
    body_h = text_height(description, width=w - 28, font_family=FONT_SANS, font_size=SIZE_LABEL,
                         line_height=1.4) + 4
    total_h = 26 + body_h + 10
    objs = [
        {"type": "rect", "box": [0, 0, 4, total_h], "fill": warn},
        {"type": "text", "box": [16, 2, w - 16, 16], "text": f"RISK {index} OF {total} — {kind_label}",
         "style": {"font_family": FONT_SANS, "font_size": SIZE_CAPTION, "font_weight": 700,
                   "color": warn, "letter_spacing": 1.0, "vertical_align": "top"}},
        {"type": "text", "box": [16, 22, w - 16, body_h], "text": description,
         "style": {"font_family": FONT_SANS, "font_size": SIZE_LABEL, "color": ink,
                   "vertical_align": "top"}},
    ]
    return {"type": "group", "box": [0, 0, w, total_h], "children": objs}


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------

def _ch_overview(book: BookBuilder, bundle: Bundle, locale: str, total: int) -> None:
    t = T(locale)
    m = bundle.manifest
    ch = book.chapter(t("ch1_title"))
    ch.figure(_chapter_opener(ch.number, total, locale), caption=None, keep_with_caption=False)
    ch.figure(_masthead(bundle, locale), caption=None, keep_with_caption=False)
    ch.para(t("ch1_intro", repo=bundle.repo_name, commit=str(m.get("commit_sha", "?"))[:12],
              date=fmt_date(m.get("generated_at", ""), locale), tool=m.get("tool_version", "?")))
    fbt = m.get("files_by_type", {})
    ch.figure(_stat_row([
        (t("kpi_total_files"), fmt_int(m.get("counts", {}).get("files", 0), locale)),
        (t("kpi_source_code"), fmt_int(fbt.get("source_code", 0), locale)),
        (t("kpi_test_code"), fmt_int(fbt.get("test_code", 0), locale)),
        (t("kpi_documentation"), fmt_int(fbt.get("documentation", 0), locale)),
    ]), caption=t("overview_kpi_caption"))
    ch.figure(_eyebrow(t("lang_chart_title")), caption=None)
    ch.figure(_language_headline(m.get("files_by_language", {}), locale), caption=t("lang_chart_caption"))
    ch.figure(_eyebrow(t("filetype_chart_title")), caption=None)
    filetype_items = sorted(((filetype_label(k, locale), v) for k, v in fbt.items() if v > 0),
                             key=lambda kv: -kv[1])
    ch.figure(_ranked_bars(filetype_items, locale), caption=t("filetype_chart_caption"))


def _ch_ast(book: BookBuilder, bundle: Bundle, locale: str, total: int) -> None:
    t = T(locale)
    ast = bundle.manifest.get("ast_coverage", {})
    by_lang = ast.get("by_language", {})
    totals = ast.get("totals", {})
    ch = book.chapter(t("ch2_title"))
    ch.figure(_chapter_opener(ch.number, total, locale), caption=None, keep_with_caption=False)
    ch.para(t("ch2_intro"))
    ch.figure(_stat_row([
        (t("kpi_ast_coverage"), f"{pct(totals.get('files_with_ast'), totals.get('files')):.0f}%"),
        (t("kpi_parse_errors"), fmt_int(totals.get("files_with_parse_errors", 0), locale)),
        (t("kpi_symbols"), fmt_int(totals.get("symbols_extracted", 0), locale)),
        (t("kpi_imports"), fmt_int(totals.get("imports_extracted", 0), locale)),
    ]), caption=t("ast_kpi_caption"))
    rows = []
    for lang, d in sorted(by_lang.items(), key=lambda kv: -kv[1].get("files", 0))[:12]:
        rows.append([lang, fmt_int(d.get("files", 0), locale), fmt_int(d.get("files_with_ast", 0), locale),
                     fmt_int(d.get("symbols_extracted", 0), locale), fmt_int(d.get("imports_extracted", 0), locale)])
    columns = [t("col_language"), t("col_files"), t("col_files_with_ast"), t("col_symbols"), t("col_imports")]
    _chunked_table(ch, columns, rows)


def _ch_deps(book: BookBuilder, bundle: Bundle, locale: str, total: int) -> None:
    t = T(locale)
    counts = bundle.manifest.get("counts", {})
    ch = book.chapter(t("ch3_title"))
    ch.figure(_chapter_opener(ch.number, total, locale), caption=None, keep_with_caption=False)
    ch.para(t("ch3_intro"))
    ch.figure(_stat_row([
        (t("kpi_import_edges"), fmt_int(counts.get("import_edges", 0), locale)),
        (t("kpi_import_external"), fmt_int(counts.get("import_external_edges", 0), locale)),
        (t("kpi_declares_dep"), fmt_int(counts.get("declares_dependency_edges", 0), locale)),
        (t("kpi_pins_dep"), fmt_int(counts.get("pins_dependency_edges", 0), locale)),
        (t("kpi_tests_edges"), fmt_int(counts.get("tests_edges", 0), locale)),
    ], value_size=SIZE_SUBHEAD * 1.6), caption=t("deps_kpi_caption"))


def _ch_concepts(book: BookBuilder, bundle: Bundle, locale: str, total: int, *,
                  top_n_chart: int = 15, top_n_desc: int = 6) -> None:
    t = T(locale)
    ch = book.chapter(t("ch4_title"))
    ch.figure(_chapter_opener(ch.number, total, locale), caption=None, keep_with_caption=False)
    ch.para(t("ch4_intro", n=fmt_int(len(bundle.top_concepts), locale)))
    if bundle.top_concepts:
        items = [(c["label"], c["frequency"]) for c in bundle.top_concepts[:top_n_chart]]
        ch.figure(_ranked_bars(items, locale), caption=t("concept_chart_caption"))
    columns = [t("col_concept"), t("col_frequency"), t("col_files")]
    rows = [[c["label"], fmt_int(c["frequency"], locale), fmt_int(c["file_count"], locale)]
            for c in bundle.top_concepts]
    _chunked_table(ch, columns, rows)

    if bundle.related_concepts:
        ch.section(t("ch4_related_section"))
        ch.para(t("ch4_related_intro"))
        rel_columns = [t("col_concept"), t("col_related")]
        rel_rows = []
        for c in bundle.top_concepts:
            partners = bundle.related_concepts.get(c["label"])
            if partners:
                rel_rows.append([c["label"],
                                  ", ".join(f"{p} ({fmt_int(n, locale)})" for p, n in partners)])
        _chunked_table(ch, rel_columns, rel_rows, chunk=20)

    described = [c for c in bundle.top_concepts[:top_n_desc] if c["label"] in bundle.concept_descriptions]
    if described:
        ch.section(t("ch4_commentary_section"))
        ch.figure(badge(t("llm_generated", model=bundle.enrichment_model or "?"), tone="warn",
                        theme=REPORT_THEME), caption=None)
        ch.para(t("ch4_disclaimer"))
        for c in described:
            ch.para(f"{c['label'].upper()} — {bundle.concept_descriptions[c['label']]}")


def _ch_file_digest(book: BookBuilder, bundle: Bundle, locale: str, total: int) -> None:
    t = T(locale)
    ch = book.chapter(t("ch5_title"))
    ch.figure(_chapter_opener(ch.number, total, locale), caption=None, keep_with_caption=False)
    ch.para(t("ch5_intro", n=fmt_int(len(bundle.file_samples), locale)))
    if bundle.file_samples:
        ch.figure(_eyebrow(t("receipt_title")), caption=None)
        ch.para(t("receipt_note"))
        by_len = sorted(bundle.file_samples, key=lambda s: len(s.get("text", "")))
        picks = {by_len[-1]["path"]: by_len[-1]}          # longest
        if len(by_len) > 2:
            picks[by_len[len(by_len) // 2]["path"]] = by_len[len(by_len) // 2]  # median
        if len(by_len) > 1:
            picks[by_len[0]["path"]] = by_len[0]          # shortest
        for sample in sorted(picks.values(), key=lambda s: s["path"]):
            ch.figure(_verbatim_receipt(sample, bundle.enrichment_model, locale), caption=None)
        ch.figure(badge(t("llm_generated", model=bundle.enrichment_model or "?"), tone="warn",
                        theme=REPORT_THEME), caption=None)
    # One line per cell: the flow table's cell wrapper clips at its computed
    # line cap rather than growing the row, so a "summary" here means a short
    # single-line teaser, not a wrapped paragraph.
    columns = [{"label": t("col_path"), "width": "38%"}, {"label": t("col_summary"), "width": "62%"}]
    rows = [[truncate(s["path"], 32), truncate(s["text"], 52)] for s in bundle.file_samples]
    _chunked_table(ch, columns, rows, chunk=18)


def _ch_provenance(book: BookBuilder, bundle: Bundle, locale: str, total: int) -> None:
    t = T(locale)
    m = bundle.manifest
    ch = book.chapter(t("ch6_title"))
    ch.figure(_chapter_opener(ch.number, total, locale), caption=None, keep_with_caption=False)
    conforms = bool((m.get("shacl_self_check") or {}).get("conforms"))
    ch.figure(badge(t("shacl_pass") if conforms else t("shacl_fail"),
                    tone="good" if conforms else "bad", theme=REPORT_THEME), caption=None)
    ch.para(t("ch6_intro"))
    columns = [t("col_artifact"), t("col_size"), t("col_sha256")]
    rows = []
    for name, art in (m.get("artifacts") or {}).items():
        sha = art.get("sha256") or ""
        rows.append([name, fmt_bytes(art.get("size_bytes", 0), locale), (sha[:16] + "…") if sha else "?"])
    _chunked_table(ch, columns, rows)
    ch.para(t("ch6_closing"))


def _ch_risks(book: BookBuilder, bundle: Bundle, locale: str, total: int) -> None:
    """Optional: only emitted when a sibling ``<repo>.buildplan.yaml`` sits
    next to the tar (see _load_sidecar_analysis). Real, evidence-backed
    architectural risk content — not derived from anything this script
    computes itself."""
    if not bundle.risks:
        return
    t = T(locale)
    ch = book.chapter(t("ch7_title"))
    ch.figure(_chapter_opener(ch.number, total, locale), caption=None, keep_with_caption=False)
    ch.para(t("ch7_intro", n=fmt_int(len(bundle.risks), locale)))
    bm = bundle.buildplan_meta
    if bm:
        ch.figure(_stat_row([
            (t("kpi_risks"), fmt_int(len(bundle.risks), locale)),
            (t("kpi_build_steps"), fmt_int(bm.get("n_steps", 0), locale)),
            (t("kpi_skipped_phases"), fmt_int(bm.get("n_skipped_phases", 0), locale)),
            (t("kpi_open_assumptions"), fmt_int(bm.get("n_open_assumptions", 0), locale)),
        ]), caption=t("risk_kpi_caption"))
    n = len(bundle.risks)
    for i, risk in enumerate(bundle.risks, 1):
        ch.figure(_risk_callout(risk.get("kind", "?"), risk.get("description", ""), i, n),
                  caption=None, keep_with_caption=False)


def _ch_decomposition(book: BookBuilder, bundle: Bundle, locale: str, total: int) -> None:
    """Optional: only emitted when a sibling ``<repo>.decomposition.yaml``
    sits next to the tar. Confidence-tagged architectural parts, not a raw
    frequency count — the antidote to a wall of undifferentiated tables."""
    if not bundle.parts:
        return
    t = T(locale)
    ch = book.chapter(t("ch8_title"))
    ch.figure(_chapter_opener(ch.number, total, locale), caption=None, keep_with_caption=False)
    ch.para(t("ch8_intro", n=fmt_int(len(bundle.parts), locale)))
    dm = bundle.decomposition_meta
    ch.figure(_stat_row([
        (t("kpi_parts"), fmt_int(len(bundle.parts), locale)),
        (t("kpi_relationships"), fmt_int(dm.get("n_relationships", 0), locale)),
        (t("kpi_quality_gates"), fmt_int(dm.get("n_quality_gates", 0), locale)),
        (t("kpi_cycle_resolutions"), fmt_int(dm.get("n_cycle_resolutions", 0), locale)),
    ]), caption=t("decomp_kpi_caption"))

    kind_counts = Counter(p.get("kind") or "?" for p in bundle.parts)
    ch.figure(_eyebrow(t("decomp_kind_title")), caption=None)
    ch.figure(_ranked_bars(sorted(kind_counts.items(), key=lambda kv: -kv[1]), locale),
              caption=t("decomp_kind_caption"))

    ch.figure(_eyebrow(t("decomp_catalog_title")), caption=None)
    columns = [t("col_part"), t("col_kind"), t("col_layer"), t("col_confidence"), t("col_responsibility")]
    rows = []
    for p in sorted(bundle.parts, key=lambda p: (p.get("kind") or "", p.get("name") or "")):
        rows.append([
            truncate(p.get("name", "?"), 40), p.get("kind", "?") or "?", p.get("layer") or "—",
            p.get("responsibility_confidence") or "—", truncate(p.get("responsibility", ""), 70),
        ])
    _chunked_table(ch, columns, rows, chunk=16, progress_label=t("progress_parts"), locale=locale)


# ---------------------------------------------------------------------------
# Book assembly
# ---------------------------------------------------------------------------

def build_book(bundle: Bundle, locale: str) -> dict[str, Any]:
    t = T(locale)
    book = BookBuilder(title=t("book_title", repo=bundle.repo_name), author=t("book_author"),
                       lang=locale.replace("_", "-"), master="report")
    # 6 always-present chapters + the 2 optional sidecar-derived ones — computed
    # once so every chapter's "N of TOTAL" kicker is honest whether or not
    # <repo>.buildplan.yaml / <repo>.decomposition.yaml sit next to the tar.
    total = 6 + (1 if bundle.risks else 0) + (1 if bundle.parts else 0)
    _ch_overview(book, bundle, locale, total)
    _ch_ast(book, bundle, locale, total)
    _ch_deps(book, bundle, locale, total)
    _ch_concepts(book, bundle, locale, total)
    _ch_file_digest(book, bundle, locale, total)
    _ch_provenance(book, bundle, locale, total)
    _ch_risks(book, bundle, locale, total)
    _ch_decomposition(book, bundle, locale, total)

    doc = book.build(validate=False)
    doc.setdefault("defs", {}).setdefault("masters", {})["report"] = {
        "canvas": {"preset": "A4", "orientation": "portrait"},
    }
    doc["profile"] = "report"  # honest genre hint — this is a report, not a book (metadata only)
    validate_document(doc)
    return doc


# ---------------------------------------------------------------------------
# MCP contract + CLI
# ---------------------------------------------------------------------------

DEFAULT_BUNDLE = os.environ.get("CODEBASE_REPORT_BUNDLE", os.path.join(ROOT, "_tmp", "fastapi", "fastapi.tar"))
DEFAULT_LOCALE = os.environ.get("CODEBASE_REPORT_LOCALE", "en_US")


def build() -> dict[str, Any]:
    """MCP run_sdk_client contract: one locale's book from the default bundle."""
    bundle = load_bundle(DEFAULT_BUNDLE)
    locale = DEFAULT_LOCALE if DEFAULT_LOCALE in SUPPORTED_LOCALES else "en_US"
    return build_book(bundle, locale)


def _render_pdf(yaml_path: str, out_dir: str, filename: str) -> None:
    render_pdf = os.path.join(ROOT, "tooling", "render_pdf.py")
    pdf_path = os.path.join(out_dir, filename)
    # --single is a direct output path (NOT joined with --out — that flag only
    # applies to the one-PDF-per-document branch), so it must be given in full.
    cmd = [sys.executable, render_pdf, yaml_path, "--single", pdf_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = result.stderr.strip().splitlines()[-1] if result.stderr else "unknown error"
        print(f"  PDF skipped ({filename}): {tail}")
        print("  Install with: uv sync --group pdfout")
    else:
        print(f"  PDF: {pdf_path}")


def _write_locale(bundle: Bundle, locale: str, out_root: str, *, make_pdf: bool) -> str:
    doc = build_book(bundle, locale)
    out_dir = os.path.join(out_root, locale)
    os.makedirs(out_dir, exist_ok=True)
    yaml_path = os.path.join(out_dir, "report.fg.yaml")
    with open(yaml_path, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc))
    svgs = render_page_svgs(doc, base_dir=out_dir)
    for i, svg in enumerate(svgs, 1):
        with open(os.path.join(out_dir, f"page-{i:02d}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print(f"[{locale}] wrote {len(svgs)} pages to {out_dir}")
    if make_pdf:
        _render_pdf(yaml_path, out_dir, f"{bundle.repo_name}-{locale}.pdf")
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle", nargs="?", default=DEFAULT_BUNDLE,
                    help="path to a codebase-mapper .tar bundle")
    ap.add_argument("--locale", default="en_US,pt_BR",
                    help="comma-separated locales, or 'all' (default: en_US,pt_BR)")
    ap.add_argument("--out", default=None, help="output root (default: _tmp/codebase-report/<repo>)")
    ap.add_argument("--top-concepts", type=int, default=150, help="concepts kept (bounded, any corpus size)")
    ap.add_argument("--file-sample", type=int, default=50, help="file summaries reservoir-sampled")
    ap.add_argument("--full-appendix", action="store_true",
                    help="use the WHOLE concept vocabulary and ALL sampled file summaries "
                         "(overrides --top-concepts/--file-sample with values comfortably above "
                         "the manifest's own totals) — an honest full-coverage appendix, not "
                         "padding; drops the bounded-for-any-corpus-size guarantee, so use this "
                         "for a small/medium repo, not Linux-kernel scale")
    ap.add_argument("--pdf", action="store_true", help="also merge pages into a PDF (needs the pdfout group)")
    args = ap.parse_args(argv)

    locales = SUPPORTED_LOCALES if args.locale == "all" else tuple(
        loc.strip() for loc in args.locale.split(",") if loc.strip())
    unknown = [loc for loc in locales if loc not in SUPPORTED_LOCALES]
    if unknown:
        ap.error(f"unsupported locale(s): {', '.join(unknown)} (supported: {', '.join(SUPPORTED_LOCALES)})")

    top_concepts, file_sample = args.top_concepts, args.file_sample
    if args.full_appendix:
        # a heap of size K / a reservoir of size K holding fewer than K real
        # items just holds everything — no separate "load all" code path needed
        top_concepts, file_sample = 1_000_000, 1_000_000
    bundle = load_bundle(args.bundle, top_concepts=top_concepts, file_sample=file_sample)
    out_root = args.out or os.path.join(ROOT, "_tmp", "codebase-report", bundle.repo_name)
    heap_note = "streaming (ijson)" if bundle.concept_stream_used_ijson else "whole-file json.load fallback"
    print(f"{bundle.repo_name}: {fmt_int(bundle.manifest.get('counts', {}).get('files', 0), 'en_US')} files, "
          f"{len(bundle.top_concepts)} concepts selected [{heap_note}], "
          f"{len(bundle.file_samples)} file summaries sampled")
    for locale in locales:
        _write_locale(bundle, locale, out_root, make_pdf=args.pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
