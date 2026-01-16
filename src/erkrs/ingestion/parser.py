"""Markdown parser for ERKRS ingestion pipeline.

This module provides functionality to parse markdown documents while preserving
structure, extracting YAML front matter, and handling complex markdown elements.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import marko
from marko import Markdown
from marko.block import BlockElement, CodeBlock, FencedCode, Heading, List as MarkdownList, ListItem, Paragraph, Quote, ThematicBreak
from marko.inline import InlineElement, CodeSpan, Emphasis, Image, Link, RawText, StrongEmphasis
import yaml


@dataclass
class MarkdownNode:
    """Represents a node in the markdown AST."""

    type: str
    content: Optional[str] = None
    children: List['MarkdownNode'] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass
class MarkdownAST:
    """Structured representation of a markdown document."""

    front_matter: Dict[str, Any] = field(default_factory=dict)
    root: MarkdownNode = field(default_factory=lambda: MarkdownNode(type="document"))
    raw_content: str = ""

    def get_headings(self, level: Optional[int] = None) -> List[MarkdownNode]:
        """Get all headings in the document, optionally filtered by level."""
        headings = []
        self._collect_nodes_by_type(self.root, "heading", headings)
        if level is not None:
            headings = [h for h in headings if h.attributes.get("level") == level]
        return headings

    def get_code_blocks(self) -> List[MarkdownNode]:
        """Get all code blocks in the document."""
        code_blocks = []
        self._collect_nodes_by_type(self.root, "code_block", code_blocks)
        return code_blocks

    def get_tables(self) -> List[MarkdownNode]:
        """Get all tables in the document."""
        tables = []
        self._collect_nodes_by_type(self.root, "table", tables)
        return tables

    def get_lists(self) -> List[MarkdownNode]:
        """Get all lists in the document."""
        lists = []
        self._collect_nodes_by_type(self.root, "list", lists)
        return lists

    def _collect_nodes_by_type(self, node: MarkdownNode, node_type: str, result: List[MarkdownNode]) -> None:
        """Recursively collect nodes of a specific type."""
        if node.type == node_type:
            result.append(node)
        for child in node.children:
            self._collect_nodes_by_type(child, node_type, result)


class MarkdownParser:
    """Parser for markdown documents with structure preservation."""

    def __init__(self):
        """Initialize the markdown parser."""
        self.markdown = Markdown()
        self._line_counter = 0

    def parse(self, content: str) -> MarkdownAST:
        """Parse markdown content and return a structured AST.

        Args:
            content: Raw markdown content as a string

        Returns:
            MarkdownAST: Structured representation of the document
        """
        ast = MarkdownAST(raw_content=content)

        # Extract YAML front matter if present
        content, front_matter = self._extract_front_matter(content)
        ast.front_matter = front_matter

        # Parse the markdown content
        self._line_counter = 0
        parsed_doc = self.markdown.parse(content)

        # Convert marko AST to our AST format
        ast.root = self._convert_to_ast(parsed_doc)

        return ast

    def _extract_front_matter(self, content: str) -> tuple[str, Dict[str, Any]]:
        """Extract YAML front matter from markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Tuple of (content without front matter, front matter dict)
        """
        front_matter = {}

        # Match YAML front matter pattern (--- at start, --- or ... at end)
        pattern = r'^---\s*\n(.*?)\n(?:---|\.\.\.)\s*\n'
        match = re.match(pattern, content, re.DOTALL)

        if match:
            yaml_content = match.group(1)
            try:
                front_matter = yaml.safe_load(yaml_content) or {}
            except yaml.YAMLError as e:
                # If YAML parsing fails, store as raw string
                front_matter = {"_raw": yaml_content, "_error": str(e)}

            # Remove front matter from content
            content = content[match.end():]

        return content, front_matter

    def _convert_to_ast(self, element: Union[BlockElement, InlineElement, Any]) -> MarkdownNode:
        """Convert marko element to MarkdownNode.

        Args:
            element: Marko parsed element

        Returns:
            MarkdownNode: Converted node
        """
        node = MarkdownNode(type=self._get_element_type(element))

        # Handle different element types
        if isinstance(element, Heading):
            node.attributes["level"] = element.level
            node.content = self._extract_text(element)
            for child in element.children:
                node.children.append(self._convert_to_ast(child))

        elif isinstance(element, Paragraph):
            node.content = self._extract_text(element)
            for child in element.children:
                node.children.append(self._convert_to_ast(child))

        elif isinstance(element, (FencedCode, CodeBlock)):
            node.content = element.children[0].children if element.children else ""
            if isinstance(element, FencedCode):
                node.attributes["language"] = element.lang or ""
                node.attributes["info_string"] = element.extra or ""

        elif isinstance(element, MarkdownList):
            node.attributes["ordered"] = element.ordered
            node.attributes["start"] = getattr(element, 'start', 1) if element.ordered else None
            for item in element.children:
                node.children.append(self._convert_to_ast(item))

        elif isinstance(element, ListItem):
            node.content = self._extract_text(element)
            for child in element.children:
                node.children.append(self._convert_to_ast(child))

        elif isinstance(element, Quote):
            for child in element.children:
                node.children.append(self._convert_to_ast(child))

        elif isinstance(element, Link):
            node.attributes["url"] = element.dest
            node.attributes["title"] = element.title or ""
            node.content = self._extract_text(element)

        elif isinstance(element, Image):
            node.attributes["url"] = element.dest
            node.attributes["alt"] = self._extract_text(element)
            node.attributes["title"] = element.title or ""

        elif isinstance(element, (Emphasis, StrongEmphasis)):
            node.content = self._extract_text(element)
            for child in element.children:
                node.children.append(self._convert_to_ast(child))

        elif isinstance(element, CodeSpan):
            node.content = element.children

        elif isinstance(element, RawText):
            node.content = element.children

        elif isinstance(element, ThematicBreak):
            pass  # No content for horizontal rules

        elif hasattr(element, 'children'):
            # Generic handling for elements with children
            if isinstance(element.children, str):
                node.content = element.children
            else:
                for child in element.children:
                    if isinstance(child, (BlockElement, InlineElement)):
                        node.children.append(self._convert_to_ast(child))
                    elif isinstance(child, str):
                        text_node = MarkdownNode(type="text", content=child)
                        node.children.append(text_node)

        return node

    def _get_element_type(self, element: Any) -> str:
        """Get the type name for an element.

        Args:
            element: Marko element

        Returns:
            String type name
        """
        type_map = {
            'Heading': 'heading',
            'Paragraph': 'paragraph',
            'FencedCode': 'code_block',
            'CodeBlock': 'code_block',
            'List': 'list',
            'ListItem': 'list_item',
            'Quote': 'quote',
            'Link': 'link',
            'Image': 'image',
            'Emphasis': 'emphasis',
            'StrongEmphasis': 'strong',
            'CodeSpan': 'inline_code',
            'RawText': 'text',
            'ThematicBreak': 'horizontal_rule',
            'Document': 'document',
        }

        element_class = element.__class__.__name__
        return type_map.get(element_class, element_class.lower())

    def _extract_text(self, element: Any) -> str:
        """Extract plain text content from an element.

        Args:
            element: Marko element

        Returns:
            Plain text content
        """
        if isinstance(element, str):
            return element

        if isinstance(element, RawText):
            return element.children

        if isinstance(element, CodeSpan):
            return element.children

        if hasattr(element, 'children'):
            if isinstance(element.children, str):
                return element.children

            text_parts = []
            for child in element.children:
                if isinstance(child, str):
                    text_parts.append(child)
                elif isinstance(child, (BlockElement, InlineElement)):
                    text_parts.append(self._extract_text(child))

            return ''.join(text_parts)

        return ""
