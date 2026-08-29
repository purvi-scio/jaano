"""Tiny local RAG retriever for Jaano's hackathon corpus.

The corpus is synthetic and intentionally small. Retrieval is real: queries are normalized,
scored against record chunks, and the top evidence is passed to the AI layer. The LLM is
never the source of government facts.
"""
import re
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
CORPUS_FILE = ROOT / 'data' / 'government_corpus.json'
with open(CORPUS_FILE, encoding='utf-8') as f:
    CORPUS = json.load(f)

STOP = set('the a an and or to of in on for with from is are was were my your i want know what why where how it this that has have had be been'.split())

def tokens(text):
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in STOP and len(x) > 2}

def retrieve(query, scenario=None, top_k=6):
    q = tokens(query)
    scored=[]
    for rec in CORPUS:
        if scenario and rec.get('scenario') not in (scenario, 'general'):
            continue
        text=' '.join([rec.get('title',''), rec.get('department',''), rec.get('text',''), ' '.join(rec.get('keywords',[]))])
        rt=tokens(text)
        overlap=q & rt
        score=len(overlap) / max(1, len(q))
        # Boost direct scenario/title matches so generic words don't dominate.
        if scenario and rec.get('scenario') == scenario: score += 0.15
        if score > 0:
            scored.append((score, rec, sorted(overlap)))
    scored.sort(key=lambda x: x[0], reverse=True)
    results=[]
    for score, rec, overlap in scored[:top_k]:
        results.append({**rec, 'retrieval_score': round(min(score,1),3), 'matched_terms': overlap})
    return results
