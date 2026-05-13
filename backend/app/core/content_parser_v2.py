"""
Content Parser V2 - LLM-assisted textbook content structuring
Step 1: Extract raw text from docx/pdf (rule-based)  
Step 2: LLM-assisted structure analysis (THE CORE VALUE)
Step 3: Persist to content_nodes table

Usage:
    parser = ContentParserV2(llm=llm_helper)
    nodes = await parser.parse_from_docx(filepath, textbook_id, category_id)
"""
import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import fitz  # PyMuPDF
from docx import Document

logger = logging.getLogger(__name__)

# ============ Prompt Engineering ============

CONTENT_ANALYSIS_SYSTEM_PROMPT = """You are an expert educational content analyst specializing in emergency response and public safety training materials (应急救援与公共安全培训). Your task is to analyze Chinese-language textbook content and produce highly structured information.

## Your Task
For the provided textbook section, identify and extract:

1. **Section Header**: The most specific heading that introduces this block of content
2. **Content Type**: Classify as one of:
   - "chapter" - major chapter heading
   - "section" - section within a chapter  
   - "subsection" - sub-section
   - "concept" - introduces a key concept or theory
   - "procedure" - step-by-step operational procedure
   - "safety_rule" - safety requirement or warning
   - "case_study" - real-world case analysis
   - "exercise" - practice exercise or question
   - "summary" - chapter/section summary
   - "definition" - term definition
   - "table" - data table
3. **Learning Objectives** (1-5 items): Specific, measurable skills/knowledge students should gain
4. **Key Concepts** (2-8 items): Important terms, theories, or principles introduced
5. **Difficulty Level**: "beginner" | "intermediate" | "advanced" | "expert"
6. **Prerequisites**: Concepts that SHOULD be understood before this section (empty list if none)
7. **Safety Notes** (0-3 items): Critical safety information or warnings
8. **Core Content Summary** (2-5 sentences in Chinese): Concise summary of the section's main points

## Output Format
Return ONLY a valid JSON object (no markdown, no explanation):
{
  "nodes": [
    {
      "title": "section title",
      "content_type": "concept",
      "learning_objectives": ["obj1", "obj2"],
      "key_concepts": ["concept1", "concept2"],
      "difficulty_level": "intermediate",
      "prerequisites": ["prereq1"],
      "safety_notes": ["warning1"],
      "summary": "Concise Chinese summary of core content."
    }
  ]
}

## Rules
- Preserve original terminology - do NOT translate specialized diving/safety terms
- All text fields (title, summary) MUST be in Chinese
- Learning objectives should be actionable (start with verbs like 理解/掌握/能够/识别)
- Difficulty: beginner=basic awareness, intermediate=operational knowledge, advanced=professional application, expert=specialized mastery
- If the content does not contain safety information, return an empty safety_notes array
- Merge very short adjacent sections into one node
- Split very long sections into multiple nodes"""


@dataclass
class ParsedNode:
    """Intermediate representation of a parsed content node"""
    title: str
    content_type: str = "section"
    learning_objectives: list[str] = field(default_factory=list)
    key_concepts: list[str] = field(default_factory=list)
    difficulty_level: str = "beginner"
    prerequisites: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    summary: str = ""
    content_raw: str = ""
    page_start: int | None = None
    page_end: int | None = None
    parent_title: str | None = None
    level: int = 0
    sort_order: int = 0
    source_location: str = ""


class ContentParserV2:
    """LLM-assisted textbook content parser"""

    def __init__(self, llm_helper=None):
        from app.core import llm_config
        from app.core.llm import get_llm_helper
        self.llm = llm_helper or get_llm_helper()
        self.llm_config = llm_config
        self._chunk_size = 6000
        self._db: Any = None  # set by caller before parsing

    async def parse_from_docx(
        self,
        filepath: str,
        textbook_id: int,
        category_id: int,
        db_session: Any = None,
    ) -> list[ParsedNode]:
        """Full parse pipeline: DOCX -> structured nodes"""
        # Step 1: Extract raw text chunks
        text = self._extract_docx_text(filepath)
        raw_chunks = self._chunk_by_headings(text)

        # Check if LLM is enabled for this textbook
        if db_session:
            allowed, reason = await self.llm_config.check_llm_allowed(
                db_session, textbook_id=textbook_id
            )
            if not allowed:
                logger.warning(f"LLM not allowed for textbook {textbook_id}: {reason}")
                return []
            # Load LLM runtime config
            cfg = await self.llm_config.db_get_llm_runtime_config(db_session)
            self.llm.configure(cfg)

        # Step 2: LLM-assisted structuring (for each chunk)
        all_nodes = []
        for i, chunk in enumerate(raw_chunks):
            logger.info(f"Processing chunk {i+1}/{len(raw_chunks)} ({len(chunk['text'])} chars)")
            nodes = await self._analyze_chunk_llm(
                chunk_text=chunk["text"],
                heading_hint=chunk.get("heading", ""),
                page_start=chunk.get("page_start"),
                chunk_index=i,
            )
            # Annotate with source info
            for node in nodes:
                node.source_location = f"docx:{filepath}:chunk{i}"
                node.page_start = chunk.get("page_start")
            all_nodes.extend(nodes)

        # Step 3: Post-process - merge adjacent, reorder, generate content_hash
        all_nodes = self._post_process(all_nodes, textbook_id)

        return all_nodes

    async def parse_from_pdf(
        self,
        filepath: str,
        textbook_id: int,
        category_id: int,
        db_session: Any = None,
    ) -> list[ParsedNode]:
        """Full parse pipeline: PDF -> structured nodes"""
        pages = self._extract_pdf_pages(filepath)
        if not pages:
            return []

        # Concatenate pages with page markers
        full_text = ""
        page_map = {}  # char_index -> page_number
        for p in pages:
            start = len(full_text)
            full_text += p["text"] + "\n"
            end = len(full_text)
            for i in range(start, end):
                page_map[i] = p["page"]

        # Chunk by headings and length
        raw_chunks = self._chunk_by_headings(full_text, page_map=page_map)

        all_nodes = []
        for i, chunk in enumerate(raw_chunks):
            logger.info(f"Processing chunk {i+1}/{len(raw_chunks)} ({len(chunk['text'])} chars)")
            nodes = await self._analyze_chunk_llm(
                chunk_text=chunk["text"],
                heading_hint=chunk.get("heading", ""),
                page_start=chunk.get("page_start"),
                chunk_index=i,
            )
            for node in nodes:
                node.source_location = f"pdf:{filepath}:chunk{i}"
            all_nodes.extend(nodes)

        all_nodes = self._post_process(all_nodes, textbook_id)
        return all_nodes

    async def _analyze_chunk_llm(
        self,
        chunk_text: str,
        heading_hint: str = "",
        page_start: int | None = None,
        chunk_index: int = 0,
    ) -> list[ParsedNode]:
        """Step 2: Send chunk to LLM for structure analysis"""
        # Trim to avoid exceeding context window
        max_chars = 8000
        if len(chunk_text) > max_chars:
            chunk_text = chunk_text[:max_chars] + "\n...[content truncated]..."

        user_prompt = f"""Analyze the following textbook content:

## Context
- Previous heading: {heading_hint or "Not available"}
- Chunk index: {chunk_index + 1}

## Content
{chunk_text}"""

        try:
            result = await self.llm.analyze_content_json(
                system_prompt=CONTENT_ANALYSIS_SYSTEM_PROMPT,
                content=user_prompt,
                temperature=0.15,
            )
        except Exception as e:
            logger.error(f"LLM analysis failed for chunk {chunk_index}: {e}")
            # Fallback: create a single node from raw content
            return [self._fallback_node(chunk_text, heading_hint, chunk_index)]

        nodes = []
        items = result.get("nodes", [result]) if isinstance(result, dict) else result
        if not isinstance(items, list):
            items = [items]

        for item in items:
            node = ParsedNode(
                title=item.get("title", heading_hint or f"Section {chunk_index+1}"),
                content_type=item.get("content_type", "section"),
                learning_objectives=item.get("learning_objectives", []),
                key_concepts=item.get("key_concepts", []),
                difficulty_level=item.get("difficulty_level", "beginner"),
                prerequisites=item.get("prerequisites", []),
                safety_notes=item.get("safety_notes", []),
                summary=item.get("summary", ""),
                content_raw=chunk_text[:2000],
                sort_order=chunk_index * 100 + len(nodes),
            )
            nodes.append(node)

        return nodes

    def _extract_docx_text(self, filepath: str) -> str:
        """Extract plain text from DOCX file"""
        doc = Document(filepath)
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                style = para.style.name if para.style else ""
                if "Heading" in style or "heading" in style.lower():
                    # Preserve heading markers for chunking
                    level = 1
                    level_match = re.search(r'(\d+)', style)
                    if level_match:
                        level = min(int(level_match.group(1)), 6)
                    prefix = "#" * level
                    paragraphs.append(f"{prefix} {text}")
                else:
                    paragraphs.append(text)
        return "\n\n".join(paragraphs)

    def _extract_pdf_pages(self, filepath: str) -> list[dict]:
        """Extract text per page from PDF"""
        pages = []
        try:
            doc = fitz.open(filepath)
            for i, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    pages.append({"page": i + 1, "text": text.strip()})
            doc.close()
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
        return pages

    def _chunk_by_headings(
        self, text: str, page_map: dict[int, int] | None = None
    ) -> list[dict]:
        """Split text into chunks at heading boundaries"""
        chunks = []
        # Split on markdown-style headings or Chinese heading patterns
        heading_pattern = re.compile(
            r'(?:^|\n)(?:(#{1,3})\s+(.+)|第[一二三四五六七八九十百千\d]+[章节篇])\s*',
            re.MULTILINE,
        )

        _parts = heading_pattern.split(text)  # noqa: F841
        _current_heading = ""
        _current_text = ""  # noqa: F841
        start_pos = 0

        # Simple approach: split on double newlines and markdown headings
        lines = text.split("\n")
        buffer = []
        current_heading = ""

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this is a heading
            heading_match = re.match(r'^(#{1,3})\s+(.+)', stripped)
            ch_heading_match = re.match(
                r'^(第[一二三四五六七八九十百千\d]+[章节篇]|[\d]+[\.、]\s*(?:[^a-zA-Z].{3,}))',
                stripped
            )

            if heading_match or ch_heading_match:
                # Save previous chunk
                if buffer:
                    text_block = "\n".join(buffer)
                    if len(text_block) > 50:
                        chunks.append({
                            "text": text_block,
                            "heading": current_heading,
                            "page_start": page_map.get(start_pos) if page_map else None,
                        })
                    buffer = []

                if heading_match:
                    current_heading = heading_match.group(2).strip()
                else:
                    current_heading = stripped[:50]
                buffer.append(stripped)
                start_pos = len("\n".join(lines[:lines.index(line)]))
            else:
                buffer.append(stripped)

        # Last chunk
        if buffer:
            text_block = "\n".join(buffer)
            if len(text_block) > 50:
                chunks.append({
                    "text": text_block,
                    "heading": current_heading,
                    "page_start": page_map.get(start_pos) if page_map else None,
                })

        return chunks

    def _post_process(self, nodes: list[ParsedNode], textbook_id: int) -> list[ParsedNode]:
        """Clean up and enhance parsed nodes"""
        for i, node in enumerate(nodes):
            node.sort_order = i * 10
            # Validate and normalize fields
            if node.difficulty_level not in ("beginner", "intermediate", "advanced", "expert"):
                node.difficulty_level = "beginner"
            if node.content_type not in (
                "chapter", "section", "subsection", "concept", "procedure",
                "safety_rule", "case_study", "exercise", "summary", "definition", "table"
            ):
                node.content_type = "section"
            # Generate content hash
            hash_input = f"{textbook_id}:{node.title}:{node.summary[:100]}"
            _node_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]  # noqa: F841
        return nodes

    @staticmethod
    def _fallback_node(text: str, heading: str, index: int) -> ParsedNode:
        """Create a minimal node when LLM analysis fails"""
        return ParsedNode(
            title=heading or f"Section {index+1}",
            content_type="section",
            summary=text[:300],
            content_raw=text[:2000],
            sort_order=index * 100,
        )


