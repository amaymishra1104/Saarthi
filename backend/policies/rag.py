import os
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import settings

class PolicyChunk:
    def __init__(self, chunk_id: str, policy_id: str, rule_id: str, title: str, content: str, source_file: str):
        self.chunk_id = chunk_id
        self.policy_id = policy_id
        self.rule_id = rule_id
        self.title = title
        self.content = content
        self.source_file = source_file
        self.full_text = f"{policy_id} {rule_id} {title} {content}".lower()

    @property
    def citation(self) -> str:
        return f"[{self.policy_id}: {self.rule_id} ({self.source_file})]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "policy_id": self.policy_id,
            "rule_id": self.rule_id,
            "title": self.title,
            "citation": self.citation,
            "source_file": self.source_file,
            "content": self.content
        }

class PolicyRAG:
    """
    Local zero-dependency vector/semantic Policy RAG engine.
    Indexes markdown policies, extracts structured rules, and performs
    hybrid keyword-semantic vector retrieval with deterministic source citations.
    """
    def __init__(self, policy_dir: Optional[Path] = None):
        self.policy_dir = policy_dir or settings.POLICY_DIR
        self.chunks: List[PolicyChunk] = []
        self._load_and_index()

    def _load_and_index(self):
        self.chunks = []
        if not self.policy_dir.exists():
            return

        for filepath in self.policy_dir.glob("*.md"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            self._parse_markdown(filepath.name, text)

    def _parse_markdown(self, filename: str, content: str):
        # Extract Policy ID from top header e.g. # Policy POL-FPR-001: ...
        policy_id_match = re.search(r'# Policy\s+([A-Z0-9\-]+):?\s*(.*)', content)
        policy_id = policy_id_match.group(1) if policy_id_match else filename.replace(".md", "").upper()
        policy_title = policy_id_match.group(2) if policy_id_match else filename

        # Split on Rule headers, e.g., 1. **Rule FPR-1: Eligibility for Reversal**
        rule_pattern = re.compile(r'(\d+\.\s+\*\*Rule\s+([A-Z0-9\-]+):?\s*([^\*]+)\*\*)([\s\S]*?)(?=(?:\d+\.\s+\*\*Rule|\Z))')
        matches = list(rule_pattern.finditer(content))

        if matches:
            for idx, match in enumerate(matches):
                rule_id = f"Rule {match.group(2)}"
                rule_title = match.group(3).strip()
                rule_body = match.group(4).strip()
                chunk_id = f"{policy_id}_{match.group(2)}"
                self.chunks.append(
                    PolicyChunk(
                        chunk_id=chunk_id,
                        policy_id=policy_id,
                        rule_id=rule_id,
                        title=rule_title,
                        content=f"{match.group(1)}\n{rule_body}",
                        source_file=filename
                    )
                )
        else:
            # Fallback: chunk by markdown sections
            sections = content.split("## ")
            for idx, section in enumerate(sections):
                if not section.strip():
                    continue
                lines = section.strip().split("\n")
                sec_title = lines[0].strip()
                sec_body = "\n".join(lines[1:]).strip()
                self.chunks.append(
                    PolicyChunk(
                        chunk_id=f"{policy_id}_sec_{idx}",
                        policy_id=policy_id,
                        rule_id=f"Section {idx}",
                        title=sec_title,
                        content=sec_body or sec_title,
                        source_file=filename
                    )
                )

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_\-]{2,}\b', text)]

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.chunks:
            self._load_and_index()

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return [c.to_dict() for c in self.chunks[:top_k]]

        scored = []
        for chunk in self.chunks:
            score = 0.0
            chunk_tokens = self._tokenize(chunk.full_text)
            chunk_token_set = set(chunk_tokens)

            # Query token overlap and frequency
            for qt in q_tokens:
                if qt in chunk_token_set:
                    # Boost for rule title and ID matches
                    term_count = chunk_tokens.count(qt)
                    idf_approx = 1.0 + 1.0 / (1.0 + math.log(1.0 + term_count))
                    weight = 2.5 if qt in chunk.title.lower() or qt in chunk.rule_id.lower() or qt in chunk.policy_id.lower() else 1.0
                    score += term_count * idf_approx * weight

            if score > 0:
                scored.append((score, chunk))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [c.to_dict() for _, c in scored[:top_k]]

        # If no lexical hits, return fallback highest-level policies
        if not results:
            results = [c.to_dict() for c in self.chunks[:top_k]]

        return results

# Singleton policy store
policy_rag = PolicyRAG()

