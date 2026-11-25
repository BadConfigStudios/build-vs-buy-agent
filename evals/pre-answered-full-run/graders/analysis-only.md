---
type: llm
focus: last_message
criteria: The final message reports the run directory, the ranking, whether it is a close call and the unverified items, and says the analysis is not a decision. It does not tell the owner which option to choose.
---
Fail if the message recommends a single option as the decision.
