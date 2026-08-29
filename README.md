# Jaano — Ask. Find. Know.

Hackathon proof of concept for rebuilding the RTI citizen experience around one core loop:

**FIND → ASK → VERIFY**

## What is new in V7

Jaano now has a grounded AI layer in addition to the working V6 citizen journey:

- Natural-language intent extraction
- Retrieval from the prototype public-record corpus before generation
- Information-gap detection
- AI authority routing with confidence + rationale
- Record-based RTI drafting
- AI response verification against the exact submitted request
- AI-assisted first-appeal drafting from unanswered items
- Deterministic fallback when no API key is configured
- AI/API observability logs

The Track an RTI + My RTIs experience from V6 is preserved.

## Run

```bash
cd backend
python3 server.py
```

Open `http://localhost:8000`.

## Enable live AI

The browser never receives the API key. Configure it only in the backend environment:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_MODEL="gpt-5.6-luna"
python3 server.py
```

If the key is absent, or the live call fails, the app falls back to deterministic demo logic so the judge journey remains reliable.

## Grounding rule

The model does **not** invent government facts. Jaano retrieves prototype records first and gives those records to the model as evidence. The model is used for interpretation, transformation and response comparison.

## Main API routes

- `POST /api/analyse` — grounded intent + retrieval + gap + authority + RTI drafting
- `POST /api/submit` — simulated filing + persistence
- `POST /api/response/analyse` — response verification + appeal aid
- `POST /api/rtis/track` — passwordless RTI lookup
- `POST /api/rtis/list` — My RTIs lookup
- `POST /api/log` — non-sensitive UI interaction telemetry
- `GET /api/health` — health check

## Demo data

All government records, authority routing, responses and submission are synthetic for the hackathon POC.


## Curated judge scenarios
The home page provides three guided journeys: Highway project, Passport delay, and School infrastructure. Government records, responses, and accounts are simulated for the proof of concept. Judges can use the guided examples or enter their own civic question.


## V11 evidence UI
Find and response verification screens expose source/evidence details from the synthetic corpus and response analysis. This is a prototype; records and responses are simulated.
