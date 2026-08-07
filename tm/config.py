# -*- coding: utf-8 -*-
"""Константы приложения: названия, версия, палитра, стили."""

import os
import sys

APP_TITLE = "Task Manager"
VERSION = "1.2"

if sys.platform == "win32":
    FONT_FAMILY = "Segoe UI"
elif sys.platform == "darwin":
    FONT_FAMILY = "Helvetica"
else:
    FONT_FAMILY = "DejaVu Sans"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "tasks.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
PID_FILE = os.path.join(BASE_DIR, "task_manager.pid")

STATUSES = ("К выполнению", "В процессе", "Готово")
PRIORITIES = ("Высокий", "Средний", "Низкий")
PRIORITY_RANK = {"Высокий": 0, "Средний": 1, "Низкий": 2}
PRIORITY_COLORS = {"Высокий": "#ef5350", "Средний": "#f3a04c", "Низкий": "#2ebd7f"}
STATUS_COLORS = {"К выполнению": "#a0a8ba", "В процессе": "#5595ff", "Готово": "#5eead4"}
TAG_PALETTE = ("#4f9df5", "#7c6cf2", "#ef7a5a", "#3fd0a4", "#f355a7",
               "#22c9cf", "#ef5350", "#3fb8ad", "#b17be0", "#f3c04d")

BG = "#141422"
COLUMN_BG = "#1f1f33"
CARD_BG = "#2a2a40"
BORDER = "#3a3a58"
HOVER = "#34344e"
TEXT = "#e7e7f2"
MUTED = "#a3a3bd"
ACCENT = "#4f9df5"
DANGER = "#f87171"