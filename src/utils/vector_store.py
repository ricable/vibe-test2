"""
Vector Store with FAISS and Sentence Transformers

Implements context-preserving chunking and efficient similarity search
for grounding multi-agent RAG systems.
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata"""
    id: str
    text: str
    source: str
    domain: str
    chunk_index: int
    total_chunks: int
    metadata: Dict = None
    embedding: Optional[np.ndarray] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary (excluding embedding for serialization)"""
        data = asdict(self)
        data.pop('embedding', None)
        return data


class VectorStore:
    """
    FAISS-based vector store with semantic search capabilities.

    Features:
    - Sentence Transformer embeddings
    - HNSW indexing for fast similarity search
    - Domain-specific filtering
    - Overlapping chunks for context preservation
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_path: Optional[Path] = None
    ):
        """
        Initialize VectorStore.

        Args:
            embedding_model: HuggingFace model name for embeddings
            index_path: Path to save/load FAISS index
        """
        self.embedding_model_name = embedding_model
        self.encoder = SentenceTransformer(embedding_model)
        self.embedding_dim = self.encoder.get_sentence_embedding_dimension()

        self.index: Optional[faiss.IndexHNSWFlat] = None
        self.chunks: List[DocumentChunk] = []
        self.index_path = index_path

        # Initialize FAISS index
        self._init_index()

    def _init_index(self):
        """Initialize FAISS HNSW index"""
        self.index = faiss.IndexHNSWFlat(self.embedding_dim, 32)  # 32 = M parameter
        self.index.hnsw.efConstruction = 40  # Higher = better quality, slower build
        self.index.hnsw.efSearch = 16  # Higher = better recall, slower search

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks to preserve context.

        Args:
            text: Input text to chunk
            chunk_size: Target size for each chunk (in characters)
            chunk_overlap: Overlap between consecutive chunks

        Returns:
            List of text chunks
        """
        # Split by sentences to avoid breaking mid-sentence
        sentences = text.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_size = len(sentence)

            # If adding this sentence exceeds chunk_size, save current chunk
            if current_size + sentence_size > chunk_size and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                # Keep last few sentences for overlap
                overlap_sentences = []
                overlap_size = 0
                for s in reversed(current_chunk):
                    if overlap_size + len(s) < chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_size += len(s)
                    else:
                        break
                current_chunk = overlap_sentences
                current_size = overlap_size

            current_chunk.append(sentence)
            current_size += sentence_size

        # Add remaining chunk
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')

        return chunks

    def add_documents(
        self,
        documents: List[Dict],
        domain: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> int:
        """
        Add documents to the vector store.

        Args:
            documents: List of dicts with 'text', 'source', and optional 'metadata'
            domain: Domain category (e.g., 'diabetes', 'copd')
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            Number of chunks added
        """
        all_chunks = []
        chunk_id_counter = len(self.chunks)

        for doc_idx, doc in enumerate(tqdm(documents, desc=f"Processing {domain} documents")):
            text = doc['text']
            source = doc.get('source', f'document_{doc_idx}')
            metadata = doc.get('metadata', {})

            # Chunk the document
            text_chunks = self.chunk_text(text, chunk_size, chunk_overlap)

            # Create DocumentChunk objects
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    id=f"{domain}_{chunk_id_counter}",
                    text=chunk_text,
                    source=source,
                    domain=domain,
                    chunk_index=i,
                    total_chunks=len(text_chunks),
                    metadata={**metadata, 'created_at': datetime.now().isoformat()}
                )
                all_chunks.append(chunk)
                chunk_id_counter += 1

        # Generate embeddings in batches
        print(f"Generating embeddings for {len(all_chunks)} chunks...")
        texts = [chunk.text for chunk in all_chunks]
        embeddings = self.encoder.encode(
            texts,
            show_progress_bar=True,
            batch_size=32,
            convert_to_numpy=True
        )

        # Add embeddings to chunks
        for chunk, embedding in zip(all_chunks, embeddings):
            chunk.embedding = embedding

        # Add to FAISS index
        embeddings_matrix = np.vstack([chunk.embedding for chunk in all_chunks])
        self.index.add(embeddings_matrix)

        # Store chunks
        self.chunks.extend(all_chunks)

        print(f"Added {len(all_chunks)} chunks to vector store.")
        return len(all_chunks)

    def search(
        self,
        query: str,
        k: int = 5,
        domain: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Semantic search for relevant document chunks.

        Args:
            query: Search query
            k: Number of results to return
            domain: Filter by specific domain (optional)
            min_score: Minimum similarity score threshold

        Returns:
            List of (DocumentChunk, similarity_score) tuples
        """
        # Generate query embedding
        query_embedding = self.encoder.encode([query], convert_to_numpy=True)

        # Search in FAISS
        # FAISS returns L2 distances, convert to cosine similarity
        distances, indices = self.index.search(query_embedding, k * 2)  # Get more for filtering

        # Filter and rank results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue

            chunk = self.chunks[idx]

            # Domain filtering
            if domain and chunk.domain != domain:
                continue

            # Convert L2 distance to similarity score (approximate cosine)
            # For normalized vectors: cosine_sim ≈ 1 - (L2_dist^2 / 2)
            similarity = 1 - (dist ** 2 / 2)

            if similarity >= min_score:
                results.append((chunk, similarity))

            if len(results) >= k:
                break

        return results

    def save(self, path: Optional[Path] = None):
        """Save index and metadata to disk"""
        save_path = path or self.index_path
        if not save_path:
            raise ValueError("No save path specified")

        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(save_path / "index.faiss"))

        # Save chunks metadata (without embeddings to save space)
        chunks_data = [chunk.to_dict() for chunk in self.chunks]
        with open(save_path / "chunks.json", 'w') as f:
            json.dump(chunks_data, f, indent=2)

        # Save config
        config = {
            'embedding_model': self.embedding_model_name,
            'embedding_dim': self.embedding_dim,
            'num_chunks': len(self.chunks)
        }
        with open(save_path / "config.json", 'w') as f:
            json.dump(config, f, indent=2)

        print(f"Vector store saved to {save_path}")

    def load(self, path: Optional[Path] = None):
        """Load index and metadata from disk"""
        load_path = path or self.index_path
        if not load_path:
            raise ValueError("No load path specified")

        load_path = Path(load_path)

        # Load FAISS index
        self.index = faiss.read_index(str(load_path / "index.faiss"))

        # Load chunks
        with open(load_path / "chunks.json", 'r') as f:
            chunks_data = json.load(f)

        self.chunks = [
            DocumentChunk(**chunk_dict) for chunk_dict in chunks_data
        ]

        # Load config
        with open(load_path / "config.json", 'r') as f:
            config = json.load(f)

        print(f"Loaded vector store with {config['num_chunks']} chunks")

    def get_domain_stats(self) -> Dict[str, int]:
        """Get statistics on chunks per domain"""
        stats = {}
        for chunk in self.chunks:
            stats[chunk.domain] = stats.get(chunk.domain, 0) + 1
        return stats
