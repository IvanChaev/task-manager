# -*- coding: utf-8 -*-
"""Хранилище задач: загрузка, нормализация, сохранение в JSON."""

import json
import logging
import os
import time
import uuid
from tkinter import messagebox

from tm.config import APP_TITLE, PRIORITIES, STATUSES

logger = logging.getLogger(__name__)


class TaskStore:
    def __init__(self, path):
        self.path = path
        self.tasks = []
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            logger.info("Файл данных не найден: %s — стартуем с пустого списка", self.path)
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get("tasks", []) if isinstance(data, dict) else data
            for item in raw:
                if isinstance(item, dict) and item.get("title"):
                    self.tasks.append(self._normalize(item))
            logger.info("Загружено %d задач(а) из %s", len(self.tasks), self.path)
        except (OSError, ValueError) as exc:
            logger.exception("Ошибка чтения файла данных %s", self.path)
            backup = self.path + ".bak"
            try:
                os.replace(self.path, backup)
            except OSError:
                logger.warning("Не удалось создать бэкап %s", backup)
            messagebox.showwarning(
                APP_TITLE,
                "Не удалось прочитать файл данных:\n%s\n\n"
                "Файл сохранён как %s.\nНачинаем с пустого списка." % (exc, backup),
            )

    @staticmethod
    def _normalize(item):
        tags = [str(x).strip() for x in (item.get("tags") or []) if str(x).strip()]
        return {
            "id": str(item.get("id") or uuid.uuid4().hex),
            "title": str(item.get("title", "")),
            "description": str(item.get("description", "")),
            "priority": item.get("priority") if item.get("priority") in PRIORITIES else "Средний",
            "tags": tags,
            "status": item.get("status") if item.get("status") in STATUSES else STATUSES[0],
            "due": item.get("due") if isinstance(item.get("due"), str) else "",
            "created": float(item.get("created", time.time())),
        }

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "tasks": self.tasks}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
        logger.info("Сохранено %d задач(а) в %s", len(self.tasks), self.path)

    def all_tags(self):
        tags, seen = [], set()
        for task in self.tasks:
            for tag in task["tags"]:
                if tag not in seen:
                    seen.add(tag)
                    tags.append(tag)
        return tags