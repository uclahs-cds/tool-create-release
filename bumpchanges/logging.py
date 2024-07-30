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
        record.gha_prefix = self.prefixes[record.levelno]
        return True


def setup_logging() -> logging.Logger:
    "Set up logging to GitHub Actions and return the configured logger."
    # Does this need to be re-entrant like this?
    logger_name = "bumpchanges"

    if logging.getLevelName("NOTICE") == NOTICE:
        return logging.getLogger(logger_name)

    logging.addLevelName(NOTICE, "NOTICE")

    logging.setLoggerClass(NoticeLogger)

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.addFilter(GHAFilter())
    handler.setFormatter(logging.Formatter(
        "%(ghaprefix)s%(message)s",
        defaults={"ghaprefix": ""}
    ))

    root_logger = logging.getLogger(logger_name)
    root_logger.addHandler(handler)

    return root_logger
