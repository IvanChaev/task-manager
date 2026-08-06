# -*- coding: utf-8 -*-
"""Настройка логирования: каждая сессия пишется в отдельный файл в logs/."""

import logging
import os
import sys
import traceback
from datetime import datetime

from tm.config import APP_TITLE, LOG_DIR, VERSION

_FMT = "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level=logging.INFO):
    os.makedirs(LOG_DIR, exist_ok=True)
    filename = os.path.join(
        LOG_DIR,
        "%s-%s.log" % (APP_TITLE.lower().replace(" ", "_"),
                       datetime.now().strftime("%Y%m%d_%H%M%S")),
    )
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    file_handler = logging.FileHandler(filename, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(_FMT, _DATEFMT))
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(_FMT, _DATEFMT))
    root.addHandler(console_handler)

    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        traceback.print_exception = lambda *a, **k: logging.getLogger().error(
            "".join(traceback.format_exception(*a, **k))
        ) if a else None
        _excepthook._hook = True
        logging.getLogger().error(
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        )

    sys.excepthook = _excepthook

    try:
        import tkinter
        _orig_report = tkinter.Tk.report_callback_exception

        def _report_callback_exception(exc, /):
            _orig_report(None, exc)
            logging.getLogger().error(
                "Exception in Tkinter callback\n%s",
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            )

        tkinter.Widget.report_callback_exception = _report_callback_exception
    except Exception:
        pass

    logging.info("=== Запуск %s v%s ===", APP_TITLE, VERSION)
    logging.info("Файл данных: будет передан TaskStore")
    logging.info("Файл лога: %s", filename)
    return filename
