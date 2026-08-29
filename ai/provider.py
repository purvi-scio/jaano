"""Jaano AI provider: OpenAI-backed structured reasoning with deterministic fallback.

The model is never treated as the source of truth for government facts. Local retrieved
records are passed as evidence; the model is only used to interpret, transform and compare.
"""
import json, os, urllib.request, urllib.error, uuid

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
API_URL = "https://api.openai.com/v1/responses"


def enabled():
    return bool(os.getenv("OPENAI_API_KEY"))


def _call(instructions, payload, schema_name, schema):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    body = {
        "model": MODEL,
        "input": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "text": {"format": {"type": "json_schema", "name": schema_name, "strict": True, "schema": schema}},
    }
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"
    })
    request_id = str(uuid.uuid4())[:8]
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            raw = resp.read().decode()
            data = json.loads(raw)
            text = data.get("output_text")
            if not text:
                # Defensive extraction for Responses API output blocks.
                chunks=[]
                for item in data.get("output", []):
                    for c in item.get("content", []):
                        if c.get("type") in ("output_text", "text") and c.get("text"):
                            chunks.append(c["text"])
                text=''.join(chunks)
            return json.loads(text), {"provider":"openai", "model":MODEL, "request_id":request_id}
    except urllib.error.HTTPError as e:
        detail=e.read().decode(errors="replace")
        raise RuntimeError(f"OpenAI HTTP {e.code}: {detail[:500]}")


def analyse(question, authorities, documents):
    schema={
      "type":"object","additionalProperties":False,"properties":{
        "topic":{"type":"string"},
        "requirements":{"type":"array","items":{"type":"string"}},
        "scenario":{"type":"string","enum":["highway","passport","general"]},
        "authority_key":{"type":"string","enum":["highway","passport","general"]},
        "missing_requirements":{"type":"array","items":{"type":"string"}},
        "request_items":{"type":"array","items":{"type":"string"}},
        "mappings":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{"from":{"type":"string"},"to":{"type":"string"},"why":{"type":"string"}},"required":["from","to","why"]}},
        "reason":{"type":"string"},
        "confidence":{"type":"integer","minimum":0,"maximum":100},
        "evidence_ids":{"type":"array","items":{"type":"string"}}
      },"required":["topic","requirements","scenario","authority_key","missing_requirements","request_items","mappings","reason","confidence","evidence_ids"]
    }
    instructions=("You are Jaano, a civic-information assistant for India's RTI process. "
      "Interpret the citizen's problem, but NEVER invent government facts. The supplied records are the only evidence. "
      "First identify what information the citizen needs. Then mark as missing only information not supported by the supplied records. "
      "Convert missing needs into concise requests for existing records, documents, data or recorded facts. Do not ask officials for opinions, explanations, justifications or actions. "
      "Select the best authority key from the supplied authority directory. Confidence is your routing confidence, not legal certainty. For every factual claim about existing public information, cite an evidence_id from the supplied retrieved records. Never invent an evidence_id. "
      "Return JSON only according to the schema.")
    payload={"question":question,"authorities":authorities,"retrieved_records":documents}
    return _call(instructions,payload,"jaano_analysis",schema)


def response_analyse(request_items, response_text, scenario):
    item_schema={
      "type":"object","additionalProperties":False,"properties":{
        "question":{"type":"string"},
        "status":{"type":"string","enum":["answered","partially_answered","unanswered"]},
        "answer":{"type":"string"},
        "reason":{"type":"string"},
        "evidence":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{"page":{"type":"string"},"quote":{"type":"string"}},"required":["page","quote"]}}
      },"required":["question","status","answer","reason","evidence"]
    }
    schema={"type":"object","additionalProperties":False,"properties":{"results":{"type":"array","items":item_schema},"appeal_draft":{"type":"string"}},"required":["results","appeal_draft"]}
    instructions=("You are Jaano's response verifier. Compare each exact RTI request with the supplied synthetic response. "
      "Do not infer facts that are absent. Mark answered only when the response actually provides the requested information; use partially_answered when only part is supplied. "
      "For answered or partially answered items, include a short verbatim evidence quote from the supplied response and page number 1. For unanswered items, evidence must be an empty array. "
      "For unanswered items, explain the gap factually. Draft a short first-appeal aid only from unanswered/partial items. Do not provide legal advice.")
    return _call(instructions,{"scenario":scenario,"request_items":request_items,"response":response_text},"jaano_response_check",schema)
