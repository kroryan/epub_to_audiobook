import logging
import re
from typing import List, Tuple

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from audiobook_generator.book_parsers.base_book_parser import BaseBookParser
from audiobook_generator.config.general_config import GeneralConfig

logger = logging.getLogger(__name__)


class EpubBookParser(BaseBookParser):
    MIN_FRAGMENT_CHARS = 300
    CONTINUATION_WORDS = {
        "a", "al", "con", "contra", "de", "del", "desde", "e", "el", "en",
        "entre", "hacia", "hasta", "la", "las", "lo", "los", "ni", "o", "para",
        "por", "que", "sin", "sobre", "su", "un", "una", "y",
    }

    def __init__(self, config: GeneralConfig):
        super().__init__(config)
        self.book = epub.read_epub(self.config.input_file, {"ignore_ncx": True})

    def __str__(self) -> str:
        return super().__str__()

    def validate_config(self):
        if self.config.input_file is None:
            raise ValueError("Epub Parser: Input file cannot be empty")
        if not self.config.input_file.endswith(".epub"):
            raise ValueError(f"Epub Parser: Unsupported file format: {self.config.input_file}")

    def get_book(self):
        return self.book

    def get_book_title(self) -> str:
        if self.book.get_metadata('DC', 'title'):
            return self.book.get_metadata("DC", "title")[0][0]
        return "Untitled"

    def get_book_author(self) -> str:
        if self.book.get_metadata('DC', 'creator'):
            return self.book.get_metadata("DC", "creator")[0][0]
        return "Unknown"

    def get_chapters(self, break_string) -> List[Tuple[str, str]]:
        chapters = []
        search_and_replaces = self.get_search_and_replaces()
        for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            item_name = (item.get_name() or "").lower()
            item_properties = set(getattr(item, "properties", ()) or ())
            if "nav" in item_properties or item_name.endswith(("nav.xhtml", "toc.xhtml", "toc.html")):
                logger.debug(f"Skipping EPUB navigation document: {item.get_name()}")
                continue

            content = item.get_content()
            soup = BeautifulSoup(content, "lxml-xml")
            raw = soup.get_text(strip=False)
            logger.debug(f"Raw text: <{raw[:]}>")

            # Replace excessive whitespaces and newline characters based on the mode
            if self.config.newline_mode == "single":
                cleaned_text = re.sub(r"[\n]+", break_string, raw.strip())
            elif self.config.newline_mode == "double":
                cleaned_text = re.sub(r"[\n]{2,}", break_string, raw.strip())
            elif self.config.newline_mode == "none":
                cleaned_text = re.sub(r"[\n]+", " ", raw.strip())
            else:
                raise ValueError(f"Invalid newline mode: {self.config.newline_mode}")

            logger.debug(f"Cleaned text step 1: <{cleaned_text[:]}>")
            cleaned_text = re.sub(r"\s+", " ", cleaned_text)
            logger.debug(f"Cleaned text step 2: <{cleaned_text[:100]}>")

            # Removes end-note numbers
            if self.config.remove_endnotes:
                cleaned_text = re.sub(r'(?<=[a-zA-Z.,!?;”")])\d+', "", cleaned_text)
                logger.debug(f"Cleaned text step 4: <{cleaned_text[:100]}>")

            # Removes references numbers like [1] or [2.3]
            if self.config.remove_reference_numbers:
                cleaned_text = re.sub(r'\[\d+(\.\d+)?\]', '', cleaned_text)
                logger.debug(f"Cleaned text step 4.1 (removed brackets): <{cleaned_text[:100]}>")

            # Does user defined search and replaces
            for search_and_replace in search_and_replaces:
                cleaned_text = re.sub(search_and_replace['search'], search_and_replace['replace'], cleaned_text)
            logger.debug(f"Cleaned text step 5: <{cleaned_text[:100]}>")

            # Get proper chapter title
            if self.config.title_mode == "auto":
                title = ""
                title_levels = ['title', 'h1', 'h2', 'h3']
                for level in title_levels:
                    if soup.find(level):
                        title = soup.find(level).text
                        break
                if title.strip() == "" or re.match(r'^\d{1,3}$',title) is not None:
                    title = cleaned_text[:60]
            elif self.config.title_mode == "tag_text":
                title = ""
                title_levels = ['title', 'h1', 'h2', 'h3']
                for level in title_levels:
                    if soup.find(level):
                        title = soup.find(level).text
                        break
                if title.strip() == "":
                    title = "<blank>"
            elif self.config.title_mode == "first_few":
                title = cleaned_text[:60]
            else:
                raise ValueError("Unsupported title_mode")
            logger.debug(f"Raw title: <{title}>")
            title = self._sanitize_title(title, break_string)
            logger.debug(f"Sanitized title: <{title}>")

            chapters.append((title, cleaned_text))
            soup.decompose()
        chapters = self._consolidate_fragmented_documents(chapters)
        logger.info(
            "EPUB chapter consolidation: %s readable chapters after joining short document fragments",
            len(chapters),
        )
        return chapters

    @classmethod
    def _ends_sentence_or_heading(cls, text: str) -> bool:
        """Detect a safe boundary between two EPUB documents.

        EPUBs produced from PDFs/e-books often split in the middle of a
        sentence. A final colon/semicolon is also treated as a boundary so
        headings such as ``ACTO UNO:`` do not swallow the following section.
        """
        stripped = (text or "").rstrip()
        if not stripped:
            return True
        return stripped[-1] in ".!?…。！？:;)]}»”’"

    @classmethod
    def _starts_continuation(cls, text: str, previous_text: str) -> bool:
        stripped = (text or "").lstrip()
        if not stripped:
            return True
        if stripped[0] in ",.;:!?)]}»”’":
            return True
        first_word = re.match(r"([\wÁÉÍÓÚÜÑáéíóúüñ]+)", stripped)
        if first_word and first_word.group(1)[0].islower():
            return True
        previous_words = re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ]+", previous_text or "")
        return bool(previous_words and previous_words[-1].lower() in cls.CONTINUATION_WORDS)

    @staticmethod
    def _join_fragment(left: str, right: str) -> str:
        left = (left or "").rstrip()
        right = (right or "").lstrip()
        if not left:
            return right
        if not right:
            return left
        return f"{left} {right}"

    @classmethod
    def _consolidate_fragmented_documents(
        cls, chapters: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """Join tiny EPUB spine documents that are page/phrase fragments.

        A document boundary is not necessarily a chapter boundary. This is
        especially common in Calibre-generated EPUBs, where a page break can
        leave words such as ``los resultados del`` in separate XHTML files.
        Short runs are attached to the preceding unfinished sentence or to the
        following document when they look like a heading/lead-in.
        """
        if not chapters:
            return []

        consolidated: List[Tuple[str, str]] = []
        index = 0
        while index < len(chapters):
            title, text = chapters[index]
            if len(text.strip()) >= cls.MIN_FRAGMENT_CHARS:
                consolidated.append((title, text))
                index += 1
                continue

            run_start = index
            fragments = []
            while index < len(chapters) and len(chapters[index][1].strip()) < cls.MIN_FRAGMENT_CHARS:
                fragments.append(chapters[index][1])
                index += 1
            fragment_text = " ".join(part.strip() for part in fragments if part.strip())

            if not fragment_text:
                continue

            if consolidated and not cls._ends_sentence_or_heading(consolidated[-1][1]):
                previous_title, previous_text = consolidated[-1]
                previous_text = cls._join_fragment(previous_text, fragment_text)

                # If the next document starts with a lowercase word or the
                # previous fragment ends in a connector such as "del", it is
                # the continuation of the same sentence too.
                if index < len(chapters) and cls._starts_continuation(
                    chapters[index][1], previous_text
                ):
                    previous_text = cls._join_fragment(previous_text, chapters[index][1])
                    index += 1
                consolidated[-1] = (previous_title, previous_text)
            elif index < len(chapters):
                next_title, next_text = chapters[index]
                consolidated.append((next_title, cls._join_fragment(fragment_text, next_text)))
                index += 1
            elif consolidated:
                previous_title, previous_text = consolidated[-1]
                consolidated[-1] = (previous_title, cls._join_fragment(previous_text, fragment_text))
            else:
                consolidated.append((title, fragment_text))

            logger.debug(
                "Joined EPUB fragment documents %s-%s (%s chars)",
                run_start + 1,
                index,
                len(fragment_text),
            )

        return consolidated

    def get_search_and_replaces(self):
        search_and_replaces = []
        if self.config.search_and_replace_file:
            with open(self.config.search_and_replace_file) as fp:
                search_and_replace_content = fp.readlines()
                for search_and_replace in search_and_replace_content:
                    if '==' in search_and_replace and not search_and_replace.startswith('==') and not search_and_replace.endswith('==') and not search_and_replace.startswith('#'):
                        search_and_replaces = search_and_replaces + [ {'search': r"{}".format(search_and_replace.split('==')[0]), 'replace': r"{}".format(search_and_replace.split('==')[1][:-1])} ]
        return search_and_replaces

    @staticmethod
    def _sanitize_title(title, break_string) -> str:
        # replace MAGIC_BREAK_STRING with a blank space
        # strip incase leading bank is missing
        title = title.replace(break_string, " ")
        sanitized_title = re.sub(r"[^\w\s]", "", title, flags=re.UNICODE)
        sanitized_title = re.sub(r"\s+", "_", sanitized_title.strip())
        return sanitized_title
