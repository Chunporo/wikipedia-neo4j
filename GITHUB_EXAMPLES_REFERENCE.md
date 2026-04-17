# Wikipedia → Neo4j → GraphRAG: Real-World GitHub Examples & Patterns

**Last Updated**: April 2026  
**Focus**: Small, runnable demos with reusable patterns (not full code copies)

---

## 🎯 Quick Reference: Repo Selection Guide

| Use Case | Best Repo | Why |
|----------|-----------|-----|
| **LLM-based graph extraction** | `neo4j-labs/llm-graph-builder` | Full pipeline: Wikipedia → chunks → entities → relationships → vector embeddings |
| **Raw Wikipedia dumps → Neo4j** | `7mza/wikigrapher-generator` | Efficient SQL dump processing, TSV generation, bulk import |
| **Wikipedia XML parsing** | `SirCremefresh/wiki-to-neo4j-csv-parser` | Fast Java-based XML parsing, CSV export for Neo4j import |
| **Context graphs + agents** | `neo4j-labs/create-context-graph` | Domain-specific scaffolding, agent memory, multi-source ingestion |
| **Knowledge graph from docs** | `dhyeythumar/Knowledge-Graph-with-Neo4j` | NER + relation extraction, spaCy integration (archived but useful patterns) |

---

## 📦 Repository Details

### 1. **neo4j-labs/llm-graph-builder** ⭐ 4586
**Best for**: End-to-end LLM-powered graph construction with RAG retrieval

**GitHub**: https://github.com/neo4j-labs/llm-graph-builder  
**Latest Commit**: `61121df4c15716f67636a4fac2c96e909d374ada`  
**Stack**: Python (FastAPI) + React + Neo4j + LangChain  
**Key Features**:
- Wikipedia source support (via WikipediaLoader)
- Chunk-based ingestion with embeddings
- Entity extraction + relationship creation
- Vector index for semantic search
- Multi-LLM support (OpenAI, Gemini, Claude, etc.)
- Chat/QA integration with GraphRAG-like retrieval

**Runnable**: ✅ Yes (Docker Compose included)

---

### 2. **7mza/wikigrapher-generator** ⭐ 50+
**Best for**: Efficient Wikipedia dump processing at scale

**GitHub**: https://github.com/7mza/wikigrapher-generator  
**Latest Commit**: `9a1454ab54d1f8c4b4950f580c6adc4ac82b8509`  
**Stack**: Python + Bash + Neo4j  
**Key Features**:
- Downloads Wikipedia SQL dumps (pages, links, redirects, categories)
- Processes dumps into TSV files (pages, categories, links, redirects)
- Bulk import into Neo4j via `neo4j-admin import`
- Supports multiple languages (EN, AR, FR tested)
- Docker Compose setup included
- ~2h generation time for English Wikipedia on 6c/32GB machine

**Runnable**: ✅ Yes (Docker Compose)

---

### 3. **SirCremefresh/wiki-to-neo4j-csv-parser** ⭐ 5
**Best for**: Fast XML parsing of Wikipedia dumps

**GitHub**: https://github.com/SirCremefresh/wiki-to-neo4j-csv-parser  
**Latest Commit**: `f1eb177724f1f7fdf6cc44ed713fc047f8ccf58b`  
**Stack**: Java + Neo4j  
**Key Features**:
- Parses Wikipedia XML dumps efficiently
- Generates Neo4j-loadable CSVs
- Supports both plain and compressed (bz2) dumps
- Docker Compose for Neo4j setup
- Performance: 14min import for English Wikipedia (22.7M nodes, 235M relationships)

**Runnable**: ✅ Yes (Docker Compose)

---

### 4. **neo4j-labs/create-context-graph** ⭐ 468
**Best for**: Scaffolded domain-specific context graphs with agent memory

**GitHub**: https://github.com/neo4j-labs/create-context-graph  
**Latest Commit**: `263d561d40d70bb0b0ef2f9ca7f080e7e2a52042`  
**Stack**: Python (FastAPI) + Neo4j + PydanticAI  
**Key Features**:
- Interactive CLI for domain selection (22 industry domains)
- Auto-generates FastAPI backend + Neo4j schema
- Agent memory scaffolding (neo4j-agent-memory)
- Multi-source data import (GitHub, Slack, Gmail, Jira, Notion, Salesforce)
- Synthetic demo data generation
- GDS projections for graph algorithms

**Runnable**: ✅ Yes (CLI scaffolding)

---

### 5. **dhyeythumar/Knowledge-Graph-with-Neo4j** ⭐ 29
**Best for**: NER + relation extraction patterns

**GitHub**: https://github.com/dhyeythumar/Knowledge-Graph-with-Neo4j  
**Stack**: Python (spaCy, neuralcoref, NetworkX)  
**Status**: Archived (but patterns still valid)  
**Key Features**:
- Wikipedia scraping + NER extraction
- Coreference resolution (neuralcoref)
- Relation extraction
- Neo4j + MongoDB storage

**Runnable**: ✅ Yes (but archived)

---

## 🔧 Reusable Pattern Snippets

### Pattern 1: Wikipedia Source Loading (LLM Graph Builder)

**File**: [`backend/src/document_sources/wikipedia.py`](https://github.com/neo4j-labs/llm-graph-builder/blob/61121df4c15716f67636a4fac2c96e909d374ada/backend/src/document_sources/wikipedia.py)

```python
# Pattern: Load Wikipedia pages via LangChain
from langchain_community.document_loaders import WikipediaLoader

def get_documents_from_wikipedia(wiki_query: str, language: str):
    pages = WikipediaLoader(
        query=wiki_query.strip(),
        lang=language,
        load_all_available_meta=False,
        doc_content_chars_max=100000,
        load_max_docs=1
    ).load()
    return wiki_query.strip(), pages
```

**Key Takeaway**: Use `WikipediaLoader` for simple Wikipedia queries; supports language codes and metadata.

---

### Pattern 2: Chunk Creation with Embeddings (LLM Graph Builder)

**File**: [`backend/src/make_relationships.py` (lines 36-59)](https://github.com/neo4j-labs/llm-graph-builder/blob/61121df4c15716f67636a4fac2c96e909d374ada/backend/src/make_relationships.py#L36-L59)

```python
# Pattern: Create chunk embeddings and vector index
def create_chunk_embeddings(graph, chunkId_chunkDoc_list, file_name, embedding_provider, embedding_model):
    embeddings, dimension = load_embedding_model(embedding_provider, embedding_model)
    
    data_for_query = []
    for row in chunkId_chunkDoc_list:
        embeddings_arr = embeddings.embed_query(row['chunk_doc'].page_content)
        data_for_query.append({
            "chunkId": row['chunk_id'],
            "embeddings": embeddings_arr
        })
    
    # Batch upsert with Cypher
    query = """
        UNWIND $data AS row
        MATCH (d:Document {fileName: $fileName})
        MERGE (c:Chunk {id: row.chunkId})
        SET c.embedding = row.embeddings
        MERGE (c)-[:PART_OF]->(d)
    """
    execute_graph_query(graph, query, params={"fileName": file_name, "data": data_for_query})
```

**Key Takeaway**: Batch embeddings with UNWIND for performance; store as node properties.

---

### Pattern 3: Entity-Chunk Relationships (LLM Graph Builder)

**File**: [`backend/src/make_relationships.py` (lines 13-33)](https://github.com/neo4j-labs/llm-graph-builder/blob/61121df4c15716f67636a4fac2c96e909d374ada/backend/src/make_relationships.py#L13-L33)

```python
# Pattern: Link extracted entities to source chunks
def merge_relationship_between_chunk_and_entites(graph, graph_documents_chunk_chunk_Id):
    batch_data = []
    
    for graph_doc_chunk_id in graph_documents_chunk_chunk_Id:
        for node in graph_doc_chunk_id['graph_doc'].nodes:
            batch_data.append({
                'chunk_id': graph_doc_chunk_id['chunk_id'],
                'node_type': node.type,
                'node_id': node.id
            })
    
    if batch_data:
        query = """
            UNWIND $batch_data AS data
            MATCH (c:Chunk {id: data.chunk_id})
            CALL apoc.merge.node([data.node_type], {id: data.node_id}) YIELD node AS n
            MERGE (c)-[:HAS_ENTITY]->(n)
        """
        execute_graph_query(graph, query, params={"batch_data": batch_data})
```

**Key Takeaway**: Use `apoc.merge.node` for dynamic node creation; batch operations for scale.

---

### Pattern 4: Wikipedia Dump Processing (Wikigrapher)

**File**: [`scripts/process_pages.py` (lines 22-42)](https://github.com/7mza/wikigrapher-generator/blob/9a1454ab54d1f8c4b4950f580c6adc4ac82b8509/scripts/process_pages.py#L22-L42)

```python
# Pattern: Parse Wikipedia SQL dump into dictionaries
def process_pages(path: str, total_lines: int = 0):
    pages_by_ids = defaultdict(dict)
    pages_by_titles = defaultdict(dict)
    
    with pgzip.open(path, "rt") as file:
        for _, line in enumerate(tqdm(file, total=total_lines)):
            try:
                _id, title, is_redirect = line.rstrip("\n").split(SEPARATOR)
                if title not in pages_by_titles:
                    pages_by_titles[title] = _id
                    pages_by_ids[_id] = (title, is_redirect == "1")
            except Exception:
                logger.error("error parsing line:\n%s", line)
                continue
    
    return (pages_by_ids, pages_by_titles)
```

**Key Takeaway**: Use `pgzip` for compressed dumps; maintain bidirectional lookup dicts.

---

### Pattern 5: XML Parsing for Wikipedia (Wiki CSV Parser)

**File**: [`src/main/java/ch/ksobwalden/wikidump/WikiDumpParser.java`](https://github.com/SirCremefresh/wiki-to-neo4j-csv-parser/blob/f1eb177724f1f7fdf6cc44ed713fc047f8ccf58b/src/main/java/ch/ksobwalden/wikidump/WikiDumpParser.java)

```java
// Pattern: Stream-based XML parsing for Wikipedia dumps
public static void process(CsvWriter pageWriter, CsvWriter linkWriter, InputStream inputFile) 
        throws XMLStreamException, IOException {
    var urlTitles = new HashSet<String>();
    
    var xmlParser = new XmlElementParser<>(
        PageObjectParser::new,
        "page",
        (page) -> {
            if (page.validate(urlTitles)) {
                urlTitles.add(page.getUrlTitle());
                pageWriter.writeLine(page.getUrlTitle(), page.getTitle(), page.getId(), page.isRedirect());
                for (Link link : page.getLinks()) {
                    linkWriter.writeLine(page.getUrlTitle(), link.urlTitle(), link.title(), 
                                       page.isRedirect(), link.index());
                }
            }
        }
    );
    
    xmlParser.parse(inputFile);
    pageWriter.flush();
    linkWriter.flush();
}
```

**Key Takeaway**: Stream-based parsing avoids loading entire dump into memory; deduplication via HashSet.

---

### Pattern 6: Neo4j Bulk Import (Wikigrapher)

**File**: Wikigrapher README (Docker Compose)

```bash
# Pattern: Bulk import TSV files into Neo4j
docker compose exec neo4j bash -c "
cd /import && \
neo4j-admin database import full neo4j \
  --overwrite-destination \
  --delimiter='\t' \
  --array-delimiter=';' \
  --nodes=./pages.header.tsv.gz,./pages.final.tsv.gz \
  --nodes=./categories.header.tsv.gz,./categories.final.tsv.gz \
  --relationships=./link_to.header.tsv.gz,./link_to.final.tsv.gz \
  --relationships=./belong_to.header.tsv.gz,./belong_to.final.tsv.gz \
  --verbose
"
```

**Key Takeaway**: Use `neo4j-admin import` for bulk loading; separate header files for schema definition.

---

### Pattern 7: GraphRAG-like Retrieval (LLM Graph Builder)

**File**: [`backend/src/QA_integration.py` (lines 1-100)](https://github.com/neo4j-labs/llm-graph-builder/blob/61121df4c15716f67636a4fac2c96e909d374ada/backend/src/QA_integration.py#L1-L100)

```python
# Pattern: Multi-mode retrieval (vector + graph + fulltext)
from langchain_neo4j import Neo4jVector
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import EmbeddingsFilter

# Vector retrieval
vector_store = Neo4jVector(
    embedding=embedding_function,
    graph=graph,
    node_label="Chunk",
    embedding_node_property="embedding",
    index_name="vector",
    embedding_dimension=dimension
)

# Contextual compression (filter by relevance score)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=DocumentCompressorPipeline(
        transformers=[EmbeddingsFilter(embeddings=embeddings, similarity_threshold=0.76)]
    ),
    base_retriever=vector_store.as_retriever()
)
```

**Key Takeaway**: Combine vector search with compression filters; use Neo4jVector for semantic search.

---

### Pattern 8: Database Access Layer (LLM Graph Builder)

**File**: [`backend/src/graphDB_dataAccess.py` (lines 41-74)](https://github.com/neo4j-labs/llm-graph-builder/blob/61121df4c15716f67636a4fac2c96e909d374ada/backend/src/graphDB_dataAccess.py#L41-L74)

```python
# Pattern: Source node tracking for ingestion pipeline
class graphDBdataAccess:
    def __init__(self, graph: Neo4jGraph):
        self.graph = graph
    
    def create_source_node(self, obj_source_node: sourceNode):
        self.graph.query("""
            MERGE(d:Document {fileName: $fn}) 
            SET d.fileSize = $fs, 
                d.fileType = $ft,
                d.status = $st,
                d.url = $url,
                d.fileSource = $f_source,
                d.createdAt = $c_at,
                d.processingTime = $pt,
                d.nodeCount = $n_count,
                d.relationshipCount = $r_count,
                d.model = $model
        """, {
            "fn": obj_source_node.file_name,
            "fs": obj_source_node.file_size,
            "ft": obj_source_node.file_type,
            "st": "New",
            "url": obj_source_node.url,
            "f_source": obj_source_node.file_source,
            "c_at": obj_source_node.created_at,
            "pt": 0,
            "n_count": 0,
            "r_count": 0,
            "model": obj_source_node.model
        })
```

**Key Takeaway**: Track document metadata for audit trail; use MERGE for idempotency.

---

## 📊 Architecture Patterns

### Pattern A: Wikipedia → Chunks → Entities → Relationships → Vectors

```
Wikipedia Page
    ↓
[WikipediaLoader]
    ↓
Document (full text)
    ↓
[Text Splitter]
    ↓
Chunks (with position metadata)
    ↓
[LLM Entity Extraction]
    ↓
Entities + Relationships
    ↓
[Embedding Model]
    ↓
Vector Index (Chunk embeddings)
    ↓
Neo4j Graph
    ├── :Document
    ├── :Chunk (with embedding)
    ├── :Entity (extracted)
    └── Relationships (HAS_ENTITY, PART_OF, NEXT_CHUNK, etc.)
```

**Implementation**: `neo4j-labs/llm-graph-builder`

---

### Pattern B: Wikipedia SQL Dump → TSV → Bulk Import

```
Wikipedia SQL Dump (pages, links, categories)
    ↓
[Python Scripts] (process_pages.py, process_pagelinks.py, etc.)
    ↓
TSV Files (with headers)
    ├── pages.tsv.gz
    ├── categories.tsv.gz
    ├── links.tsv.gz
    └── redirects.tsv.gz
    ↓
[neo4j-admin import]
    ↓
Neo4j Graph
    ├── :Page
    ├── :Category
    ├── :Redirect
    └── Relationships (LINK_TO, BELONG_TO, REDIRECT_TO, etc.)
```

**Implementation**: `7mza/wikigrapher-generator`

---

### Pattern C: Wikipedia XML → CSV → Neo4j

```
Wikipedia XML Dump
    ↓
[Java XML Parser] (stream-based)
    ↓
CSV Files
    ├── pages.csv
    └── links.csv
    ↓
[LOAD CSV / neo4j-admin import]
    ↓
Neo4j Graph
```

**Implementation**: `SirCremefresh/wiki-to-neo4j-csv-parser`

---

## 🚀 Quick Start Commands

### LLM Graph Builder (Docker)
```bash
git clone https://github.com/neo4j-labs/llm-graph-builder.git
cd llm-graph-builder
cp backend/example.env backend/.env
# Edit .env with Neo4j credentials
docker-compose up
# Access at http://localhost:3000
```

### Wikigrapher (Docker)
```bash
git clone https://github.com/7mza/wikigrapher-generator.git
cd wikigrapher-generator
chmod +x *.sh
docker compose run --remove-orphans --build generator
# Then import into Neo4j
docker compose --profile neo4j up
```

### Wiki CSV Parser (Docker)
```bash
git clone https://github.com/SirCremefresh/wiki-to-neo4j-csv-parser.git
cd wiki-to-neo4j-csv-parser
docker-compose up
mvn compile exec:java -Dexec.args="path/to/wikipedia-dump.xml"
```

---

## 📈 Performance Benchmarks

| Repo | Dataset | Nodes | Relationships | Time | Hardware |
|------|---------|-------|---------------|------|----------|
| Wikigrapher | English Wikipedia | 22.7M | 235.7M | 14 min | 6c/32GB/NVMe |
| Wiki CSV Parser | Simple Wikipedia | 430K | 3.3M | 40 sec | - |
| LLM Graph Builder | Single Wikipedia page | ~100-500 | ~50-200 | <1 min | - |

---

## 🔗 Related Resources

- **Neo4j Official Wiki Guide**: https://guides.neo4j.com/wiki
- **LangChain Neo4j Integration**: https://python.langchain.com/docs/integrations/graphs/neo4j/
- **Neo4j APOC Library**: https://neo4j.com/docs/apoc/current/
- **GraphRAG Paper**: https://arxiv.org/abs/2404.16130

---

## 📝 Key Learnings

1. **Chunking Strategy**: Position-aware chunks with overlap improve retrieval quality
2. **Embedding Storage**: Store embeddings as node properties for fast vector search
3. **Batch Operations**: Use UNWIND for bulk inserts (10K+ records)
4. **Deduplication**: Maintain lookup dicts (title→ID) to avoid duplicate nodes
5. **Stream Processing**: Use pgzip/XML streaming for large dumps (avoid memory overload)
6. **Vector Index**: Create VECTOR index on Chunk nodes for semantic search
7. **Metadata Tracking**: Store source document metadata for audit trails
8. **Multi-mode Retrieval**: Combine vector + graph + fulltext for better results

