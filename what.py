""" Collection of utility functions used in multiple other modules. """
import csv
from pathlib import Path
from typing import Iterator


logger = logging.getLogger(__name__)


def stream_parse_csv(input_file: Path, progress_bar_title: str | None = None,
                     chunk_size: int | None = None, newline: str | None = None) -> Iterator[list[dict[str, str]]]:
    """ Read a CSV file in chunks lazily, with a progress bar.

    Args:
        input_file (Path): Input CSV file to read data from.
        progress_bar_title (str | None, optional): Title to display on the progress bar. Defaults to None.
        chunk_size (int | None, optional): Bytes to read for every CSV chunk.
                                           Defaults to `2^22` if not provided.
        newline (str | None, optional): Character to use treat as the CSV newline character. Defaults to None".

    Yields:
        list[dict[str, str]]: Lists of size `chunk_size`, containing dictionaries \
                              of individual lines from the input CSV file.
    """
    chunk_size = chunk_size or (2048 * 2048)

    # Determine a line count of the input file, as use it as the length of the progress bar.
    with Path(input_file).open("r", newline=newline) as f:
        file_size = sum(1 for _ in f)

    with (
        Path(input_file).open("r", newline=newline) as f,
        ProgressBar(progress_bar_title, length=file_size) as progress,
    ):
        field_names = None
        while lines := f.readlines(chunk_size):
            # Read the first line and set the field names of the CSV.
            reader = csv.DictReader(lines, fieldnames=field_names)
            if field_names is None:
                field_names = reader.fieldnames

            yield list(reader)

            progress.advance(len(lines))
