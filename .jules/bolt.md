## 2024-05-24 - N+1 Queries in HTTP Embeddings Requests
**Learning:** During vector indexing, `_embed_text` was called in a loop for each document chunk, resulting in an N+1 problem not against a local database, but against an external HTTP API (Ollama). Network round trips in a loop significantly degrade performance compared to batch processing.
**Action:** Always verify if external HTTP services support batch endpoints (like `_embed_texts`) and use them to process collections simultaneously. Ensure the batch method uses the correct model configuration.
