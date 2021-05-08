import sys
import logging


def setup(log):
    # set up logger
    log_screen_handler = logging.StreamHandler(stream=sys.stdout)
    log.addHandler(log_screen_handler)
    log.propagate = False

    # add colored logs if colorama is availabe
    try:
        import colorama
        import copy

        LOG_COLORS = {
            logging.DEBUG: colorama.Fore.GREEN,
            logging.INFO: colorama.Fore.BLUE,
            logging.WARNING: colorama.Fore.YELLOW,
            logging.ERROR: colorama.Fore.RED,
            logging.CRITICAL: colorama.Back.RED,
        }

        class ColorFormatter(logging.Formatter):
            def format(self, record, *args, **kwargs):
                # if the corresponding logger has children, they may receive
                # modified record, so we want to keep it intact
                new_record = copy.copy(record)
                if new_record.levelno in LOG_COLORS:
                    new_record.levelname = (
                        "{color_begin}{level}{color_end}".format(
                            level=new_record.levelname,
                            color_begin=LOG_COLORS[new_record.levelno],
                            color_end=colorama.Style.RESET_ALL,
                        ))
                return super(ColorFormatter, self).format(
                    new_record, *args, **kwargs)

        log_screen_handler.setFormatter(
            ColorFormatter(
                fmt="%(asctime)s %(levelname)-8s %(message)s",
                datefmt="{color_begin}[%H:%M:%S]{color_end}".format(
                    color_begin=colorama.Style.DIM,
                    color_end=colorama.Style.RESET_ALL
                ),
            )
        )
    except ModuleNotFoundError:
        log_screen_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(message)s",
                datefmt="[%H:%M:%S]",
            )
        )
        pass

    return log


def get(name):
    log = logging.getLogger(name)
    if not log.handlers:
        setup(log)
    return log


def set_verbose(log, verbose):
    log.setLevel(logging.INFO if not verbose else logging.DEBUG)
