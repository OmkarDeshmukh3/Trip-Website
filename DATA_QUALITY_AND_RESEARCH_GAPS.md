# TripGenie data quality and research-gap register

**Scope:** Maharashtra-first travel-planning college prototype. Updated 10 October 2026.

## Implemented in this revision

- Explainable factor scores for each recommended destination (interest, budget, duration, training-profile similarity, proximity, forecast fit, and prior user feedback).
- Forecast-aware ranking for a selected travel date only when a forecast can be fetched for the next seven days. If unavailable, the system states that weather is not used for the option rather than inventing weather.
- Persisted `more like this` / `not for me` feedback, scoped to the user's selected interest when possible. The feedback affects that user's later rankings.
- Category diversification in the returned shortlist to reduce repetitive results where alternatives exist.
- Cold-start fallback for a destination absent from the model's training labels: content metadata still contributes and its training-similarity factor receives a modest prior rather than a hard zero.
- Automated functional tests under `tests/`.

## Not solved yet (do not overclaim)

1. **Training data validity:** `data/recommendation_training.csv` is synthetic demonstration data. It is not visitor history, booking data, or a public research dataset. The model has not been validated on real trips. It must be replaced with permissioned/anonymized interaction data or a suitable public dataset before making accuracy claims.
2. **Destination verification:** destination coordinates, descriptions and interests are a curated starter set, not a fully verified or exhaustive inventory. Add `source_url` and `last_verified` metadata for every public-facing item, then review official status, access, timings, closures and safety guidance.
3. **Hotels and costs:** entries in `data/hotels.csv` are fictional illustrative records, not bookable accommodations or current prices. Live rates/availability require a licensed provider/API or verified outbound provider links.
4. **Forecast coverage:** Open-Meteo forecast-based ranking is best-effort and used only for dates within the next seven days. It is not a closure alert, route safety certification, or long-range weather prediction. Failed API calls produce a neutral weather score.
5. **Route realism:** distance from coordinates is straight-line proximity; road routing is handled by a separate public demo service and may be unavailable or rate limited.
6. **Evaluation depth:** six automated unit tests check function behaviour, not scientific quality. Future evaluation should compare a baseline with the enhanced ranker using a real/curated test set and report Recall@K/NDCG@K, category coverage/diversity, constraint violations, latency, and user-study feedback.
7. **Safety, accessibility and conservation:** TripGenie currently does not know live fort/cave closures, visitor capacity, trail difficulty, accessibility constraints, or protected-area rules. Include authoritative source links and require visitors to reconfirm current local conditions.
8. **Group preferences and natural-language requests:** not implemented yet. A future release could collect different travellers' interests and explain trade-offs, or add retrieval-grounded conversational search without inventing facts.

## Weighting used in the prototype

| Signal | Weight |
|---|---:|
| Interest fit | 28% |
| Budget fit | 23% |
| Duration fit | 12% |
| Training-profile similarity | 12% |
| Proximity | 10% |
| Forecast/weather fit | 10% |
| User feedback | 5% |

Weights are engineering choices for a classroom prototype, not learned or optimized coefficients. Scores are relative rankings, not probabilities.
