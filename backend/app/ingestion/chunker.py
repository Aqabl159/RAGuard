"""Semantic-aware text chunker with structural boundary awareness.

Pipeline:
  Step 1 — Structural boundary split (section headings = hard boundaries)
  Step 2 — Semantic boundary detection (paragraph embedding similarity)
  Step 3 — Token-level fallback (sentences at token boundaries)
  Step 4 — Metadata assembly (section_path, heading_level, prev/next links)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from app.config import settings
from app.ingestion.parser import ParsedDocument, DocumentSection, build_section_path
from app.ingestion.tokenizer import count_tokens


@dataclass
class ChunkResult:
    """Output of the chunking pipeline for a single chunk."""
    content: str
    token_count: int
    chunk_index: int
    section_path: str = ""
    heading_level: int = 0
    page_number: int | None = None
    page_number_end: int | None = None
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None


def _split_by_structure(sections, target_tokens, ancestors=None):
    if ancestors is None: ancestors = []
    results = []
    for section in sections:
        cur_anc = ancestors + [section]
        if section.is_leaf:
            results.append((section.content, section, cur_anc))
        else:
            p = section.content
            if p.strip():
                tc = count_tokens(p)
                if tc <= target_tokens:
                    ps = DocumentSection(heading=section.heading, heading_level=section.heading_level, content=p, page_number=section.page_number)
                    results.append((p, ps, ancestors))
                else: results.append((p, section, ancestors))
            results.extend(_split_by_structure(section.subsections, target_tokens, cur_anc))
    return results


def _compute_paragraph_similarities(embeddings):
    if len(embeddings) < 2: return []
    import numpy as np
    embs = np.array(embeddings, dtype=np.float32)
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    embs = embs / norms
    sims = np.sum(embs[:-1] * embs[1:], axis=1)
    return [float(s) for s in sims]


def _heuristic_boundaries(paragraphs):
    if len(paragraphs) <= 1: return []
    splits = []
    for i in range(len(paragraphs) - 1):
        c = paragraphs[i].strip(); n = paragraphs[i+1].strip()
        if not c or not n: splits.append(i)
        elif len(c) < 80 and (c[-1] in "\uFF1A:" or len(c) < 30): splits.append(i)
    return splits


async def _detect_semantic_boundaries(paragraphs, threshold=0.7):
    if len(paragraphs) <= 1: return []
    if any(len(p) < 50 for p in paragraphs): return _heuristic_boundaries(paragraphs)
    try:
        from app.ingestion.embedder import embed_texts
        embs = await embed_texts(paragraphs)
        sims = _compute_paragraph_similarities(embs)
        return [i for i, s in enumerate(sims) if s < threshold]
    except Exception:
        return _heuristic_boundaries(paragraphs)


async def _split_by_semantics(content, target_tokens, threshold=0.7):
    paras = [p.strip() for p in content.split("\n\n") if p.strip()]
    if len(paras) <= 1: return [content]
    splits = await _detect_semantic_boundaries(paras, threshold)
    if not splits: return [content]
    groups = []; start = 0
    for s in splits:
        groups.append(paras[start:s+1]); start = s + 1
    if start < len(paras): groups.append(paras[start:])
    merged = []; buf = []; buf_tok = 0
    for g in groups:
        gt = "\n\n".join(g); gtok = count_tokens(gt)
        if buf_tok + gtok <= target_tokens * 1.2:
            buf.append(gt); buf_tok += gtok
        else:
            if buf: merged.append("\n\n".join(buf))
            buf = [gt]; buf_tok = gtok
    if buf: merged.append("\n\n".join(buf))
    return merged if merged else [content]


def _split_by_tokens(content, target_tokens, overlap_tokens=50):
    pat = re.compile(r"([\u3002\uFF1B;.])\s*")
    parts = pat.split(content)
    sentences = []; i = 0
    while i < len(parts):
        if i + 2 < len(parts) and parts[i+1] in ("\u3002","\uFF1B",";","."):
            sentences.append(parts[i] + parts[i+1] + parts[i+2]); i += 3
        else:
            if parts[i].strip(): sentences.append(parts[i])
            i += 1
    if not sentences: return [content]
    chunks = []; cur = []; cur_tok = 0
    for s in sentences:
        st = count_tokens(s)
        if st > target_tokens:
            if cur: chunks.append("".join(cur)); cur = []; cur_tok = 0
            remaining = s
            from app.ingestion.tokenizer import split_at_token_boundary as sab
            while count_tokens(remaining) > target_tokens:
                part, remaining = sab(remaining, target_tokens)
                if part: chunks.append(part)
            if remaining.strip(): cur = [remaining]; cur_tok = count_tokens(remaining)
            continue
        if cur_tok + st > target_tokens and cur:
            chunks.append("".join(cur))
            ov = _get_sentence_overlap(cur, overlap_tokens)
            cur = [ov] if ov else []; cur_tok = count_tokens(ov) if ov else 0
        cur.append(s); cur_tok += st
    if cur: chunks.append("".join(cur))
    return chunks if chunks else [content]


def _get_sentence_overlap(sentences, overlap_tokens):
    if not sentences or overlap_tokens <= 0: return ""
    result = []; total = 0
    for s in reversed(sentences):
        t = count_tokens(s)
        if total + t > overlap_tokens * 2: break
        result.append(s); total += t
        if total >= overlap_tokens: break
    result.reverse(); return "".join(result)


async def chunk_document(parsed, target_tokens=None, overlap_tokens=None,
                          semantic_threshold=None, use_semantic=None):
    target_tokens = target_tokens or settings.CHUNK_TARGET_TOKENS
    overlap_tokens = overlap_tokens or settings.CHUNK_OVERLAP_TOKENS
    semantic_threshold = semantic_threshold or settings.CHUNK_SEMANTIC_THRESHOLD
    if use_semantic is None: use_semantic = settings.CHUNK_USE_SEMANTIC
    candidates = _split_by_structure(parsed.sections, target_tokens)
    final_texts = []; sec_infos = []
    for content, section, ancestors in candidates:
        tc = count_tokens(content)
        if tc <= target_tokens:
            final_texts.append(content); sec_infos.append((section, ancestors))
        elif use_semantic:
            subs = await _split_by_semantics(content, target_tokens, semantic_threshold)
            for sub in subs:
                if count_tokens(sub) <= target_tokens:
                    final_texts.append(sub); sec_infos.append((section, ancestors))
                else:
                    for x in _split_by_tokens(sub, target_tokens, overlap_tokens):
                        final_texts.append(x); sec_infos.append((section, ancestors))
        else:
            for x in _split_by_tokens(content, target_tokens, overlap_tokens):
                final_texts.append(x); sec_infos.append((section, ancestors))
    chunks = []
    for i, (text, (section, ancestors)) in enumerate(zip(final_texts, sec_infos)):
        path = build_section_path(section, ancestors[:-1] if ancestors else None)
        chunks.append(ChunkResult(content=text, token_count=count_tokens(text),
            chunk_index=i, section_path=path, heading_level=section.heading_level,
            page_number=section.page_number, page_number_end=section.page_number_end))
    return chunks


def chunk_text(text, chunk_size=None, chunk_overlap=None):
    import asyncio
    cs = chunk_size or settings.CHUNK_TARGET_TOKENS
    co = chunk_overlap or settings.CHUNK_OVERLAP_TOKENS
    parsed = ParsedDocument(text=text, sections=[DocumentSection(heading="", heading_level=0, content=text)])
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return [c.strip() for c in _split_by_tokens(text, cs, co) if c.strip()]
    else:
        r = loop.run_until_complete(chunk_document(parsed, target_tokens=cs, overlap_tokens=co, use_semantic=False))
        return [c.content for c in r]


from app.ingestion.tokenizer import estimate_tokens  # noqa: F401