import io
import re
import logging
from typing import List, Tuple, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader
from sqlalchemy.orm import Session
from app.models import KBChunk, KBDocument

logger = logging.getLogger(__name__)

def extract_text_from_file(filename: str, content_bytes: bytes) -> str:
    """Extract raw text from uploaded .txt, .md, or .pdf files."""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["txt", "md"]:
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return content_bytes.decode("latin-1", errors="ignore")
    elif ext == "pdf":
        try:
            pdf_reader = PdfReader(io.BytesIO(content_bytes))
            text_parts = []
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error reading PDF {filename}: {e}")
            raise ValueError(f"Failed to parse PDF document: {str(e)}")
    else:
        # Fallback decode
        try:
            return content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping character chunks cleanly by sentences/words."""
    text = text.strip()
    if not text:
        return []
    
    # Simple chunking by paragraph or fixed length
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = []
    
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 1 <= chunk_size:
            current_chunk = f"{current_chunk}\n{para}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If paragraph itself is longer than chunk_size, split by sentences
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.?!])\s+', para)
                sub_chunk = ""
                for s in sentences:
                    if len(sub_chunk) + len(s) + 1 <= chunk_size:
                        sub_chunk = f"{sub_chunk} {s}".strip()
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = s
                if sub_chunk:
                    chunks.append(sub_chunk)
                current_chunk = ""
            else:
                current_chunk = para
                
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

class RAGEngine:
    def __init__(self):
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.chunk_ids: List[int] = []
        self.chunk_texts: List[str] = []
        self.is_dirty: bool = True

    def rebuild_index(self, db: Session):
        """Fetch all chunks from DB and rebuild the TF-IDF vector space."""
        chunks = db.query(KBChunk).all()
        if not chunks:
            self.vectorizer = None
            self.tfidf_matrix = None
            self.chunk_ids = []
            self.chunk_texts = []
            self.is_dirty = False
            logger.info("RAG Index cleared (no KB chunks).")
            return

        self.chunk_ids = [c.id for c in chunks]
        self.chunk_texts = [c.content for c in chunks]

        # Token pattern handles words + numbers
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            token_pattern=r'(?u)\b\w+\b',
            ngram_range=(1, 2)
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.chunk_texts)
        self.is_dirty = False
        logger.info(f"RAG Index rebuilt successfully with {len(chunks)} chunks.")

    def search(self, db: Session, query: str, top_k: int = 3) -> Tuple[List[Dict[str, Any]], float]:
        """Search query against TF-IDF index. Returns list of matches and top score."""
        if self.is_dirty or self.vectorizer is None or self.tfidf_matrix is None:
            self.rebuild_index(db)

        if not self.vectorizer or not self.chunk_texts or self.tfidf_matrix is None:
            return [], 0.0

        query_clean = query.strip()
        if not query_clean:
            return [], 0.0

        try:
            query_vec = self.vectorizer.transform([query_clean])
            similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            
            if len(similarities) == 0:
                return [], 0.0

            top_indices = np.argsort(similarities)[::-1][:top_k]
            top_score = float(similarities[top_indices[0]]) if len(top_indices) > 0 else 0.0

            results = []
            for idx in top_indices:
                score = float(similarities[idx])
                if score > 0.001:  # Filter zero similarity
                    results.append({
                        "chunk_id": self.chunk_ids[idx],
                        "content": self.chunk_texts[idx],
                        "score": round(score, 4)
                    })

            return results, round(top_score, 4)
        except Exception as e:
            logger.error(f"Error during RAG search: {e}")
            return [], 0.0

rag_engine = RAGEngine()
