# -*- coding: utf-8 -*-
"""Главное окно и логика приложения."""

import logging
import os
import subprocess
import sys
import time
import uuid

from tkinter import (
    Tk, Frame, Label, Entry, Button, StringVar, Menu, messagebox,
)
import tkinter as tk
from tkinter import font as tkfont
import tkinter.ttk as ttk

from tm.config import (
    ACCENT, APP_TITLE, BG, BORDER, CARD_BG, COLUMN_BG, DANGER, HOVER, MUTED,
    PID_FILE, PRIORITY_COLORS, PRIORITY_RANK, PRIORITIES, STATUS_COLORS,
    STATUSES, TEXT, VERSION,
)
from tm.store import TaskStore
from tm.widgets import BoardColumn, TagChip, TrashCan
from tm.utils import bind_shortcuts, tag_color, set_active_app

logger = logging.getLogger(__name__)


class TaskManager:
    """Главный контроллер приложения — окно с колонками и задачами."""

    def __init__(self, data_file):
        self.data_file = data_file
        self.selected_tags = set()
        self.filter_chips = []
        self._drag = None
        self._scroll_fraction = 0.0
        self._resize_job = None
        self._search_job = None

        self.root = Tk()
        self.root.title("%s %s" % (APP_TITLE, VERSION))
        self.root.geometry("1240x760")
        self.root.minsize(960, 560)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._apply_dark_theme()
        self._fonts()
        self.store = TaskStore(data_file)
        self.search_var = StringVar()
        self.priority_var = StringVar(value="Все")
        self._build_ui()
        self.refresh()

        self.root.bind("<Control-n>", lambda e: self.new_task())
        self.root.bind("<Control-N>", lambda e: self.new_task())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Control-F>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Configure>", self._on_resize)

        logger.info("TaskManager инициализирован (data_file=%s)", data_file)

        for w in self.root.winfo_children():
            bind_shortcuts(w)
        set_active_app(self)

    def _apply_dark_theme(self):
        self.root.option_add("*Entry.background", COLUMN_BG)
        self.root.option_add("*Entry.foreground", TEXT)
        self.root.option_add("*Entry.insertBackground", TEXT)
        self.root.option_add("*Entry.selectBackground", ACCENT)
        self.root.option_add("*Entry.selectForeground", "white")
        self.root.option_add("*Text.background", COLUMN_BG)
        self.root.option_add("*Text.foreground", TEXT)
        self.root.option_add("*Text.insertBackground", TEXT)
        self.root.option_add("*Text.selectBackground", ACCENT)
        self.root.option_add("*Text.selectForeground", "white")
        self.root.option_add("*Radiobutton.background", COLUMN_BG)
        self.root.option_add("*Radiobutton.foreground", TEXT)
        self.root.option_add("*Radiobutton.activeBackground", HOVER)
        self.root.option_add("*Radiobutton.activeForeground", TEXT)
        self.root.option_add("*Radiobutton.selectColor", CARD_BG)
        self.root.option_add("*Menu.background", CARD_BG)
        self.root.option_add("*Menu.foreground", TEXT)
        self.root.option_add("*Menu.activeBackground", ACCENT)
        self.root.option_add("*Menu.activeForeground", "white")
        self.root.option_add("*Listbox.background", COLUMN_BG)
        self.root.option_add("*Listbox.foreground", TEXT)
        self.root.option_add("*Listbox.selectBackground", ACCENT)
        self.root.option_add("*Listbox.selectForeground", "white")
        self.root.option_add("*TCombobox*Listbox.background", COLUMN_BG)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT,
                        fieldbackground=COLUMN_BG, bordercolor=BORDER,
                        arrowcolor=MUTED, lightcolor=BG, darkcolor=BG)
        style.map("TCombobox", fieldbackground=[("readonly", COLUMN_BG)],
                  foreground=[("readonly", TEXT)],
                  selectbackground=[("readonly", COLUMN_BG)],
                  selectforeground=[("readonly", TEXT)])
        style.map("TCombobox", background=[("readonly", COLUMN_BG)])
        style.map("Vertical.TScrollbar", background=[("", COLUMN_BG)],
                  troughcolor=[("", BG)], bordercolor=[("", BG)],
                  arrowcolor=[("", MUTED)], lightcolor=[("", COLUMN_BG)],
                  darkcolor=[("", COLUMN_BG)])

    def _fonts(self):
        family = "Segoe UI"
        self.font_title = tkfont.Font(family=family, size=14, weight="bold")
        self.font_done = tkfont.Font(family=family, size=14, overstrike=1)
        self.font_mid = tkfont.Font(family=family, size=12)
        self.font_small = tkfont.Font(family=family, size=11)
        self.font_tiny = tkfont.Font(family=family, size=10)
        self.font_tag = tkfont.Font(family=family, size=12)
        self.font_card_btn = tkfont.Font(family=family, size=13)

    def _build_ui(self):
        toolbar = Frame(self.root, bg=BG, padx=14, pady=12)
        toolbar.pack(fill="x")
        Button(toolbar, text="+ Новая задача", bg=ACCENT, fg="white",
               activebackground="#1d4ed8", activeforeground="white", font=self.font_small,
               padx=14, pady=4, cursor="hand2", relief="flat",
               command=self.new_task).pack(side="left")
        Label(toolbar, text="Поиск:", bg=BG, fg=MUTED, font=self.font_small).pack(side="left", padx=18)
        self.search_entry = Entry(toolbar, textvariable=self.search_var, width=24,
                                  relief="solid", bd=1, font=self.font_mid)
        self.search_entry.pack(side="left")
        Label(toolbar, text="Приоритет:", bg=BG, fg=MUTED, font=self.font_small).pack(side="left", padx=14)
        self.priority_combo = ttk.Combobox(toolbar, textvariable=self.priority_var,
                                           values=("Все",) + PRIORITIES, state="readonly", width=12)
        self.priority_combo.pack(side="left")
        self.priority_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        Button(toolbar, text="Очистить фильтры", bg=COLUMN_BG, fg=TEXT,
               activebackground=HOVER, font=self.font_small, padx=10, pady=3,
               cursor="hand2", relief="flat", command=self._clear_filters).pack(side="left", padx=10)
        Button(toolbar, text="🏷", bg=COLUMN_BG, fg=TEXT,
               activebackground=HOVER, font=self.font_small, padx=8, pady=3,
               cursor="hand2", relief="flat", command=self.manage_tags).pack(side="left", padx=4)
        Button(toolbar, text="Перезапуск", bg=COLUMN_BG, fg=TEXT,
               activebackground=HOVER, font=self.font_small, padx=10, pady=3,
               cursor="hand2", relief="flat", command=self.restart_app).pack(side="right")
        self.search_var.trace_add("write", self._on_search_change)

        self.tagbar = Frame(self.root, bg=BG, padx=14)
        self.tagbar.pack(fill="x", pady=4)

        board = Frame(self.root, bg=BG, padx=14)
        board.pack(fill="both", expand=True, pady=8)
        board.grid_rowconfigure(0, weight=1)
        for i in range(3):
            board.columnconfigure(i, weight=1, uniform="cols")
        self.columns = [BoardColumn(board, self, s) for s in STATUSES]
        for i, col in enumerate(self.columns):
            col.grid(row=0, column=i, sticky="nsew",
                     padx=(0 if i == 0 else 6, 0 if i == 2 else 6))

        statusbar = Frame(self.root, bg=COLUMN_BG)
        statusbar.pack(fill="x", side="bottom")
        self.status_lbl = Label(statusbar, text="", bg=COLUMN_BG, fg=MUTED,
                                font=self.font_small, padx=14, pady=4, anchor="w")
        self.status_lbl.pack(fill="x")

        self.trash_can = TrashCan(self.root, self)
        self.trash_can.place(relx=1.0, rely=1.0, x=-24, y=-38, anchor="se")
        self.trash_can.lift()

    def set_trash_active(self, active):
        if hasattr(self, "trash_can"):
            self.trash_can.set_active(active)

    def _rebuild_tagbar(self):
        tags = self.store.all_tags()
        tag_signature = (tuple(tags), tuple(sorted(self.selected_tags)))
        if hasattr(self, "_last_tag_signature") and self._last_tag_signature == tag_signature:
            return
        self._last_tag_signature = tag_signature

        for widget in self.tagbar.winfo_children():
            widget.destroy()
        self.filter_chips = []
        if not tags:
            return
        Label(self.tagbar, text="Теги:", bg=BG, fg=MUTED,
              font=self.font_small).pack(side="left", padx=8)
        for tag in tags:
            chip = TagChip(self.tagbar, tag, self._toggle_filter_chip,
                           self.font_small, active=tag in self.selected_tags)
            chip.pack(side="left", padx=5)
            self.filter_chips.append(chip)

    def _toggle_filter_chip(self, chip):
        if chip.text in self.selected_tags:
            self.selected_tags.discard(chip.text)
            chip.set_active(False)
        else:
            self.selected_tags.add(chip.text)
            chip.set_active(True)
        self.refresh()

    def _clear_filters(self):
        self.search_var.set("")
        self.priority_var.set("Все")
        self.selected_tags.clear()
        self.refresh()

    def manage_tags(self):
        from tm.dialog import TagManagerDialog
        logger.info("Открыт диалог управления тегами")
        dialog = TagManagerDialog(self)
        dialog.top.wait_window()
        if dialog.result:
            logger.info("Диалог тегов закрыт с сохранением")
            self.refresh()

    def _visible_tasks(self, status):
        query = self.search_var.get().strip().lower()
        priority = self.priority_var.get()
        result = []
        for task in self.store.tasks:
            if task["status"] != status:
                continue
            if priority != "Все" and task["priority"] != priority:
                continue
            if self.selected_tags and not self.selected_tags.issubset(set(task["tags"])):
                continue
            if query:
                haystack = " ".join((task["title"], task["description"],
                                     " ".join(task["tags"]))).lower()
                if query not in haystack:
                    continue
            result.append(task)
        return result

    def scroll_all(self, delta):
        max_scroll = 0
        for col in self.columns:
            box = col.canvas.bbox("all")
            if box is None:
                continue
            max_scroll = max(max_scroll, box[3] - col.canvas.winfo_height())
        if max_scroll <= 0:
            return
        step = 60
        self._scroll_fraction += (-delta / 120) * step / max_scroll
        self._scroll_fraction = max(0.0, min(1.0, self._scroll_fraction))
        for col in self.columns:
            col.canvas.yview_moveto(self._scroll_fraction)

    def refresh(self):
        width = max(220, (self.root.winfo_width() - 90) // 3 - 44)
        self.card_wrap = width
        self._rebuild_tagbar()
        self._scroll_fraction = 0.0
        for col in self.columns:
            col.render(self._visible_tasks(col.status))
        total = len(self.store.tasks)
        done = sum(1 for t in self.store.tasks if t["status"] == "Готово")
        percent = int(done / total * 100) if total else 0
        self.status_lbl.config(
            text="Всего: %d   Выполнено: %d (%d%%)   Файл: %s" % (
                total, done, percent, self.store.path))

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        if event.width <= 1:
            return
        width = max(220, (event.width - 90) // 3 - 44)
        if hasattr(self, "_last_width") and self._last_width == width:
            return
        self._last_width = width
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(100, self.refresh)

    def _on_search_change(self, *args):
        if self._search_job:
            self.root.after_cancel(self._search_job)
        self._search_job = self.root.after(150, self.refresh)

    def new_task(self, status=STATUSES[0]):
        from tm.dialog import TaskDialog
        logger.info("Создание новой задачи (status=%s)", status)
        dialog = TaskDialog(self, initial_status=status)
        dialog.top.wait_window()
        if not dialog.result:
            logger.info("Создание задачи отменено")
            return
        task = {"id": uuid.uuid4().hex, "created": time.time(), **dialog.result}
        self.store.tasks.append(task)
        self.store.save()
        self.refresh()
        logger.info("Создана задача «%s» (id=%s)", task["title"], task["id"])

    def edit_task(self, task):
        from tm.dialog import TaskDialog
        logger.info("Редактирование задачи «%s» (id=%s)", task["title"], task["id"])
        dialog = TaskDialog(self, task=task)
        dialog.top.wait_window()
        if not dialog.result:
            logger.info("Редактирование задачи отменено (id=%s)", task["id"])
            return
        task.update(dialog.result)
        self.store.save()
        self.refresh()
        logger.info("Задача «%s» (id=%s) обновлена", task["title"], task["id"])

    def delete_task(self, task):
        logger.info("Удаление задачи «%s» (id=%s)", task["title"], task["id"])
        self.store.tasks = [t for t in self.store.tasks if t["id"] != task["id"]]
        self.store.save()
        self.refresh()
        logger.info("Удалена задача (id=%s)", task["id"])
        return True

    def _column_at(self, x_root, y_root):
        widget = self.root.winfo_containing(x_root, y_root)
        while widget is not None:
            if isinstance(widget, BoardColumn):
                return widget
            widget = getattr(widget, "master", None)
        return None

    def set_status(self, task, status):
        if task["status"] == status:
            return
        logger.info("Смена статуса задачи «%s» (id=%s): %s → %s",
                    task["title"], task["id"], task["status"], status)
        task["status"] = status
        self.store.save()
        self.refresh()

    def reorder_task(self, task, target_status, target_index):
        old_status = task["status"]
        logger.info("Перемещение/переупорядочивание задачи «%s» (id=%s): статус %s -> %s, индекс %d",
                    task["title"], task["id"], old_status, target_status, target_index)
        
        self.store.tasks = [t for t in self.store.tasks if t["id"] != task["id"]]
        task["status"] = target_status

        other_tasks_of_status = [t for t in self.store.tasks if t["status"] == target_status]
        
        if target_index >= len(other_tasks_of_status):
            if other_tasks_of_status:
                last_task = other_tasks_of_status[-1]
                idx = self.store.tasks.index(last_task) + 1
                self.store.tasks.insert(idx, task)
            else:
                self.store.tasks.append(task)
        else:
            target_task = other_tasks_of_status[target_index]
            idx = self.store.tasks.index(target_task)
            self.store.tasks.insert(idx, task)

        self.store.save()
        self.refresh()

    def restart_app(self):
        logger.info("Перезапуск приложения (новая сессия)")
        self.store.save()
        
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass

        python = sys.executable
        if python.lower().endswith("python.exe"):
            pythonw = python[:-4] + "w.exe"
            if os.path.exists(pythonw):
                python = pythonw

        script_path = os.path.abspath(sys.argv[0])
        subprocess.Popen([python, script_path] + sys.argv[1:],
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        
        self.root.destroy()
        sys.exit(0)

    def _on_close(self):
        logger.info("Закрытие приложения — сохранение данных")
        self.store.save()
        self.root.destroy()

    def run(self):
        logger.info("Запуск главного цикла приложения")
        self.root.mainloop()
