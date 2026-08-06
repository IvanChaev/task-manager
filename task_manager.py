#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task Manager — лёгкий десктопный таск-менеджер.

Точка входа: настраивает логирование и запускает приложение.
Логика вынесена в пакет ``tm``:

  tm.config  — константы, версия, палитра
  tm.logger  — логирование в папку logs/
  tm.utils   — утилиты (цвета тегов, даты, truncate)
  tm.store   — TaskStore: загрузка / сохранение задач
  tm.widgets — TagChip, TaskCard, BoardColumn
  tm.dialog  — TaskDialog: окно создания / редактирования задачи
  tm.app     — TaskManager: главное окно и логика приложения
"""

import argparse
import logging
import os
import sys
import atexit
import subprocess

from tm.config import APP_TITLE, DATA_FILE, VERSION, PID_FILE
from tm.logger import setup_logging
from tm.app import TaskManager


def is_python_process_running(pid):
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, OSError):
        return False

    try:
        output = subprocess.check_output(
            f'tasklist /fi "PID eq {pid}" /fo csv /nh',
            shell=True, text=True, errors="ignore"
        )
        if "python" in output.lower():
            return True
    except Exception:
        pass
    return False


def terminate_process(pid):
    try:
        subprocess.run(f'taskkill /f /pid {pid}', shell=True, capture_output=True)
    except Exception:
        try:
            os.kill(pid, 9)
        except Exception:
            pass


def check_and_write_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                old_pid = int(f.read().strip())
            
            if is_python_process_running(old_pid):
                logging.info("Найден запущенный процесс Python/Pythonw с PID=%s. Завершаем его...", old_pid)
                terminate_process(old_pid)
            else:
                logging.info("Процесс с PID=%s не найден или не является Python-процессом", old_pid)
        except Exception:
            logging.exception("Ошибка при проверке старого PID")

    current_pid = os.getpid()
    try:
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(current_pid))
        logging.info("Записан текущий PID=%s", current_pid)
    except Exception:
        logging.exception("Не удалось записать PID-файл")


def remove_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(PID_FILE)
                logging.info("PID-файл удален")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="%s %s — карточки задач, теги, приоритеты." % (APP_TITLE, VERSION))
    parser.add_argument(
        "--data", default=DATA_FILE,
        help="путь к JSON-файлу данных (по умолчанию tasks.json рядом со скриптом)")
    args = parser.parse_args()

    log_file = setup_logging()
    logging.info("Запуск с data_file=%s", args.data)

    check_and_write_pid()
    atexit.register(remove_pid)

    try:
        TaskManager(args.data).run()
    except Exception:
        logging.exception("Непойманное исключение в главном цикле")
        raise
    finally:
        remove_pid()


if __name__ == "__main__":
    main()
