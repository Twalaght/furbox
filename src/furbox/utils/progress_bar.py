""" Custom implementation of Rich progress bars.

Allows for multiple progress bars with different formats, in addition to custom formatted progress bars.
"""
import atexit
from enum import auto, StrEnum
from types import TracebackType
from typing import Self

import rich.progress
import rich.table
from fluffless.utils import logging
from fluffless.utils.console import console
from rich.console import Group
from rich.live import Live
from rich.progress import filesize, Progress
from rich.text import Text

logger = logging.getLogger(__name__)


class ProgressBarStyle(StrEnum):
    """ String enum of all permissible progress bar styles. """

    GENERIC = auto()  # SI prefixed units (K, M, G, etc) with rounding.
    FILE = auto()     # File transfer operations, measured in bytes with rounding.


class MofNWithUnits(rich.progress.MofNCompleteColumn):
    """ Renders completed "count/total" progress bar with SI unit prefixes.

    Implements the base class with dynamic bar resizing if the length is updated.
    """

    def render(self, task: rich.progress.Task) -> Text:
        """ Render progress bar column output. """
        completed = int(task.completed)

        # Determine the units and suffix to display on the progress bar.
        unit, suffix = filesize.pick_unit_and_suffix(
            size=int(task.total) if task.total is not None else completed,
            suffixes=["", "K", "M", "G", "T", "P", "E", "Z", "Y"],
            base=1000,
        )
        precision = 0 if unit == 1 else 1

        completed_ratio = completed / unit
        completed_str = f"{completed_ratio:,.{precision}f}"

        if task.total is not None:
            total = int(task.total)
            total_ratio = total / unit
            total_str = f"{total_ratio:,.{precision}f}"
        else:
            total_str = "?"

        # Generate the output string, and dynamically set the column width.
        output = f"{completed_str}/{total_str}{suffix}"
        if self._table_column:
            self._table_column.width = len(output)

        return Text(output, style="progress.download")


class ProgressManager:
    """ Initialise with a Rich live display instance and an empty set of progress bars. """

    def __init__(self) -> None:
        self.live = Live(console=console, refresh_per_second=10)
        self.progress_bars: dict[int, Progress] = {}
        atexit.register(self.close)

    def update_display(self) -> None:
        """ Update the live display with an ordered list of active progress bars. """
        renderables = [self.progress_bars[task_id] for task_id in sorted(self.progress_bars.keys())]
        self.live.update(Group(*renderables))

        # If not already running, start the live display.
        if not self.live.is_started:
            self.live.start()

    def remove_bar(self, task_id: int, persist: bool) -> None:
        """ Remove a progress bar from the live display.

        Args:
            task_id (int): Task ID associated with the progress bar to remove.
            persist (bool): If True, keep the progress bar displayed after removing it. \
                            Otherwise clear the progress bar from the display.
        """
        # Remove the progress bar associated with the task ID.
        progress = self.progress_bars.pop(task_id)

        if persist:
            # Set the live group to display only the specified progress bar, and stop the live display.
            self.live.update(Group(progress))
            self.live.stop()

        self.update_display()

    def clear(self) -> None:
        """ Reset all internal state and empty the live display. """
        self.progress_bars = {}
        self.update_display()

    def close(self) -> None:
        """ Terminate the live display and re-enable the console cursor.

        If not performed, can leave the terminal without a cursor after Python exits.
        """
        self.clear()
        console.show_cursor(True)


class ProgressBar:
    """ Create a progress bar using Rich.

    Can optionally have a description, length, file specific formatting, and specify if the progress bar
    should be left on screen after being completed.

    By default Rich does not allow progress bars of different formats to run concurrently. As such, this
    is implemented with a custom ProgressBar class and ProgressManager instance with a live Rich display.

    Args:
        description (str, optional): Description to display on the progress bar. Defaults to no description.
        length (int | None, optional): Length of the progress bar. Defaults to None, acting as an indeterminate length.
        chunk_size (int | None, optional):
            Only refresh the progress bar each time the progress increases by at least this many units.
            Defaults to None, which will allow updates of smallest increment of size 1.
        style (ProgressBarStyle, optional): Display style to use. Defaults to "generic".
        persist (bool, optional): Leave the progress bar on screen after completion if True. Defaults to True.
    """

    def __init__(
        self, description: str = "", length: int | None = None, chunk_size: int | None = None,
        style: ProgressBarStyle = ProgressBarStyle.GENERIC, persist: bool = True,
    ) -> None:
        self.progress = self._create_progress_bar(style)
        self.task_id = self.progress.add_task(description=description, total=length)
        self.persist = persist
        self.advance_buffer = 0
        self.chunk_size = chunk_size

        self.bar_id = len(_progress_manager.progress_bars)

        _progress_manager.progress_bars[self.bar_id] = self.progress
        _progress_manager.update_display()

    def __enter__(self) -> Self:
        """ Allow the progress bar to be initialised in a context manager. """
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        """ Close the progress bar when exiting a context manager. """
        self.close()

    def advance(self, length: int = 1) -> None:
        """ Advance the progress bar.

        Args:
            length (int, optional): Amount to advance the progress bar by. Defaults to 1.
        """
        # Get the task object associated with the progress bar's task ID.
        task = self.progress._tasks[self.task_id]

        advance = length

        # If a total is set for the bar, limit advances such that they cannot overshoot the length of the bar.
        if task.total and task.completed + advance >= task.total:
            advance = task.total - task.completed
            self.advance_buffer = 0

        elif self.chunk_size:
            self.advance_buffer += advance

            # Increment the progress bar in whole numbers of chunks, leaving any remainders in the advance buffer.
            advance = (self.advance_buffer // self.chunk_size) * self.chunk_size
            self.advance_buffer %= self.chunk_size

        # If the progress bar is to be advanced by any amount, update it and refresh.
        if advance:
            self.progress.update(self.task_id, advance=advance, refresh=True)
            _progress_manager.live.refresh()

    def set_length(self, length: int) -> None:
        """ Set the length of the progress bar. """
        self.progress.update(self.task_id, total=length)

    def close(self) -> None:
        """ Finish and close the progress bar. """
        task = self.progress._tasks[self.task_id]

        # If the progress bar did not have a total, set the total to the completed value before finishing it.
        if not task.total:
            self.progress.update(self.task_id, total=task.completed, completed=task.completed)
            _progress_manager.live.refresh()

        _progress_manager.remove_bar(self.bar_id, persist=self.persist)

    @staticmethod
    def _create_progress_bar(style: ProgressBarStyle) -> rich.progress.Progress:
        """ Create a Rich progress bar instance.

        Args:
            style (ProgressBarStyle): Display style to use.

        Returns:
            rich.progress.Progress: Rich progress bar instance.
        """
        custom_styles = {
            ProgressBarStyle.GENERIC: [MofNWithUnits(table_column=rich.table.Column(justify="center"))],
            ProgressBarStyle.FILE: [rich.progress.DownloadColumn(), "•", rich.progress.TransferSpeedColumn()],
        }

        return rich.progress.Progress(
            rich.progress.SpinnerColumn(style="progress.data.speed"),
            rich.progress.TextColumn("{task.description}", justify="left", table_column=rich.table.Column(width=40)),
            rich.progress.BarColumn(bar_width=None, finished_style="green"),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            *custom_styles[style],
            "•",
            rich.progress.TimeElapsedColumn(),
            *(["/", rich.progress.TimeRemainingColumn()] if style == ProgressBarStyle.FILE else []),
            transient=False,
            console=console,
        )


_progress_manager = ProgressManager()
