# -*- coding: utf-8 -*-
"""Диалог создания / редактирования задачи."""

import logging
from tkinter import (
    Toplevel, Frame, Label, Entry, Button, Text, Radiobutton, StringVar, messagebox,
)
from tkinter import simpledialog
import tkinter as tk

from tkinter import font as tkfont
import tkinter.ttk as ttk

from tm.config import (
    ACCENT, BG, COLUMN_BG, DANGER, HOVER, MUTED, PRIORITY_COLORS,
    PRIORITIES, STATUSES, TEXT,
)
from tm.utils import bind_shortcuts, format_due, parse_due
from tm.widgets import TagChip

logger = logging.getLogger(__name__)


class TaskDialog:
    """Модальное окно создания или редактирования задачи."""

    def __init__(self, app, task=None, initial_status=None):
        self.app = app
        self.result = None
        self.tag_chips = []
        self.editing = task is not None

        top = Toplevel(app.root)
        self.top = top
        top._dialog_controller = self
        top.title("Редактирование задачи" if task else "Новая задача")
        top.configure(bg=BG)
        top.resizable(False, False)
        top.transient(app.root)
        app.register_modal(top)

        body = Frame(top, bg=BG, padx=16, pady=14)
        body.pack(fill="both", expand=True)

        def field_label(text):
            Label(body, text=text, bg=BG, fg=TEXT,
                  font=app.font_small, anchor="w").pack(fill="x", pady=6)

        field_label("Название")
        self.title_text = Text(body, width=58, height=5, wrap="word",
                               font=app.font_mid, relief="solid", bd=1)
        self.title_text.pack(fill="x")
        if task and task["title"]:
            self.title_text.insert("1.0", task["title"])
        self.title_text.bind("<Return>", lambda e: (self._save(), "break")[1])

        field_label("Описание")
        self.desc_text = Text(body, width=58, height=5, wrap="word",
                               font=app.font_mid, relief="solid", bd=1)
        self.desc_text.pack(fill="x")
        if task and task["description"]:
            self.desc_text.insert("1.0", task["description"])

        def _insert_newline(event):
            event.widget.insert(tk.INSERT, "\n")
            return "break"

        for w_txt in (self.title_text, self.desc_text):
            w_txt.bind("<Control-Return>", _insert_newline)
            w_txt.bind("<Control-KP_Enter>", _insert_newline)
            w_txt.bind("<Shift-Return>", _insert_newline)
            w_txt.bind("<Shift-KP_Enter>", _insert_newline)

        field_label("Приоритет")
        prio = Frame(body, bg=BG)
        prio.pack(fill="x")
        self.priority_var = StringVar(value=task["priority"] if task else "Средний")
        for i, p in enumerate(PRIORITIES):
            Radiobutton(prio, text=p, value=p, variable=self.priority_var, indicatoron=False,
                        bg=COLUMN_BG, selectcolor=PRIORITY_COLORS[p], activebackground=HOVER,
                        fg=TEXT, font=app.font_small, padx=10).grid(row=0, column=i, padx=(0, 6))

        row = Frame(body, bg=BG)
        row.pack(fill="x", pady=8)
        Label(row, text="Статус", bg=BG, fg=TEXT, font=app.font_small).pack(side="left")
        self.status_var = StringVar(value=task["status"] if task else (initial_status or STATUSES[0]))
        ttk.Combobox(row, textvariable=self.status_var, values=list(STATUSES),
                     state="readonly", width=16).pack(side="left", padx=10)
        Label(row, text="Срок (ДД.ММ.ГГГГ)", bg=BG, fg=TEXT,
              font=app.font_small).pack(side="left", padx=18)
        self.due_var = StringVar(value=format_due(task["due"]) if task and task["due"] else "")
        Entry(row, textvariable=self.due_var, width=14, font=app.font_mid).pack(side="left", padx=6)

        field_label("Теги (через запятую или кликом по готовым)")
        self.tag_entry = Entry(body, width=58, font=app.font_mid)
        self.tag_entry.pack(fill="x")
        if task and task["tags"]:
            self.tag_entry.insert(0, ", ".join(task["tags"]))

        chips = Frame(body, bg=BG)
        chips.pack(fill="x", pady=6)
        existing = task["tags"] if task else []
        all_tags = app.store.all_tags()

        if all_tags:
            top.update_idletasks()
            avail_width = max(self.tag_entry.winfo_reqwidth(), 520)

            spacing = 6
            tag_widths = {}
            for tag in all_tags:
                is_active = tag in existing
                dummy = TagChip(chips, tag, lambda e: None, app.font_small, active=is_active)
                tag_widths[tag] = dummy.winfo_reqwidth()
                dummy.destroy()

            remaining = list(all_tags)
            rows = []

            while remaining:
                current_row = []
                current_width = 0
                next_remaining = []

                for tag in remaining:
                    w = tag_widths[tag]
                    item_width = w + spacing if current_row else w
                    if current_width + item_width <= avail_width:
                        current_row.append(tag)
                        current_width += item_width
                    else:
                        next_remaining.append(tag)

                if current_row:
                    still_next = []
                    for tag in next_remaining:
                        w = tag_widths[tag]
                        item_width = w + spacing if current_row else w
                        if current_width + item_width <= avail_width:
                            current_row.append(tag)
                            current_width += item_width
                        else:
                            still_next.append(tag)
                    next_remaining = still_next

                if not current_row:
                    current_row.append(remaining[0])
                    next_remaining = remaining[1:]

                rows.append(current_row)
                remaining = next_remaining

            for row_items in rows:
                row_frame = Frame(chips, bg=BG)
                row_frame.pack(anchor="w", fill="x", pady=2)
                for tag in row_items:
                    is_active = tag in existing
                    chip = TagChip(row_frame, tag, self._toggle_chip, app.font_small, active=is_active)
                    chip.pack(side="left", padx=(0, spacing), pady=2)
                    self.tag_chips.append(chip)

        buttons = Frame(body, bg=BG)
        buttons.pack(fill="x", pady=16)
        Button(buttons, text="Сохранить", bg=ACCENT, fg="white", activebackground="#1d4ed8",
               activeforeground="white", font=app.font_small, padx=18, pady=4,
               cursor="hand2", relief="flat", command=self._save).pack(side="right")
        Button(buttons, text="Отмена", bg=COLUMN_BG, fg=TEXT, activebackground=HOVER,
               font=app.font_small, padx=14, pady=4, cursor="hand2", relief="flat",
               command=top.destroy).pack(side="right", padx=8)

        top.bind("<Escape>", lambda e: top.destroy())
        top.bind("<Return>", lambda e: self._save())
        top.bind("<Control-s>", lambda e: self._save())
        top.bind("<Control-S>", lambda e: self._save())
        self._center()
        bind_shortcuts(top)
        top.grab_set()
        top.focus_force()
        self.title_text.focus_set()

    def _center(self):
        self.top.update_idletasks()
        w = self.top.winfo_reqwidth()
        h = self.top.winfo_reqheight()
        x = self.app.root.winfo_rootx() + (self.app.root.winfo_width() - w) // 2
        y = self.app.root.winfo_rooty() + (self.app.root.winfo_height() - h) // 3
        self.top.geometry("+%d+%d" % (max(x, 0), max(y, 0)))

    def _toggle_chip(self, chip):
        current = [t.strip() for t in self.tag_entry.get().split(",") if t.strip()]
        if chip.text in current:
            current.remove(chip.text)
            chip.set_active(False)
        else:
            current.append(chip.text)
            chip.set_active(True)
        self.tag_entry.delete(0, "end")
        self.tag_entry.insert(0, ", ".join(current))
        self.tag_entry.icursor("end")

    def _save(self):
        title = self.title_text.get("1.0", "end").strip()
        if not title:
            messagebox.showerror("Ошибка", "Название задачи не может быть пустым", parent=self.top)
            return
        due = ""
        if self.due_var.get().strip():
            try:
                due = parse_due(self.due_var.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат срока. Пример: 31.12.2026",
                                     parent=self.top)
                return
        tags = []
        for tag in self.tag_entry.get().split(","):
            tag = tag.strip()
            if tag and tag not in tags:
                tags.append(tag)
        self.result = {
            "title": title,
            "description": self.desc_text.get("1.0", "end").strip(),
            "priority": self.priority_var.get(),
            "status": self.status_var.get(),
            "tags": tags,
            "due": due,
        }
        logger.info("Диалог: %s задачу «%s»",
                    "отредактирована" if self.editing else "создана", title)
        self.top.destroy()


class TagManagerDialog:
    """Диалог управления тегами: создание, переименовка, удаление."""

    def __init__(self, app):
        self.app = app
        self.result = None
        self.selected = None

        top = Toplevel(app.root)
        self.top = top
        top._dialog_controller = self
        top.title("Управление тегами")
        top.configure(bg=BG)
        top.resizable(False, False)
        top.transient(app.root)
        app.register_modal(top)
        top.geometry("550x520")

        body = Frame(top, bg=BG, padx=14, pady=12)
        body.pack(fill="both", expand=True)

        Label(body, text="Теги:", bg=BG, fg=MUTED,
              font=app.font_small, anchor="w").pack(fill="x", pady=(0, 6))

        self._lb_frame = Frame(body, bg=BG)
        self._lb_frame.pack(fill="both", expand=True)

        self.tag_listbox = tk.Listbox(
            self._lb_frame,
            font=app.font_mid, bg=COLUMN_BG, fg=TEXT,
            selectbackground=ACCENT, selectforeground="white",
            relief="solid", bd=1,
        )
        self.tag_listbox.pack(side="left", fill="both", expand=True)
        self.tag_listbox.bind("<<ListboxSelect>>", self._on_select)

        scrollbar = ttk.Scrollbar(self._lb_frame, orient="vertical",
                                  command=self.tag_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.tag_listbox.configure(yscrollcommand=scrollbar.set)

        _populate = app.store.all_tags()
        for tag in _populate:
            self.tag_listbox.insert("end", tag)
        logger.info("Теги в списке: %d", len(_populate))

        Label(body, text="Новый тег:", bg=BG, fg=MUTED,
              font=app.font_small, anchor="w").pack(fill="x", pady=(14, 4))
        self.new_var = StringVar()
        self.new_entry = Entry(body, textvariable=self.new_var, width=40, font=app.font_mid)
        self.new_entry.pack(fill="x", pady=2)
        self.new_entry.bind("<Return>", self._add_new)

        buttons = Frame(body, bg=BG)
        buttons.pack(fill="x", pady=16)
        btn_rename = Button(buttons, text="Переименовать", bg=COLUMN_BG, fg=TEXT,
                            activebackground=HOVER, font=app.font_small,
                            padx=12, pady=3, cursor="hand2", relief="flat",
                            command=self._rename_selected, state="disabled")
        btn_rename.pack(side="left", padx=4)
        self.btn_rename = btn_rename
        btn_del = Button(buttons, text="Удалить", bg="#3d1f26", fg=DANGER,
                         activebackground="#522b34", font=app.font_small,
                         padx=12, pady=3, cursor="hand2", relief="flat",
                         command=self._delete_selected, state="disabled")
        btn_del.pack(side="left", padx=4)
        self.btn_delete = btn_del
        Button(buttons, text="Сохранить", bg=ACCENT, fg="white",
               activebackground="#1d4ed8", activeforeground="white",
               font=app.font_small, padx=18, pady=4,
               cursor="hand2", relief="flat", command=self._save).pack(side="right")
        Button(buttons, text="Отмена", bg=COLUMN_BG, fg=TEXT,
               activebackground=HOVER, font=app.font_small,
               padx=14, pady=4, cursor="hand2", relief="flat",
               command=top.destroy).pack(side="right", padx=8)

        top.bind("<Escape>", lambda e: top.destroy())
        top.bind("<Control-s>", lambda e: self._save())
        top.bind("<Control-S>", lambda e: self._save())
        self._center()
        bind_shortcuts(top)
        top.grab_set()
        top.focus_force()

    def _center(self):
        self.top.update_idletasks()
        w = self.top.winfo_reqwidth()
        h = self.top.winfo_reqheight()
        x = self.app.root.winfo_rootx() + (self.app.root.winfo_width() - w) // 2
        y = self.app.root.winfo_rooty() + (self.app.root.winfo_height() - h) // 3
        self.top.geometry("+%d+%d" % (max(x, 0), max(y, 0)))

    def _on_select(self, event=None):
        indices = self.tag_listbox.curselection()
        if indices:
            self.selected = self.tag_listbox.get(indices[0])
            self.btn_rename.configure(state="normal")
            self.btn_delete.configure(state="normal")
        else:
            self.selected = None
            self.btn_rename.configure(state="disabled")
            self.btn_delete.configure(state="disabled")

    def _add_new(self, event=None):
        name = self.new_var.get().strip()
        if not name:
            return
        existing = list(self.tag_listbox.get(0, "end"))
        if name in existing:
            messagebox.showwarning("Ошибка", "Тег «%s» уже существует" % name, parent=self.top)
            self.new_entry.focus_set()
            return
        self.tag_listbox.insert("end", name)
        self.tag_listbox.selection_clear(0, "end")
        self.tag_listbox.selection_set(self.tag_listbox.size() - 1)
        self.tag_listbox.see(self.tag_listbox.size() - 1)
        self._on_select()
        self.new_var.set("")
        self.new_entry.focus_set()
        logger.info("Добавлен новый тег: «%s»", name)

    def _rename_selected(self):
        if self.selected is None:
            return
        old = self.selected
        new = simpledialog.askstring(
            "Переименовать тег", "Новое имя для «%s»:" % old,
            parent=self.top)
        if not new:
            return
        new = new.strip()
        if not new:
            return
        if new == old:
            return
        existing = list(self.tag_listbox.get(0, "end"))
        if new in existing:
            messagebox.showwarning("Ошибка", "Тег «%s» уже существует" % new, parent=self.top)
            return
        idx = self.tag_listbox.index(self.tag_listbox.curselection()[0])
        self.tag_listbox.delete(idx)
        self.tag_listbox.insert(idx, new)
        self.tag_listbox.selection_clear(0, "end")
        self.tag_listbox.selection_set(idx)
        self.selected = new
        logger.info("Переименован тег: «%s» → «%s»", old, new)

    def _delete_selected(self):
        if self.selected is None:
            return
        name = self.selected
        idx = self.tag_listbox.index(self.tag_listbox.curselection()[0])
        self.tag_listbox.delete(idx)
        self._on_select()
        if self.tag_listbox.size() == 0:
            self.selected = None
            self.btn_rename.configure(state="disabled")
            self.btn_delete.configure(state="disabled")
        logger.info("Удалён тег: «%s»", name)

    def _save(self):
        old_tags = list(self.tag_listbox.get(0, "end"))
        self._apply_changes(old_tags)
        self.result = True
        self.top.destroy()

    def _apply_changes(self, new_tags):
        old_tags = set(self.app.store.all_tags())
        for task in self.app.store.tasks:
            task["tags"] = [t for t in task["tags"] if t in new_tags]
        self.app.store.save()
        self.app.refresh()
        deleted = old_tags - set(new_tags)
        logger.info("Управление тегами: итого %d тегов, удалено %d",
                    len(new_tags), len(deleted))
