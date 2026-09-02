import logging
import multiprocessing
import os

from audiobook_generator.book_parsers.base_book_parser import get_book_parser
from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.tts_providers.base_tts_provider import get_tts_provider
from audiobook_generator.utils.log_handler import setup_logging

logger = logging.getLogger(__name__)


def confirm_conversion():
    logger.info("Do you want to continue? (y/n)")
    answer = input()
    if answer.lower() != "y":
        logger.info("Aborted.")
        exit(0)


def get_total_chars(chapters):
    total_characters = 0
    for title, text in chapters:
        total_characters += len(text)
    return total_characters


class AudiobookGenerator:
    def __init__(self, config: GeneralConfig):
        self.config = config
        self._coqui_provider = None

    def __str__(self) -> str:
        return f"{self.config}"

    def process_chapter(self, idx, title, text, book_parser):
        """Process a single chapter: write text (if needed) and convert to audio."""
        try:
            logger.info(f"Processing chapter {idx}: {title}")
            # CUDA-backed Coqui models must stay in the process that loaded
            # them. Reusing this provider also avoids reloading the model for
            # every chapter when Coqui is selected.
            if self.config.tts == "coqui":
                if self._coqui_provider is None:
                    self._coqui_provider = get_tts_provider(self.config)
                tts_provider = self._coqui_provider
            else:
                tts_provider = get_tts_provider(self.config)

            # Save chapter text if required
            if self.config.output_text:
                text_file = os.path.join(self.config.output_folder, f"{idx:04d}_{title}.txt")
                with open(text_file, "w", encoding="utf-8") as f:
                    f.write(text)

            # Skip audio generation in preview mode
            if self.config.preview:
                return True

            # Generate audio file
            output_file = os.path.join(
                self.config.output_folder,
                f"{idx:04d}_{title}.{tts_provider.get_output_file_extension()}",
            )
            audio_tags = AudioTags(
                title, book_parser.get_book_author(), book_parser.get_book_title(), idx
            )
            tts_provider.text_to_speech(text, output_file, audio_tags)

            logger.info(f"✅ Converted chapter {idx}: {title}, output file: {output_file}")

            return True
        except Exception as e:
            logger.exception(f"Error processing chapter {idx}, error: {e}")
            return False

    def process_chapter_wrapper(self, args):
        """Wrapper for process_chapter to handle unpacking args for imap."""
        idx, title, text, book_parser = args
        return idx, self.process_chapter(idx, title, text, book_parser)

    def run(self):
        try:
            logger.info("Starting audiobook generation...")
            book_parser = get_book_parser(self.config)
            tts_provider = get_tts_provider(self.config)
            if self.config.tts == "coqui":
                self._coqui_provider = tts_provider

            # The WebUI starts chapter workers in separate processes. Resolve the
            # user-provided output directory before spawning them so relative
            # paths remain valid in every worker and during final MP3 export.
            if not self.config.output_folder:
                raise ValueError("An output directory is required")
            self.config.output_folder = os.path.abspath(
                os.path.expanduser(self.config.output_folder)
            )
            os.makedirs(self.config.output_folder, exist_ok=True)
            chapters = book_parser.get_chapters(tts_provider.get_break_string())
            # Filter out empty or very short chapters
            chapters = [(title, text) for title, text in chapters if text.strip()]

            logger.info(f"Chapters count: {len(chapters)}.")

            # Check chapter start and end args
            if self.config.chapter_start < 1 or self.config.chapter_start > len(chapters):
                raise ValueError(
                    f"Chapter start index {self.config.chapter_start} is out of range. Check your input."
                )
            if self.config.chapter_end < -1 or self.config.chapter_end > len(chapters):
                raise ValueError(
                    f"Chapter end index {self.config.chapter_end} is out of range. Check your input."
                )
            if self.config.chapter_end == -1:
                self.config.chapter_end = len(chapters)
            if self.config.chapter_start > self.config.chapter_end:
                raise ValueError(
                    f"Chapter start index {self.config.chapter_start} is larger than chapter end index {self.config.chapter_end}. Check your input."
                )

            logger.info(
                f"Converting chapters from {self.config.chapter_start} to {self.config.chapter_end}."
            )

            # Initialize total_characters to 0
            total_characters = get_total_chars(
                chapters[self.config.chapter_start - 1 : self.config.chapter_end]
            )
            logger.info(f"Total characters in selected book chapters: {total_characters}")
            rough_price = tts_provider.estimate_cost(total_characters)
            logger.info(f"Estimate book voiceover would cost you roughly: ${rough_price:.2f}\n")

            # Prompt user to continue if not in preview mode
            if self.config.no_prompt:
                logger.info("Skipping prompt as passed parameter no_prompt")
            elif self.config.preview:
                logger.info("Skipping prompt as in preview mode")
            else:
                confirm_conversion()

            # Prepare chapters for processing
            chapters_to_process = chapters[self.config.chapter_start - 1 : self.config.chapter_end]
            tasks = [
                (idx, title, text, book_parser)
                for idx, (title, text) in enumerate(
                    chapters_to_process, start=self.config.chapter_start
                )
            ]

            # Track failed chapters
            failed_chapters = []

            # CUDA-backed Coqui models cannot safely be loaded from forked
            # workers. Process Coqui chapters sequentially in this process;
            # cloud providers retain the existing parallel path.
            if self.config.tts == "coqui":
                logger.info("Coqui TTS selected: processing chapters sequentially to keep CUDA stable")
                results = [self.process_chapter_wrapper(task) for task in tasks]
            else:
                with multiprocessing.Pool(
                    processes=self.config.worker_count,
                    initializer=setup_logging,
                    initargs=(self.config.log, self.config.log_file, True)
                ) as pool:
                    results = list(pool.imap_unordered(self.process_chapter_wrapper, tasks))

            # Check for failed chapters
            for idx, success in results:
                if not success:
                    chapter_title = chapters_to_process[idx - self.config.chapter_start][0]
                    failed_chapters.append((idx, chapter_title))

            if failed_chapters:
                logger.warning("The following chapters failed to convert:")
                for idx, title in failed_chapters:
                    logger.warning(f"  - Chapter {idx}: {title}")
                logger.info(f"Conversion completed with {len(failed_chapters)} failed chapters. Check your output directory: {self.config.output_folder} and log file: {self.config.log_file} for more details.")
            else:
                logger.info(f"All chapters converted successfully. Check your output directory: {self.config.output_folder}")

        except KeyboardInterrupt:
            logger.info("Audiobook generation process interrupted by user (Ctrl+C).")
        except Exception as e:
            logger.exception(f"Error during audiobook generation: {e}")
        finally:
            logger.debug("AudiobookGenerator.run() method finished.")
