# Solutions digest: Product page reads

Question: How should the product page read price and stock: from the database, through a cache, or from a view kept up to date by events?
Model: 3 approaches, 5 inputs, 6 settings, 4 scenarios, 4 measures.
Fact tokens: `{{solutions.<scenario>.<approach>.<measure>}}`, source `model`.

## Results at each approach's own settings

### Typical weekday (`typical`): Page views per second 400 rps; Database read at low load 40 ms; Products viewed often 2,000 products; Price and stock changes per second 5 per second; Reads one replica serves 250 rps

| Approach | p95 page read | Failed reads | Oldest price shown | Monthly cost |
| --- | --- | --- | --- | --- |
| Query the database (`direct`) | 117 ms (met) | 0.0% (met) | 0 s (met) | $1.2K |
| Read through a cache (`cache`) | 45 ms (met) | 0.0% (met) | 60 s (met) | $1.6K |
| Read a view kept by events (`view`) | 5 ms (met) | 0.0% (met) | 1 s (met) | $1.9K |

### Sale peak (`sale`): Page views per second 2,400 rps; Database read at low load 40 ms; Products viewed often 6,000 products; Price and stock changes per second 60 per second; Reads one replica serves 250 rps

| Approach | p95 page read | Failed reads | Oldest price shown | Monthly cost |
| --- | --- | --- | --- | --- |
| Query the database (`direct`) | 250 ms (missed) | 79.2% (missed) | 0 s (met) | $1.2K |
| Read through a cache (`cache`) | 41 ms (met) | 0.0% (met) | 60 s (met) | $1.6K |
| Read a view kept by events (`view`) | 5 ms (met) | 0.0% (met) | 2 s (met) | $1.9K |

### Database degraded (`slow_db`): Page views per second 400 rps; Database read at low load 220 ms; Products viewed often 2,000 products; Price and stock changes per second 5 per second; Reads one replica serves 250 rps

| Approach | p95 page read | Failed reads | Oldest price shown | Monthly cost |
| --- | --- | --- | --- | --- |
| Query the database (`direct`) | 250 ms (missed) | 61.1% (missed) | 0 s (met) | $1.2K |
| Read through a cache (`cache`) | 227 ms (missed) | 0.0% (met) | 60 s (met) | $1.6K |
| Read a view kept by events (`view`) | 5 ms (met) | 0.0% (met) | 1 s (met) | $1.9K |

### Catalog reprice (`reprice`): Page views per second 400 rps; Database read at low load 40 ms; Products viewed often 2,000 products; Price and stock changes per second 180 per second; Reads one replica serves 250 rps

| Approach | p95 page read | Failed reads | Oldest price shown | Monthly cost |
| --- | --- | --- | --- | --- |
| Query the database (`direct`) | 117 ms (met) | 0.0% (met) | 0 s (met) | $1.2K |
| Read through a cache (`cache`) | 45 ms (met) | 0.0% (met) | 60 s (met) | $1.6K |
| Read a view kept by events (`view`) | 5 ms (met) | 0.0% (met) | 3,571 s (missed) | $1.9K |

## Budgets missed

- Query the database misses p95 page read in Sale peak: 250 ms against 200 ms.
- Query the database misses Failed reads in Sale peak: 79.2% against 1.0%.
- Query the database misses p95 page read in Database degraded: 250 ms against 200 ms.
- Query the database misses Failed reads in Database degraded: 61.1% against 1.0%.
- Read through a cache misses p95 page read in Database degraded: 227 ms against 200 ms.
- Read a view kept by events misses Oldest price shown in Catalog reprice: 3,571 s against 120 s.

## Largest swings (Typical weekday, one control moved alone)

| Approach | Measure | Control, min to max | At min | At max |
| --- | --- | --- | --- | --- |
| direct | p95 page read | Database read at low load (`db_ms`) 10 ms to 300 ms | 29 ms | 250 ms |
| direct | p95 page read | Page views per second (`rps`) 50 rps to 3,000 rps | 41 ms | 250 ms |
| direct | Failed reads | Page views per second (`rps`) 50 rps to 3,000 rps | 0.0% | 83.3% |
| direct | Failed reads | Database read at low load (`db_ms`) 10 ms to 300 ms | 0.0% | 71.5% |
| direct | Monthly cost | Read replicas (`replicas`) 1 to 8 | $620 | $5K |
| cache | p95 page read | Database read at low load (`db_ms`) 10 ms to 300 ms | 14 ms | 254 ms |
| cache | p95 page read | Cache lifetime (`ttl_s`) 5 s to 600 s | 121 ms | 11 ms |
| cache | Failed reads | Database read at low load (`db_ms`) 10 ms to 300 ms | 0.0% | 1.5% |
| cache | Oldest price shown | Cache lifetime (`ttl_s`) 5 s to 600 s | 5 s | 600 s |
| cache | Oldest price shown | Serve the old entry while refreshing (`swr`) off to on | 60 s | 120 s |
| cache | Monthly cost | Read replicas (`replicas`) 1 to 8 | $1K | $5.3K |
| view | p95 page read | View store (`store_ms`) In memory to On disk | 5 ms | 11 ms |
| view | Oldest price shown | Price and stock changes per second (`writes`) 1 per second to 200 per second | 1 s | 3,571 s |
| view | Oldest price shown | Event consumers (`consumers`) 1 to 16 | 1 s | 1 s |
| view | Monthly cost | Event consumers (`consumers`) 1 to 16 | $1.8K | $3.1K |
| view | Monthly cost | View store (`store_ms`) In memory to On disk | $1.9K | $980 |

## Inputs with no source (assumptions to verify)

- Reads one replica serves (`replica_rps`): 250 rps. from a load test still to run
