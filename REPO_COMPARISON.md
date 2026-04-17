# Repository Comparison Matrix

## Feature Comparison

| Feature | LLM Graph Builder | Wikigrapher | Wiki CSV Parser | Create Context Graph |
|---------|-------------------|-------------|-----------------|----------------------|
| **Wikipedia Support** | ✅ Via WikipediaLoader | ✅ SQL dumps | ✅ XML dumps | ✅ Multi-source |
| **LLM Integration** | ✅ Multi-LLM | ❌ No | ❌ No | ✅ PydanticAI |
| **Embeddings** | ✅ Vector index | ❌ No | ❌ No | ✅ Optional |
| **Entity Extraction** | ✅ LLM-based | ❌ No | ❌ No | ✅ Auto-extract |
| **Relationship Creation** | ✅ LLM-based | ✅ Predefined | ✅ Predefined | ✅ Auto-detect |
| **RAG/Retrieval** | ✅ GraphRAG-like | ❌ No | ❌ No | ✅ Agent memory |
| **Chat Interface** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Scalability** | Medium (per-page) | High (bulk) | High (bulk) | Medium (domain) |
| **Setup Complexity** | Medium | Medium | Low | Low |
| **Docker Support** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ CLI |
| **Active Development** | ✅ Yes (2026) | ✅ Yes (2026) | ✅ Yes (2026) | ✅ Yes (2026) |

---

## Use Case Matrix

| Use Case | Best Repo | Why | Time to Setup |
|----------|-----------|-----|----------------|
| **Single Wikipedia page → Graph** | LLM Graph Builder | Full pipeline with LLM extraction | 30 min |
| **Full Wikipedia → Neo4j** | Wikigrapher | Optimized for bulk processing | 2-3 hours |
| **Wikipedia XML parsing** | Wiki CSV Parser | Fastest XML parsing | 20 min |
| **Domain-specific graphs** | Create Context Graph | Scaffolding + agent memory | 15 min |
| **NER + Relation extraction** | Knowledge-Graph-with-Neo4j | spaCy integration | 30 min |
| **Production RAG system** | LLM Graph Builder | Complete with retrieval | 1-2 hours |
| **Batch Wikipedia processing** | Wikigrapher | TSV generation + bulk import | 2-3 hours |
| **Quick demo** | LLM Graph Builder | Docker Compose ready | 15 min |

---

## Technology Stack Comparison

| Repo | Backend | Frontend | Database | LLM | Embeddings |
|------|---------|----------|----------|-----|-----------|
| LLM Graph Builder | FastAPI (Python) | React | Neo4j | OpenAI, Gemini, Claude, etc. | Multiple providers |
| Wikigrapher | Python scripts | None | Neo4j | None | None |
| Wiki CSV Parser | Java | None | Neo4j | None | None |
| Create Context Graph | FastAPI (Python) | Optional | Neo4j | PydanticAI | Optional |

---

## Performance Characteristics

| Repo | Throughput | Memory Usage | CPU Usage | Disk I/O |
|------|-----------|--------------|-----------|----------|
| LLM Graph Builder | ~10-50 pages/min | Medium | Medium | Low |
| Wikigrapher | ~1M pages/hour | High (RAM offloading) | High | High |
| Wiki CSV Parser | ~1M pages/hour | Low (streaming) | Medium | High |
| Create Context Graph | ~100-500 items/min | Medium | Medium | Low |

---

## Code Quality & Maturity

| Repo | Stars | Forks | Issues | Last Update | Code Quality |
|------|-------|-------|--------|-------------|--------------|
| LLM Graph Builder | 4586 | 787 | 54 | Apr 2026 | ⭐⭐⭐⭐⭐ |
| Wikigrapher | 50+ | 0 | 0 | Apr 2026 | ⭐⭐⭐⭐ |
| Wiki CSV Parser | 5 | 0 | 5 | Apr 2026 | ⭐⭐⭐ |
| Create Context Graph | 468 | 50 | 2 | Apr 2026 | ⭐⭐⭐⭐⭐ |

---

## Recommended Selection Flowchart

```
START: Wikipedia → Neo4j Project
  │
  ├─ Need LLM-powered extraction?
  │  ├─ YES → Need RAG/retrieval?
  │  │        ├─ YES → LLM Graph Builder ✅
  │  │        └─ NO → LLM Graph Builder (without RAG)
  │  │
  │  └─ NO → Need to process full Wikipedia?
  │           ├─ YES → Wikigrapher ✅
  │           └─ NO → Wiki CSV Parser ✅
  │
  └─ Need domain-specific scaffolding?
     ├─ YES → Create Context Graph ✅
     └─ NO → See above
```

---

## Integration Patterns

### Pattern 1: LLM Graph Builder + Wikigrapher
- Use Wikigrapher for bulk Wikipedia import
- Use LLM Graph Builder for enrichment/extraction on top

### Pattern 2: Wiki CSV Parser + Custom LLM
- Use Wiki CSV Parser for fast XML parsing
- Add custom LLM extraction layer

### Pattern 3: Create Context Graph + LLM Graph Builder
- Use Create Context Graph for scaffolding
- Use LLM Graph Builder patterns for Wikipedia ingestion

---

## Cost Considerations

| Repo | Infrastructure | LLM Costs | Embedding Costs | Total (1M pages) |
|------|-----------------|-----------|-----------------|------------------|
| LLM Graph Builder | $50-200 | $500-2000 | $100-500 | $650-2700 |
| Wikigrapher | $50-100 | $0 | $0 | $50-100 |
| Wiki CSV Parser | $50-100 | $0 | $0 | $50-100 |
| Create Context Graph | $50-200 | $100-500 | $50-200 | $200-900 |

*Estimates based on AWS/GCP pricing (2026)*

---

## Learning Curve

| Repo | Neo4j Knowledge | Python | Java | LLM/Embeddings | Overall |
|------|-----------------|--------|------|----------------|---------|
| LLM Graph Builder | Medium | Required | No | Required | Medium-High |
| Wikigrapher | Low | Required | No | No | Low |
| Wiki CSV Parser | Low | No | Required | No | Low |
| Create Context Graph | Medium | Required | No | Optional | Medium |

---

## Customization Difficulty

| Repo | Easy Customizations | Hard Customizations | Extensibility |
|------|-------------------|-------------------|----------------|
| LLM Graph Builder | Schema, LLM model, embeddings | Retrieval logic | ⭐⭐⭐⭐⭐ |
| Wikigrapher | Dump source, output format | Processing logic | ⭐⭐⭐ |
| Wiki CSV Parser | CSV format, node types | XML parsing logic | ⭐⭐ |
| Create Context Graph | Domain, data sources | Agent logic | ⭐⭐⭐⭐ |

