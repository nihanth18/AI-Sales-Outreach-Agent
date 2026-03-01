"""
ChromaDB vector memory for contextual agent recall.
Stores research data, email history, and interaction context
so agents can make informed decisions across runs.
"""

from typing import List, Dict, Any, Optional
import json
import os

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

from app.config import settings


class VectorMemory:
    """Wraps ChromaDB for persistent agent memory."""

    def __init__(self):
        self.client = None
        self.research_collection = None
        self.email_collection = None
        self.interaction_collection = None
        self._initialized = False

    def initialize(self):
        """Lazy initialization of ChromaDB."""
        if self._initialized:
            return

        if not HAS_CHROMADB:
            print("⚠️  ChromaDB not installed. Running without vector memory.")
            self._initialized = True
            return

        try:
            persist_dir = settings.chroma_persist_dir
            os.makedirs(persist_dir, exist_ok=True)

            self.client = chromadb.PersistentClient(path=persist_dir)

            self.research_collection = self.client.get_or_create_collection(
                name="prospect_research",
                metadata={"description": "Research data for prospects"}
            )
            self.email_collection = self.client.get_or_create_collection(
                name="email_history",
                metadata={"description": "Sent emails and responses"}
            )
            self.interaction_collection = self.client.get_or_create_collection(
                name="interactions",
                metadata={"description": "All agent interactions and outcomes"}
            )

            self._initialized = True
            print("✅ Vector memory initialized (ChromaDB)")
        except Exception as e:
            print(f"⚠️  ChromaDB initialization failed: {e}. Running without vector memory.")
            self._initialized = True

    def store_research(self, prospect_id: str, research_text: str, metadata: Dict[str, Any] = None):
        """Store research data for a prospect."""
        self.initialize()
        if not self.research_collection:
            return

        try:
            self.research_collection.upsert(
                ids=[f"research_{prospect_id}"],
                documents=[research_text],
                metadatas=[metadata or {"prospect_id": prospect_id}]
            )
        except Exception as e:
            print(f"⚠️  Failed to store research: {e}")

    def store_email(self, email_id: str, email_text: str, metadata: Dict[str, Any] = None):
        """Store an email in vector memory."""
        self.initialize()
        if not self.email_collection:
            return

        try:
            self.email_collection.upsert(
                ids=[f"email_{email_id}"],
                documents=[email_text],
                metadatas=[metadata or {"email_id": email_id}]
            )
        except Exception as e:
            print(f"⚠️  Failed to store email: {e}")

    def store_interaction(self, interaction_id: str, text: str, metadata: Dict[str, Any] = None):
        """Store an interaction record."""
        self.initialize()
        if not self.interaction_collection:
            return

        try:
            self.interaction_collection.upsert(
                ids=[interaction_id],
                documents=[text],
                metadatas=[metadata or {}]
            )
        except Exception as e:
            print(f"⚠️  Failed to store interaction: {e}")

    def search_similar_research(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Find research data similar to the query."""
        self.initialize()
        if not self.research_collection:
            return []

        try:
            results = self.research_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return self._format_results(results)
        except Exception as e:
            print(f"⚠️  Research search failed: {e}")
            return []

    def search_similar_emails(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Find previously sent emails similar to the query."""
        self.initialize()
        if not self.email_collection:
            return []

        try:
            results = self.email_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return self._format_results(results)
        except Exception as e:
            print(f"⚠️  Email search failed: {e}")
            return []

    def get_prospect_context(self, prospect_id: str) -> str:
        """Get all stored context for a specific prospect."""
        self.initialize()
        context_parts = []

        # Get research
        if self.research_collection:
            try:
                results = self.research_collection.get(
                    ids=[f"research_{prospect_id}"]
                )
                if results and results["documents"]:
                    context_parts.append(f"Research:\n{results['documents'][0]}")
            except Exception:
                pass

        # Get emails
        if self.email_collection:
            try:
                results = self.email_collection.get(
                    where={"prospect_id": prospect_id}
                )
                if results and results["documents"]:
                    for doc in results["documents"]:
                        context_parts.append(f"Previous Email:\n{doc}")
            except Exception:
                pass

        return "\n\n---\n\n".join(context_parts) if context_parts else ""

    def _format_results(self, results) -> List[Dict[str, Any]]:
        """Format ChromaDB results into a clean list."""
        if not results or not results.get("documents"):
            return []

        formatted = []
        for i, doc in enumerate(results["documents"][0]):
            entry = {"text": doc}
            if results.get("metadatas") and results["metadatas"][0]:
                entry["metadata"] = results["metadatas"][0][i]
            if results.get("distances") and results["distances"][0]:
                entry["similarity"] = 1 - results["distances"][0][i]
            formatted.append(entry)

        return formatted


# Global memory instance
memory = VectorMemory()
