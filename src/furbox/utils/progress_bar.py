""" Class to handle custom implementation of Rich progress bars.

Custom implementation enables display of an arbitrary number of progress bars with different formats.

Consumed as an importable singleton instance of a `CustomProgress()` object.
"""
import atexit
from typing import NamedTuple

import rich.progress
from fluffless.utils.console import console
from rich.console import Group
from rich.live import Live


class ProgressBar(NamedTuple):
    """ Simple structure to relate a `Progress` instance to a corresponding task ID. """

    progress: rich.progress.Progress
    task_id: int


class CustomProgress:
    """ Initialise with a Live display instance and an empty list of progress bars. """

    def __init__(self) -> None:
        self.live = Live(console=console, refresh_per_second=10)
        self.live.start()

        self.progress_bars: dict[int, ProgressBar] = {}
        self.order:         list[int] = []
        self.counter:       int = 0

        # Register an atexit event such that the console is restored properly, even on an early termination
        atexit.register(self._close)

    def add_task(self, description: str, total: int = None, is_file: bool = False) -> int:
        """ Add a progress bar to the custom handlers internal stack.

        Args:
            description (str): Description to use in the progress bar.
            total (int, optional): Total length of the progress bar. Defaults to None, where it will display \
                                   a unique progress animation for an indeterminate length.
            is_file (bool, optional): Use file specific columns if True, otherwise use generic columns. \
                                      Defaults to False.

        Returns:
            int: Task ID of the created progress bar.
        """
        progress = self._create_progress_bar(is_file)
        progress_task_id = progress.add_task(description, total=total)

        # Assign the task an ID from the counter and increment it
        overall_task_id = self.counter
        self.counter += 1

        # Append the progress bar and order value to their associated structures
        self.order.append(overall_task_id)
        self.progress_bars[overall_task_id] = ProgressBar(
            progress=progress,
            task_id=progress_task_id,
        )

        self._update_renderables()

        return overall_task_id

    def advance(self, task_id: int, value: int = 1) -> None:
        """ Advance the completion value of a given progress bar.

        Args:
            task_id (int): Task ID corresponding to the given progress bar.
            value (int, optional): Amount to increment the completion value by. Defaults to 1.
        """
        self.progress_bars[task_id].progress.advance(self.progress_bars[task_id].task_id, value)

    def finish(self, task_id: int, persist: bool = False) -> None:
        """ Close a progress bar, optionally keeping it displayed after finishing.

        Args:
            task_id (int): Task ID corresponding to the given progress bar.
            persist (bool, optional): Keep the progress bar displayed if True, otherwise clear it upon finishing. \
                                      Defaults to False.
        """
        self.order.remove(task_id)
        progress = self.progress_bars.pop(task_id).progress

        if persist:
            # Set the live group to display only the specified progress bar, and stop the live display
            self.live.update(Group(progress))
            self.live.stop()

        self._update_renderables()

    def clear(self) -> None:
        """ Reset all internal state and update the live display to an empty set. """
        self.progress_bars = {}
        self.order = []
        self.counter = 0
        self.live.update(Group())

    def _update_renderables(self) -> None:
        """ Update the live display with an ordered list of active progress bars. """
        renderables = [self.progress_bars[task_id].progress for task_id in self.order]
        self.live.update(Group(*renderables))

        # If required, restart the live display
        if not self.live.is_started:
            self.live.start()

    def _close(self) -> None:
        """ Terminate the live display and reenable the console cursor. """
        self.clear()
        console.show_cursor(True)

    @staticmethod
    def _create_progress_bar(is_file: bool = True) -> rich.progress.Progress:
        """ Create a Rich progress bar instance.

        Args:
            is_file (bool, optional): Display columns relevant to downloading a file, \
                                      otherwise display generic columns. Defaults to True.

        Returns:
            rich.progress.Progress: Rich progress bar instance.
        """
        file_download_columns = [
            rich.progress.DownloadColumn(),
            "•",
            rich.progress.TransferSpeedColumn(),
        ]
        generic_download_columns = [
            rich.progress.MofNCompleteColumn(table_column=rich.table.Column(width=7, justify="center")),
        ]

        return rich.progress.Progress(
            rich.progress.SpinnerColumn(style="progress.data.speed"),
            rich.progress.TextColumn("{task.description}", justify="left", table_column=rich.table.Column(width=40)),
            rich.progress.BarColumn(bar_width=None, finished_style="green"),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            *(file_download_columns if is_file else generic_download_columns),
            "•",
            rich.progress.TimeElapsedColumn(),
            *(["/", rich.progress.TimeRemainingColumn()] if is_file else []),
            transient=False,
            console=console,
        )


progress = CustomProgress()
