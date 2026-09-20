"""
KOHLER CONCORD — Knowledge Base Loader.

Parses Markdown files with YAML frontmatter and structured clause sections.
Extracts metadata (domain, access_level, clause_id) from each section.
"""

from __future__ import annotations

import glob
import logging
import os
import re
from typing import Any, Dict, List

import yaml

from src.config import Document, settings

logger = logging.getLogger(__name__)

# Regex patterns for clause ID extraction
# Matches:  ### Title (HR-POL-001)  OR  ## HR-POL-001: Title  OR  ## HR-POL-001
_HEADER_WITH_ID_PARENS = re.compile(
    r"^(#{2,3})\s+(.+?)\s*\(([A-Z]{2,4}-[A-Z]{2,4}-\d{3}(?:\.\d+)?)\)\s*$",
    re.MULTILINE,
)
_HEADER_WITH_ID_PREFIX = re.compile(
    r"^(#{2,3})\s+([A-Z]{2,4}-[A-Z]{2,4}-\d{3}(?:\.\d+)?)[:\s]+(.*)$",
    re.MULTILINE,
)
_ACCESS_LEVEL_COMMENT = re.compile(
    r"<!--\s*access_level:\s*(\w+)\s*-->", re.IGNORECASE,
)


class KnowledgeBaseLoader:
    """Loads and parses the synthetic Kohler knowledge base."""

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = data_dir or settings.DATA_DIR

    def load_all(self) -> List[Document]:
        """Scan data_dir for .md files and parse them into Documents."""
        if not self.data_dir or not os.path.exists(self.data_dir):
            logger.warning(f"Data directory not found: {self.data_dir}")
            return []

        documents: List[Document] = []
        md_files = glob.glob(os.path.join(self.data_dir, "**", "*.md"), recursive=True)

        for filepath in sorted(md_files):
            try:
                docs = self._parse_markdown(filepath)
                documents.extend(docs)
                logger.info(f"Loaded {len(docs)} sections from {os.path.basename(filepath)}")
            except Exception as e:
                logger.error(f"Error parsing {filepath}: {e}")

        logger.info(f"Total documents loaded: {len(documents)}")
        return documents

    def _parse_markdown(self, filepath: str) -> List[Document]:
        """Parse a single markdown file into per-clause Document objects."""
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()

        filename = os.path.basename(filepath)

        # ── Extract YAML frontmatter ──────────────────────────────────
        frontmatter: Dict[str, Any] = {}
        body = raw
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError as e:
                    logger.error(f"Bad YAML in {filename}: {e}")
                body = parts[2]

        domain = frontmatter.get("domain", "unknown")
        default_access = frontmatter.get("access_level", "public")

        # ── Find all clause sections ──────────────────────────────────
        sections = self._extract_sections(body, domain, default_access, filename)

        if not sections:
            # Fallback: treat the whole file as one document
            access = default_access
            m = _ACCESS_LEVEL_COMMENT.search(body)
            if m:
                access = m.group(1)
            sections = [
                Document(
                    content=body.strip(),
                    metadata={
                        "domain": domain,
                        "access_level": access,
                        "clause_id": "GENERAL",
                        "source_file": filename,
                        "title": frontmatter.get("title", filename),
                        "chunk_id": f"{filename}_GENERAL",
                    },
                )
            ]

        return sections

    def _extract_sections(
        self,
        body: str,
        domain: str,
        default_access: str,
        filename: str,
    ) -> List[Document]:
        """Extract clause-level sections from markdown body."""
        # Collect (start_pos, clause_id, title) tuples
        markers: List[tuple] = []

        # Pattern 1: ### Title (ID)
        for m in _HEADER_WITH_ID_PARENS.finditer(body):
            title = m.group(2).strip()
            clause_id = m.group(3).strip()
            markers.append((m.start(), m.end(), clause_id, title))

        # Pattern 2: ## ID: Title
        for m in _HEADER_WITH_ID_PREFIX.finditer(body):
            clause_id = m.group(2).strip()
            title = m.group(3).strip()
            markers.append((m.start(), m.end(), clause_id, title))

        if not markers:
            return []

        # Sort by position
        markers.sort(key=lambda x: x[0])

        documents: List[Document] = []
        for i, (start, hdr_end, clause_id, title) in enumerate(markers):
            # Section runs from after the header to the next marker
            next_start = markers[i + 1][0] if i + 1 < len(markers) else len(body)
            section_text = body[hdr_end:next_start].strip()

            if not section_text:
                continue

            # Check for access_level comment within section
            access = default_access
            am = _ACCESS_LEVEL_COMMENT.search(section_text)
            if am:
                access = am.group(1)

            documents.append(
                Document(
                    content=section_text,
                    metadata={
                        "domain": domain,
                        "access_level": access,
                        "clause_id": clause_id,
                        "source_file": filename,
                        "title": title,
                        "chunk_id": f"{filename}_{clause_id}",
                    },
                )
            )

        return documents
