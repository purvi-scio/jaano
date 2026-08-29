# Jaano — AI + RAG Product Plan

## Product thesis
Government speaks in records and data; citizens speak in problems and grievances. Jaano is the translation layer between the two.

## Three jobs
### FIND
Before asking the government, retrieve relevant records from a connected corpus and identify what is already supported by evidence versus what is missing.

### ASK
Turn the evidence gap into specific, record-based RTI requests and recommend the likely authority. The citizen reviews and can edit the draft.

### VERIFY
When a response arrives, compare it against the exact original request item-by-item. Show supporting response evidence for answered/partial items and make the absence of evidence explicit for unanswered items.

## RAG architecture
1. Natural-language question enters Jaano.
2. Scenario/intent classification selects the relevant corpus partition.
3. Local retrieval ranks corpus records using token overlap + scenario boost.
4. Retrieved record IDs, dates, pages and text are passed to the AI reasoning layer.
5. The model may interpret and transform evidence, but must not invent government facts.
6. UI exposes source metadata so the citizen can inspect why a fact was shown.

## Prototype corpus
The corpus is synthetic, as permitted by the hackathon proof-of-concept requirement. It contains small evidence sets for highway and passport journeys. It deliberately includes both positive records and records indicating that a requested item is absent from the connected corpus, allowing the demo to show a real retrieval → gap-detection loop without pretending to have live access to every government database.

## Response verification
The verifier receives the exact submitted request items and the synthetic response. It classifies each item as answered, partially answered or unanswered. Answered/partial items require a short response quote; unanswered items carry an empty evidence list and an explicit explanation. The first-appeal draft is generated only from unanswered/partial items.

## Winning demo moment
Input: “The highway near my village has been under construction for three years. I want to know where the money went and why it is delayed.”

Jaano retrieves evidence for the sanctioned amount, contractor/work order and original completion date, then identifies actual expenditure and revised completion/extension information as gaps. It routes the request to NHAI, creates two record-based requests, simulates filing, then verifies the response against those same two requests.
