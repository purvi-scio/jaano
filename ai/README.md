# Jaano AI layer

Jaano uses a grounded, structured AI pipeline. The model is **not** the source of truth for government facts.

### Pipeline
1. **Intent extraction** — identify topic, information needs and likely jurisdiction.
2. **Local retrieval / RAG** — retrieve matching records from `data/documents.json`.
3. **Gap detection** — compare the citizen's information needs against retrieved evidence.
4. **Authority routing** — rank the supplied authority directory and return confidence + rationale.
5. **RTI drafting** — turn gaps into requests for existing records/data, not opinions.
6. **Response verification** — compare every original request against the response evidence.
7. **Appeal assistance** — draft only from unanswered/partial items.

### Runtime modes
- With `OPENAI_API_KEY`: uses the OpenAI Responses API with strict JSON schema output.
- Without a key: deterministic fallback keeps the hackathon demo fully runnable.

### Environment
```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-5.6-luna"
```

The API key is read only by the backend and is never sent to the browser.
