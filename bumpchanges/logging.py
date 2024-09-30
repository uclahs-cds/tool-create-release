"""Module to handle logging to GitHub Actions."""

import logging


NOTICE = 25


class GHAFilter(logging.Filter):
    """A logging filter that plays nice with GitHub Actions output."""

    # pylint: disable=too-few-public-methods

    prefixes = {
        logging.DEBUG: "::debug::",
        logging.INFO: "",
        NOTICE: "::notice::",
        logging.WARNING: "::warning::",
        logging.ERROR: "::error::",
        logging.CRITICAL: "::error::",
    }

    def filter(self, record):
        record.ghaprefix = self.prefixes[record.levelno]
        return True


def setup_logging():
    """Set up logging to GitHub Actions.logger."""
    # Does this need to be re-entrant like this?
    if logging.getLevelName("NOTICE") == NOTICE:
        return

    logging.addLevelName(NOTICE, "NOTICE")

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(ghaprefix)s%(message)s"))
    handler.addFilter(GHAFilter())

    # Set these handlers on the root logger of this module
    root_logger = logging.getLogger(__name__.rpartition(".")[0])
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)


class LoggingMixin:
    """A mixin class for logging."""

    # pylint: disable=too-few-public-methods

    @property
    def logger(self) -> logging.Logger:
        """Create and return a logger for instance or class."""
        if not hasattr(self, "_logger") or not self._logger:
            self._logger = logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._logger
