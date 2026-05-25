# --- PEGASUS META-ONLY PROMPT BUILDER + POSTFILTER ---
# KEEP PEGASUS FOCUSED ON REPHRASING *ONLY* THE GIVEN TEXT
# NO NEW FACTS. NO OUTSIDE WORDS. TWEET-SIZED OUTPUT.

# backend/pegasusprompt.py
import re
import unicodedata
from typing import Set


def _normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    # unify punctuation that commonly appears in social/meta text
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("…", "...")
    return s


def build_pegasus_prompt(meta_text: str) -> str:
    s = _normalize((meta_text or "").strip())
    s = re.sub(r"(…|\.{3})\s*$", "", s)  # drop dangling ellipses
    return s


def _source_vocab(meta_text: str) -> Set[str]:
    meta_text = _normalize(meta_text)
    toks = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", meta_text)
    return set(t.lower() for t in toks if t)


def enforce_source_vocab(summary: str, meta_text: str) -> str:
    import re

    summary = _normalize(summary)
    allowed = _source_vocab(meta_text)

    out_tokens = []
    for t in re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[.,!?;:()-]", summary):
        if t[0].isalnum():
            if t.lower() in allowed:
                out_tokens.append(t)
        else:
            out_tokens.append(t)

    # pretty join: space before words, no space before ,.!?;:)
    s = ""
    for tok in out_tokens:
        if tok[0].isalnum():
            s += (" " if s else "") + tok
        else:
            s += tok
    return re.sub(r"\s+", " ", s).strip()


def trim_to_280(s: str) -> str:
    s = (s or "").strip()
    return s if len(s) <= 280 else s[:277].rstrip() + "..."
