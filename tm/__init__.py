# -*- coding: utf-8 -*-
"""Task Manager v2.0 — пакет с логикой приложения.

Разбит на модули:
  config  — константы, версия, палитра
  logger  — настройка логирования в папку logs/
  utils   — вспомогательные функции (цвета тегов, даты, truncate)
  store   — TaskStore: загрузка / сохранение задач в JSON
  widgets — TagChip, TaskCard, BoardColumn
  dialog  — TaskDialog: окно создания / редактирования задачи
  app     — TaskManager: главное окно и логика приложения
"""

from tm.config import VERSION
from tm.logger import setup_logging
from tm.store import TaskStore
from tm.app import TaskManager

__version__ = VERSION
__all__ = [
    "VERSION",
    "setup_logging",
    "TaskStore",
    "TaskManager",
]
