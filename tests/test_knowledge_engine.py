"""Comprehensive tests for the Knowledge Engine (Phase 30).

Tests cover:
  - Knowledge Graph: Entity CRUD, relationships, traversal, merge duplicates
  - Embedding Engine: TF-IDF vectors, cosine similarity, batch embed, search
  - RAG Pipeline: query -> retrieve -> rank -> compress
  - Ingestion Pipeline: text, documents, relationships, embeddings
  - Ranking: 6-factor scoring, source reliability
  - Compression: dedup, summarize, key info extraction
  - Source Handlers: DocumentHandler, YouTubeHandler, GitHubHandler, WebsiteHandler
  - Background Learning: async tasks, cancel, stats
  - Self-Organization: maintenance, noise removal, importance update
  - KnowledgeAPI: search, retrieve, learn, summarize, compress, rank, connect, forget
"""
import time
import pytest

from jarvis.knowledge.graph import (
    Entity, Relationship, GraphPath, KnowledgeGraph, knowledge_graph,
)
from jarvis.knowledge.embeddings import EmbeddingEngine, embedding_engine
from jarvis.knowledge.rag import RAGPipeline, rag_pipeline
from jarvis.knowledge.ingestion import IngestionPipeline, IngestionResult, ingestion_pipeline
from jarvis.knowledge.ranking import KnowledgeRanker, RankedKnowledge, knowledge_ranker
from jarvis.knowledge.compression import ContextCompressor, context_compressor
from jarvis.knowledge.sources.handlers import (
    DocumentHandler, YouTubeHandler, GitHubHandler, WebsiteHandler,
    SourceResult, document_handler, youtube_handler, github_handler, website_handler,
)
from jarvis.knowledge.background import (
    BackgroundLearner, LearningTask, LearningStatus, background_learner,
)
from jarvis.knowledge.organization import SelfOrganizer, self_organizer
from jarvis.knowledge import KnowledgeEngine, knowledge_engine


def _clear_graph():
    """Clear all graph state for test isolation."""
    from jarvis.knowledge.graph import knowledge_graph as g
    from jarvis.knowledge.embeddings import embedding_engine as e
    g._entities.clear()
    g._name_index.clear()
    g._relationships.clear()
    g._edge_index.clear()
    g._adjacency.clear()
    g._entity_index.clear()
    e._embeddings.clear()


# ═══════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH
# ═══════════════════════════════════════════════════════════════════════

class TestEntity:
    def test_entity_creation(self):
        e = Entity(name="Python", entity_type="language", description="A programming language")
        assert e.name == "Python"
        assert e.entity_type == "language"
        assert e.importance == 0.5
        assert e.confidence == 0.8
        assert len(e.entity_id) == 12

    def test_entity_recency_score(self):
        e = Entity(name="Test", entity_type="concept")
        e.updated_at = time.time()
        assert e.recency_score > 0.9

    def test_entity_recency_decay(self):
        e = Entity(name="Old", entity_type="concept")
        e.updated_at = time.time() - 86400 * 60
        assert e.recency_score < 0.1

    def test_entity_to_dict(self):
        e = Entity(name="Test", entity_type="concept", importance=0.7)
        d = e.to_dict()
        assert d["name"] == "Test"
        assert d["importance"] == 0.7
        assert "entity_id" in d


class TestRelationship:
    def test_relationship_creation(self):
        r = Relationship(source_id="a", target_id="b", relationship_type="uses")
        assert r.source_id == "a"
        assert r.target_id == "b"
        assert r.weight == 1.0

    def test_relationship_to_dict(self):
        r = Relationship(source_id="a", target_id="b", relationship_type="uses")
        d = r.to_dict()
        assert d["source_id"] == "a"
        assert "relationship_id" in d


class TestGraphPath:
    def test_graph_path_length(self):
        p = GraphPath(entities=[Entity(name="A"), Entity(name="B")])
        assert p.length == 2

    def test_graph_path_empty(self):
        p = GraphPath()
        assert p.length == 0


class TestKnowledgeGraph:
    def setup_method(self):
        self.graph = KnowledgeGraph()

    def test_add_entity(self):
        e = Entity(name="Python", entity_type="language")
        result = self.graph.add_entity(e)
        assert result.name == "Python"
        assert self.graph.entity_count == 1

    def test_add_entity_merges(self):
        e1 = Entity(name="Python", entity_type="language", description="V1")
        e2 = Entity(name="Python", entity_type="language", description="V2")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        assert self.graph.entity_count == 1
        merged = self.graph.get_entity_by_name("Python")
        assert merged.description == "V2"

    def test_get_entity(self):
        e = Entity(name="Python", entity_type="language")
        self.graph.add_entity(e)
        found = self.graph.get_entity(e.entity_id)
        assert found.name == "Python"

    def test_get_entity_by_name(self):
        e = Entity(name="Python", entity_type="language")
        self.graph.add_entity(e)
        found = self.graph.get_entity_by_name("python")
        assert found is not None
        assert found.name == "Python"

    def test_get_entity_by_name_missing(self):
        assert self.graph.get_entity_by_name("nonexistent") is None

    def test_find_entities_by_type(self):
        self.graph.add_entity(Entity(name="Python", entity_type="language"))
        self.graph.add_entity(Entity(name="Django", entity_type="framework"))
        self.graph.add_entity(Entity(name="FastAPI", entity_type="framework"))
        langs = self.graph.find_entities(entity_type="language")
        assert len(langs) == 1
        assert langs[0].name == "Python"
        fw = self.graph.find_entities(entity_type="framework")
        assert len(fw) == 2

    def test_find_entities_by_tags(self):
        e = Entity(name="AI", entity_type="concept", tags=["ml", "data"])
        self.graph.add_entity(e)
        found = self.graph.find_entities(tags=["ml"])
        assert len(found) == 1
        assert found[0].name == "AI"

    def test_find_entities_min_importance(self):
        self.graph.add_entity(Entity(name="Low", entity_type="concept", importance=0.2))
        self.graph.add_entity(Entity(name="High", entity_type="concept", importance=0.9))
        found = self.graph.find_entities(min_importance=0.5)
        assert len(found) == 1
        assert found[0].name == "High"

    def test_remove_entity(self):
        e = Entity(name="Test", entity_type="concept")
        self.graph.add_entity(e)
        assert self.graph.remove_entity(e.entity_id)
        assert self.graph.entity_count == 0
        assert self.graph.get_entity(e.entity_id) is None

    def test_remove_entity_not_found(self):
        assert not self.graph.remove_entity("nonexistent")

    def test_add_relationship(self):
        e1 = Entity(name="Python", entity_type="language")
        e2 = Entity(name="Django", entity_type="framework")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        r = Relationship(source_id=e1.entity_id, target_id=e2.entity_id, relationship_type="uses")
        self.graph.add_relationship(r)
        assert self.graph.relationship_count == 1

    def test_add_relationship_raises_for_missing_entity(self):
        e1 = Entity(name="A", entity_type="concept")
        self.graph.add_entity(e1)
        r = Relationship(source_id=e1.entity_id, target_id="nonexistent", relationship_type="r")
        with pytest.raises(ValueError):
            self.graph.add_relationship(r)

    def test_get_relationships(self):
        e1 = Entity(name="A", entity_type="concept")
        e2 = Entity(name="B", entity_type="concept")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        r = Relationship(source_id=e1.entity_id, target_id=e2.entity_id, relationship_type="related_to")
        self.graph.add_relationship(r)
        rels = self.graph.get_relationships(e1.entity_id)
        assert len(rels) == 1

    def test_get_relationships_direction(self):
        e1 = Entity(name="A", entity_type="concept")
        e2 = Entity(name="B", entity_type="concept")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        r = Relationship(source_id=e1.entity_id, target_id=e2.entity_id, relationship_type="r")
        self.graph.add_relationship(r)
        outgoing = self.graph.get_relationships(e1.entity_id, direction="outgoing")
        incoming = self.graph.get_relationships(e2.entity_id, direction="incoming")
        assert len(outgoing) == 1
        assert len(incoming) == 1

    def test_get_neighbors(self):
        e1 = Entity(name="A", entity_type="concept")
        e2 = Entity(name="B", entity_type="concept")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        r = Relationship(source_id=e1.entity_id, target_id=e2.entity_id, relationship_type="related_to")
        self.graph.add_relationship(r)
        neighbors = self.graph.get_neighbors(e1.entity_id)
        assert len(neighbors) == 1
        assert neighbors[0].name == "B"

    def test_get_subgraph_returns_tuple(self):
        e1 = Entity(name="A", entity_type="concept")
        e2 = Entity(name="B", entity_type="concept")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        r = Relationship(source_id=e1.entity_id, target_id=e2.entity_id, relationship_type="related_to")
        self.graph.add_relationship(r)
        entities, relationships = self.graph.get_subgraph(e1.entity_id, max_depth=1)
        assert len(entities) == 2
        assert len(relationships) == 1

    def test_find_path(self):
        e1 = Entity(name="A", entity_type="concept")
        e2 = Entity(name="B", entity_type="concept")
        e3 = Entity(name="C", entity_type="concept")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        self.graph.add_entity(e3)
        self.graph.add_relationship(Relationship(source_id=e1.entity_id, target_id=e2.entity_id, relationship_type="r"))
        self.graph.add_relationship(Relationship(source_id=e2.entity_id, target_id=e3.entity_id, relationship_type="r"))
        path = self.graph.find_path(e1.entity_id, e3.entity_id)
        assert path is not None
        assert len(path.entities) == 3

    def test_find_path_no_path(self):
        e1 = Entity(name="A", entity_type="concept")
        e2 = Entity(name="B", entity_type="concept")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        path = self.graph.find_path(e1.entity_id, e2.entity_id)
        assert path is None

    def test_merge_duplicates(self):
        e1 = Entity(name="Python", entity_type="language")
        e2 = Entity(name="Python", entity_type="language")
        e1.access_count = 5
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        merged = self.graph.merge_duplicates()
        assert self.graph.entity_count == 1

    def test_search_entities(self):
        self.graph.add_entity(Entity(name="Python", entity_type="language", description="programming language"))
        self.graph.add_entity(Entity(name="Java", entity_type="language", description="programming language"))
        results = self.graph.search_entities("Python", limit=5)
        assert len(results) >= 1
        assert results[0].name == "Python"

    def test_get_stats(self):
        self.graph.add_entity(Entity(name="A", entity_type="concept"))
        stats = self.graph.get_stats()
        assert stats["entity_count"] == 1
        assert "relationship_count" in stats
        assert "entity_types" in stats
        assert "avg_importance" in stats

    def test_get_entity_count(self):
        assert self.graph.entity_count == 0
        self.graph.add_entity(Entity(name="A", entity_type="concept"))
        assert self.graph.entity_count == 1

    def test_get_relationship_count(self):
        e1 = Entity(name="A", entity_type="concept")
        e2 = Entity(name="B", entity_type="concept")
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        self.graph.add_relationship(Relationship(source_id=e1.entity_id, target_id=e2.entity_id, relationship_type="r"))
        assert self.graph.relationship_count == 1

    def test_find_similar(self):
        e1 = Entity(name="Python", entity_type="language", embedding=[1.0, 0.0, 0.0])
        e2 = Entity(name="Java", entity_type="language", embedding=[0.9, 0.1, 0.0])
        self.graph.add_entity(e1)
        self.graph.add_entity(e2)
        similar = self.graph.find_similar(e1.entity_id, limit=5)
        assert len(similar) >= 1

    def test_find_by_embedding(self):
        e1 = Entity(name="Python", entity_type="language", embedding=[1.0, 0.0, 0.0])
        self.graph.add_entity(e1)
        found = self.graph.find_by_embedding([1.0, 0.0, 0.0], limit=5)
        assert len(found) >= 1


# ═══════════════════════════════════════════════════════════════════════
# EMBEDDING ENGINE
# ═══════════════════════════════════════════════════════════════════════

class TestEmbeddingEngine:
    def setup_method(self):
        self.engine = EmbeddingEngine(dimension=128)

    def test_embed_returns_list(self):
        emb = self.engine.embed("Python programming")
        assert isinstance(emb, list)
        assert len(emb) == 128

    def test_embed_empty_string(self):
        emb = self.engine.embed("")
        assert isinstance(emb, list)
        assert len(emb) == 128

    def test_batch_embed(self):
        embs = self.engine.embed_batch(["Python", "Java", "C++"])
        assert len(embs) == 3
        for emb in embs:
            assert len(emb) == 128

    def test_store_and_search(self):
        emb = self.engine.store_embedding("test:1", "Python programming language")
        results = self.engine.search_similar(emb, top_k=3)
        assert len(results) >= 1
        assert results[0][0] == "test:1"

    def test_search_text(self):
        self.engine.store_embedding("test:1", "Python programming language")
        results = self.engine.search_text("Python", top_k=3)
        assert len(results) >= 1

    def test_similarity_identical(self):
        v = [1.0, 0.0, 0.0]
        sim = self.engine.similarity(v, v)
        assert abs(sim - 1.0) < 0.001

    def test_similarity_orthogonal(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        sim = self.engine.similarity(v1, v2)
        assert abs(sim) < 0.001

    def test_similarity_zero_vector(self):
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        sim = self.engine.similarity(v1, v2)
        assert sim == 0.0

    def test_get_stored(self):
        self.engine.store_embedding("key1", "hello world")
        stored = self.engine.get_stored("key1")
        assert stored is not None
        assert len(stored) == 128

    def test_get_stored_missing(self):
        assert self.engine.get_stored("nonexistent") is None

    def test_get_stats(self):
        self.engine.store_embedding("a", "hello")
        self.engine.store_embedding("b", "world")
        stats = self.engine.get_stats()
        assert stats["stored_embeddings"] == 2

    def test_dimension(self):
        e = EmbeddingEngine(dimension=64)
        assert e.dimension == 64


# ═══════════════════════════════════════════════════════════════════════
# RANKING
# ═══════════════════════════════════════════════════════════════════════

class TestKnowledgeRanker:
    def setup_method(self):
        self.ranker = KnowledgeRanker()

    def test_rank_empty(self):
        result = self.ranker.rank([], "test")
        assert result == []

    def test_rank_single(self):
        candidates = [{"text": "Python is great", "importance": 0.8}]
        result = self.ranker.rank(candidates, "Python")
        assert len(result) == 1
        assert result[0].final_score >= 0

    def test_rank_ordering(self):
        candidates = [
            {"text": "Python is a language", "importance": 0.3},
            {"text": "Python programming language", "importance": 0.9},
        ]
        result = self.ranker.rank(candidates, "Python")
        assert len(result) == 2
        assert result[0].final_score >= result[1].final_score

    def test_rank_to_dict(self):
        candidates = [{"text": "test", "importance": 0.5}]
        result = self.ranker.rank(candidates, "test")
        d = result[0].to_dict()
        assert "content" in d
        assert "final_score" in d

    def test_ranked_knowledge_fields(self):
        candidates = [{"text": "test", "importance": 0.5, "source": "docs"}]
        result = self.ranker.rank(candidates, "test")
        r = result[0]
        assert hasattr(r, "content")
        assert hasattr(r, "source")
        assert hasattr(r, "importance")
        assert hasattr(r, "confidence")
        assert hasattr(r, "recency")
        assert hasattr(r, "frequency")
        assert hasattr(r, "source_reliability")
        assert hasattr(r, "final_score")

    def test_get_stats(self):
        stats = self.ranker.get_stats()
        assert "weights" in stats
        assert "source_reliability_count" in stats

    def test_update_weights(self):
        self.ranker.update_weights({"importance": 0.5})
        stats = self.ranker.get_stats()
        assert stats["weights"]["importance"] == 0.5


# ═══════════════════════════════════════════════════════════════════════
# COMPRESSION
# ═══════════════════════════════════════════════════════════════════════

class TestContextCompressor:
    def setup_method(self):
        self.compressor = ContextCompressor()

    def test_compress_empty(self):
        result = self.compressor.compress([], "test")
        assert result == ""

    def test_compress_single(self):
        result = self.compressor.compress(["Hello world"], "test")
        assert "Hello world" in result

    def test_compress_multiple(self):
        contexts = [
            "Python is a programming language",
            "FastAPI is a web framework",
            "Django is another framework",
        ]
        result = self.compressor.compress(contexts, "Python")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_summarize(self):
        text = "Python is a language. It is used for many things. It is popular in AI. It has many libraries."
        summary = self.compressor.summarize(text, max_sentences=2)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_extract_key_info(self):
        text = "Python is a programming language. It was created by Guido. It is open source."
        info = self.compressor.extract_key_info(text)
        assert isinstance(info, list)

    def test_split_sentences(self):
        sentences = ContextCompressor._split_sentences("Hello world. How are you? I am fine.")
        assert len(sentences) == 3

    def test_relevance_score(self):
        score = self.compressor._relevance_score("Python programming language", "Python")
        assert 0 <= score <= 1

    def test_sentence_score(self):
        score = self.compressor._sentence_score("Python is a very important language.")
        assert 0 <= score <= 1

    def test_get_stats(self):
        self.compressor.compress(["test"], "query")
        stats = self.compressor.get_stats()
        assert "max_tokens" in stats
        assert "compression_count" in stats


# ═══════════════════════════════════════════════════════════════════════
# INGESTION PIPELINE
# ═══════════════════════════════════════════════════════════════════════

class TestIngestionPipeline:
    def setup_method(self):
        self.pipeline = IngestionPipeline()
        _clear_graph()

    def test_ingest_text(self):
        result = self.pipeline.ingest_text("Python is a programming language.")
        assert result.success
        assert result.entities_created >= 1
        assert result.latency_ms >= 0

    def test_ingest_text_empty(self):
        result = self.pipeline.ingest_text("")
        assert result.success
        assert result.entities_created == 0

    def test_ingest_text_extracts_entities(self):
        result = self.pipeline.ingest_text(
            "Python was created by Guido van Rossum. Django is a Python web framework."
        )
        assert result.entities_created >= 3
        assert result.relationships_created >= 1

    def test_ingest_chunks(self):
        result = self.pipeline.ingest_chunks(
            ["Python is a language", "FastAPI is a framework"],
            source_type="text",
            source_name="test",
        )
        assert result.success
        assert result.entities_created >= 1

    def test_clean_text(self):
        cleaned = self.pipeline._clean_text("Hello   world\n\n\n\n\nTest")
        assert "  " not in cleaned
        assert "\n\n\n" not in cleaned

    def test_chunk_text_short(self):
        chunks = self.pipeline._chunk_text("Hello world")
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_chunk_text_empty(self):
        chunks = self.pipeline._chunk_text("")
        assert len(chunks) == 0

    def test_extract_entities(self):
        entities = self.pipeline._extract_entities(
            ["Python is a language and Django is a framework"],
            "text", "test",
        )
        names = [e.name for e in entities]
        assert "Python" in names
        assert "Django" in names

    def test_extract_relationships(self):
        entities = [
            Entity(name="Python", entity_type="language"),
            Entity(name="Django", entity_type="framework"),
        ]
        rels = self.pipeline._extract_relationships(entities)
        assert len(rels) == 1
        assert rels[0].relationship_type in ("related_to", "uses", "part_of", "references", "explains")

    def test_estimate_importance(self):
        score = self.pipeline._estimate_importance("Python", "Python is important and key")
        assert score >= 0.6

    def test_get_stats(self):
        self.pipeline.ingest_text("Test text")
        stats = self.pipeline.get_stats()
        assert stats["ingestion_count"] == 1
        assert stats["total_entities"] >= 1


# ═══════════════════════════════════════════════════════════════════════
# RAG PIPELINE
# ═══════════════════════════════════════════════════════════════════════

class TestRAGPipeline:
    def setup_method(self):
        self.rag = RAGPipeline()
        _clear_graph()
        self.rag._query_count = 0
        ingestion_pipeline.ingest_text("Python is a programming language for web development and AI.")
        ingestion_pipeline.ingest_text("FastAPI is a Python web framework built on Starlette.")

    def test_query(self):
        result = self.rag.query("What is Python?")
        assert "context" in result
        assert "sources" in result
        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1

    def test_query_with_min_relevance(self):
        result = self.rag.query("quantum physics", min_relevance=0.9)
        assert isinstance(result, dict)

    def test_has_relevant_knowledge(self):
        assert self.rag.has_relevant_knowledge("Python")
        assert not self.rag.has_relevant_knowledge("quantum physics", threshold=0.9)

    def test_get_stats(self):
        self.rag.query("test")
        stats = self.rag.get_stats()
        assert stats["query_count"] == 1


# ═══════════════════════════════════════════════════════════════════════
# SOURCE HANDLERS
# ═══════════════════════════════════════════════════════════════════════

class TestSourceResult:
    def test_creation(self):
        r = SourceResult(success=True, title="Test", source_type="text")
        assert r.success
        assert r.title == "Test"

    def test_fields(self):
        r = SourceResult(success=True, title="Test", chunks=["a", "b"], source="file.pdf")
        assert r.chunks == ["a", "b"]
        assert r.source == "file.pdf"


class TestYouTubeHandler:
    def test_extract_video_id(self):
        vid = youtube_handler._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_extract_video_id_short(self):
        vid = youtube_handler._extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_process(self):
        result = youtube_handler.process("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result.success
        assert result.source_type == "youtube"


class TestGitHubHandler:
    def test_parse_repo_url(self):
        parsed = github_handler._parse_repo_url("https://github.com/fastapi/fastapi")
        assert parsed["owner"] == "fastapi"
        assert parsed["repo"] == "fastapi"

    def test_parse_repo_url_with_git(self):
        parsed = github_handler._parse_repo_url("https://github.com/user/repo.git")
        assert parsed["owner"] == "user"
        assert "repo" in parsed["repo"]

    def test_process(self):
        result = github_handler.process("https://github.com/fastapi/fastapi")
        assert result.success
        assert result.source_type == "github"


class TestWebsiteHandler:
    def test_clean_html(self):
        html = "<html><body><p>Hello world</p></body></html>"
        text = website_handler._clean_html(html)
        assert "Hello world" in text
        assert "<" not in text


class TestDocumentHandler:
    def test_process_nonexistent(self):
        result = document_handler.process("nonexistent.txt")
        assert not result.success


# ═══════════════════════════════════════════════════════════════════════
# BACKGROUND LEARNING
# ═══════════════════════════════════════════════════════════════════════

class TestBackgroundLearner:
    def setup_method(self):
        self.learner = BackgroundLearner()

    def test_learn_text(self):
        task = self.learner.learn("Python is a language", source_type="text")
        assert task.task_id
        # Task should be LEARNING or COMPLETED (thread runs fast)
        assert task.status in (LearningStatus.LEARNING, LearningStatus.COMPLETED)

    def test_learn_completes(self):
        task = self.learner.learn("Python is a language", source_type="text")
        time.sleep(1.5)
        updated = self.learner.get_task(task.task_id)
        assert updated.status == LearningStatus.COMPLETED

    def test_get_all_tasks(self):
        self.learner.learn("test1", source_type="text")
        self.learner.learn("test2", source_type="text")
        tasks = self.learner.get_all_tasks()
        assert len(tasks) == 2

    def test_get_active_tasks(self):
        self.learner.learn("test", source_type="text")
        active = self.learner.get_active_tasks()
        assert isinstance(active, list)

    def test_cancel(self):
        task = self.learner.learn("test", source_type="text")
        time.sleep(0.1)
        # Cancel may succeed if still LEARNING, or fail if already completed
        result = self.learner.cancel(task.task_id)
        updated = self.learner.get_task(task.task_id)
        if result:
            assert updated.status == LearningStatus.FAILED
        # else: task completed before cancel could fire, which is fine

    def test_cancel_nonexistent(self):
        assert not self.learner.cancel("nonexistent")

    def test_get_stats(self):
        self.learner.learn("test", source_type="text")
        time.sleep(0.5)
        stats = self.learner.get_stats()
        assert "total_tasks" in stats
        assert "active_tasks" in stats
        assert "completed" in stats

    def test_active_count(self):
        count = self.learner.active_count
        assert isinstance(count, int)
        assert count >= 0

    def test_unknown_source_type(self):
        task = self.learner.learn("test", source_type="unknown_type_xyz")
        time.sleep(1.0)
        updated = self.learner.get_task(task.task_id)
        assert updated.status == LearningStatus.FAILED


# ═══════════════════════════════════════════════════════════════════════
# SELF-ORGANIZATION
# ═══════════════════════════════════════════════════════════════════════

class TestSelfOrganizer:
    def setup_method(self):
        self.organizer = SelfOrganizer()

    def test_should_maintain_initial(self):
        self.organizer._last_maintenance = 0
        assert self.organizer.should_maintain()

    def test_should_not_maintain_recent(self):
        self.organizer._last_maintenance = time.time()
        assert not self.organizer.should_maintain()

    def test_run_maintenance(self):
        from jarvis.knowledge.graph import knowledge_graph
        knowledge_graph.add_entity(Entity(name="Test", entity_type="concept", importance=0.5))
        result = self.organizer.run_maintenance()
        assert "merged_duplicates" in result
        assert "latency_ms" in result

    def test_get_stats(self):
        stats = self.organizer.get_stats()
        assert "maintenance_count" in stats


# ═══════════════════════════════════════════════════════════════════════
# KNOWLEDGE API (INTEGRATION)
# ═══════════════════════════════════════════════════════════════════════

class TestKnowledgeEngine:
    def setup_method(self):
        self.engine = KnowledgeEngine()
        _clear_graph()

    def test_learn_text(self):
        r = self.engine.learn("Python is a programming language.")
        assert r["success"]
        assert r["entities"] >= 1

    def test_learn_background(self):
        r = self.engine.learn("test", background=True)
        assert r["status"] == "learning"
        assert "task_id" in r

    def test_search(self):
        self.engine.learn("Python is a language.")
        results = self.engine.search("Python")
        assert len(results) >= 1

    def test_search_semantic(self):
        self.engine.learn("Python is a language.")
        results = self.engine.search_semantic("Python")
        assert isinstance(results, list)

    def test_retrieve(self):
        self.engine.learn("Python is a language.")
        result = self.engine.retrieve("What is Python?")
        assert "context" in result
        assert "confidence" in result

    def test_retrieve_entity(self):
        self.engine.learn("Python is a language.")
        entity = self.engine.retrieve_entity("Python")
        assert entity is not None
        assert entity["name"] == "Python"

    def test_retrieve_entity_missing(self):
        assert self.engine.retrieve_entity("nonexistent") is None

    def test_connect(self):
        self.engine.learn("Python is a language.")
        self.engine.learn("FastAPI is a framework.")
        r = self.engine.connect("Python", "FastAPI", "uses")
        assert r["success"]

    def test_connect_missing(self):
        r = self.engine.connect("Nonexistent", "Also", "related_to")
        assert not r["success"]

    def test_forget(self):
        self.engine.learn("Python is a language.")
        r = self.engine.forget("Python")
        assert r["removed"] >= 1

    def test_forget_no_match(self):
        r = self.engine.forget("nonexistent")
        assert r["removed"] == 0

    def test_summarize(self):
        summary = self.engine.summarize("A. B. C. D.")
        assert isinstance(summary, str)

    def test_compress(self):
        result = self.engine.compress(["A", "B", "C"], query="test")
        assert isinstance(result, str)

    def test_rank(self):
        ranked = self.engine.rank(
            [{"text": "a", "importance": 0.5}, {"text": "b", "importance": 0.8}],
            query="test",
        )
        assert len(ranked) == 2

    def test_maintain(self):
        result = self.engine.maintain()
        assert "merged_duplicates" in result

    def test_get_stats(self):
        stats = self.engine.get_stats()
        assert "graph" in stats
        assert "embeddings" in stats
        assert "rag" in stats

    def test_full_workflow(self):
        """Test complete learn -> search -> retrieve -> connect -> forget cycle."""
        r1 = self.engine.learn("Python is a programming language created by Guido van Rossum.")
        assert r1["success"]
        r2 = self.engine.learn("FastAPI is a Python web framework for building APIs.")
        assert r2["success"]

        results = self.engine.search("Python")
        assert len(results) >= 1

        rag = self.engine.retrieve("What is Python used for?")
        assert rag["confidence"] >= 0

        r3 = self.engine.connect("Python", "FastAPI", "uses")
        assert r3["success"]

        r4 = self.engine.forget("FastAPI")
        assert r4["removed"] >= 1

        stats = self.engine.get_stats()
        assert stats["graph"]["entity_count"] >= 1

    def test_ingestion_stats(self):
        self.engine.learn("test content")
        self.engine.learn("more content")
        stats = self.engine.get_stats()
        assert stats["ingestion"]["ingestion_count"] >= 2

    def test_learn_document(self):
        result = self.engine.learn_document("nonexistent.txt")
        assert not result["success"]

    def test_learn_url_youtube(self):
        result = self.engine.learn_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result["success"]

    def test_learn_url_github(self):
        result = self.engine.learn_url("https://github.com/fastapi/fastapi")
        assert result["success"]

    def test_has_relevant_knowledge(self):
        self.engine.learn("Python is a language.")
        assert self.engine.rag.has_relevant_knowledge("Python")
