"""Tests for memory functionality."""
import pytest
import tempfile
from core.execution_first import MemoryStore, LocalNgramEmbeddings


class TestMemoryStore:
    """Test MemoryStore class."""
    
    def test_memory_store_initialization(self):
        """Test memory store initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            assert memory.root.name == tmpdir
            assert "facts" in memory._cache
            assert "conversation" in memory._cache
            assert "mistakes" in memory._cache
    
    def test_remember_fact(self):
        """Test remembering a fact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            result = memory.remember("name", "Ada", "facts")
            assert result.success is True
            assert result.verified is True
            assert "name" in memory._cache["facts"]
    
    def test_retrieve_fact(self):
        """Test retrieving a fact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            memory.remember("name", "Ada", "facts")
            
            assert memory._cache["facts"]["name"]["value"] == "Ada"
    
    def test_remember_multiple_categories(self):
        """Test remembering across categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            
            memory.remember("name", "Ada", "facts")
            memory.remember("language", "Python", "preferences")
            memory.remember("project", "JARVIS", "goals")
            
            assert "name" in memory._cache["facts"]
            assert "language" in memory._cache["preferences"]
            assert "project" in memory._cache["goals"]
    
    def test_recall_with_embeddings(self):
        """Test semantic recall with embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embeddings = LocalNgramEmbeddings()
            memory = MemoryStore(tmpdir, embeddings)
            
            memory.remember("name", "Ada Lovelace", "facts")
            memory.remember("birth_year", "1815", "facts")
            
            result = memory.recall("name", limit=5)
            assert result.success is True
            assert result.verified is True
            assert "matches" in result.data
    
    def test_recall_without_embeddings(self):
        """Test recall without embeddings returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir, None)
            result = memory.recall("name", limit=5)
            assert result.success is False
            assert "unavailable" in result.error
    
    def test_persistence(self):
        """Test memory persistence across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First instance
            memory1 = MemoryStore(tmpdir)
            memory1.remember("test", "value", "facts")
            
            # Second instance
            memory2 = MemoryStore(tmpdir)
            assert "test" in memory2._cache["facts"]
            assert memory2._cache["facts"]["test"]["value"] == "value"
    
    def test_embedding_storage(self):
        """Test embedding storage and retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embeddings = LocalNgramEmbeddings()
            memory = MemoryStore(tmpdir, embeddings)
            
            memory.remember("test", "value", "facts")
            
            # Check embedding was stored
            entry = memory._cache["facts"]["test"]
            assert "embedding" in entry
            assert len(entry["embedding"]) == embeddings.dimension
    
    def test_conversation_history(self):
        """Test conversation history tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            
            # Conversation is a list by default
            assert isinstance(memory._cache["conversation"], list)
    
    def test_mistakes_tracking(self):
        """Test mistakes tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            
            memory.remember("mistake1", "Test mistake", "mistakes")
            assert "mistake1" in memory._cache["mistakes"]
    
    def test_update_existing_fact(self):
        """Test updating an existing fact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            
            memory.remember("name", "Ada", "facts")
            memory.remember("name", "Ada Lovelace", "facts")
            
            assert memory._cache["facts"]["name"]["value"] == "Ada Lovelace"
    
    def test_unsupported_category(self):
        """Test error on unsupported category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            result = memory.remember("test", "value", "unsupported")
            assert result.success is False
            assert "Unsupported" in result.error


class TestMemoryEmbeddings:
    """Test memory embedding integration."""
    
    def test_embedding_similarity(self):
        """Test embedding similarity calculation."""
        embeddings = LocalNgramEmbeddings()
        
        v1 = embeddings.embed(["hello world"])[0]
        v2 = embeddings.embed(["hello world"])[0]
        v3 = embeddings.embed(["goodbye world"])[0]
        
        # Same text should have same embedding
        assert v1 == v2
        
        # Different text should have different embedding
        assert v1 != v3
    
    def test_embedding_dimension_consistency(self):
        """Test embedding dimension is consistent."""
        embeddings = LocalNgramEmbeddings()
        
        texts = ["hello", "world", "test"]
        vectors = embeddings.embed(texts)
        
        for vector in vectors:
            assert len(vector) == embeddings.dimension


class TestMemoryIntegration:
    """Test memory integration scenarios."""
    
    def test_user_profile_building(self):
        """Test building user profile from memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            
            memory.remember("name", "Ada", "facts")
            memory.remember("language", "Python", "preferences")
            memory.remember("goal", "Build AI", "goals")
            
            profile = {
                "facts": memory._cache["facts"],
                "preferences": memory._cache["preferences"],
                "goals": memory._cache["goals"]
            }
            
            assert "name" in profile["facts"]
            assert "language" in profile["preferences"]
            assert "goal" in profile["goals"]
    
    def test_learning_from_mistakes(self):
        """Test learning from mistakes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            
            memory.remember("mistake_1", "Used wrong tool", "mistakes")
            memory.remember("mistake_2", "Misunderstood intent", "mistakes")
            
            assert len(memory._cache["mistakes"]) == 2
    
    def test_knowledge_storage(self):
        """Test knowledge storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryStore(tmpdir)
            
            # Knowledge is stored in knowledge directory
            knowledge_dir = memory.knowledge
            assert knowledge_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
