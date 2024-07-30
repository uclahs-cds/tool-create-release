"Module to handle logging to GitHub Actions."

import logging


NOTICE = 25


class NoticeLogger(logging.getLoggerClass()):
    "A logger subclass that has an additional NOTICE level."

    def notice(self, msg, *args, **kwargs):
        "Log the message at NOTICE level."
        self.log(NOTICE, msg, *args, **kwargs)


class GHAFilter(logging.Filter):
    "A logging filter that plays nice with GitHub Actions output."

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
    "Set up logging to GitHub Actions.logger."
    # Does this need to be re-entrant like this?
    if logging.getLevelName("NOTICE") == NOTICE:
        return

    logging.addLevelName(NOTICE, "NOTICE")

    logging.setLoggerClass(NoticeLogger)

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(ghaprefix)s%(message)s"))
    handler.addFilter(GHAFilter())

    # Set these handlers on the root logger of this module
    root_logger = logging.getLogger(__name__.rpartition(".")[0])
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
