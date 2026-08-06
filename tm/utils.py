# -*- coding: utf-8 -*-
"""Утилиты: цвета, даты, обрезка текста, горячие клавиши."""

import logging
import tkinter as tk
import tkinter.ttk as ttk
from datetime import date, datetime

from tm.config import TAG_PALETTE

logger = logging.getLogger(__name__)


def tag_color(tag):
    return TAG_PALETTE[sum(ord(ch) for ch in tag) % len(TAG_PALETTE)]


def _copy(event):
    try:
        if isinstance(event.widget, tk.Text):
            text = event.widget.get("sel.first", "sel.last")
        elif isinstance(event.widget, (tk.Entry, ttk.Entry)):
            if event.widget.selection_present():
                i1 = event.widget.index("sel.first")
                i2 = event.widget.index("sel.last")
                text = event.widget.get()[i1:i2]
            else:
                text = ""
        else:
            text = ""
        if text:
            event.widget.clipboard_clear()
            event.widget.clipboard_append(text)
            event.widget.update()
    except tk.TclError:
        pass
    return "break"


def _cut(event):
    try:
        if isinstance(event.widget, tk.Text):
            text = event.widget.get("sel.first", "sel.last")
            event.widget.delete("sel.first", "sel.last")
        elif isinstance(event.widget, (tk.Entry, ttk.Entry)):
            if event.widget.selection_present():
                i1 = event.widget.index("sel.first")
                i2 = event.widget.index("sel.last")
                text = event.widget.get()[i1:i2]
                event.widget.delete(i1, i2)
            else:
                text = ""
        else:
            text = ""
        if text:
            event.widget.clipboard_clear()
            event.widget.clipboard_append(text)
            event.widget.update()
    except tk.TclError:
        pass
    return "break"


def _paste(event):
    try:
        try:
            clip = event.widget.clipboard_get()
        except tk.TclError:
            clip = ""
        if clip:
            if isinstance(event.widget, tk.Text):
                try:
                    event.widget.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                event.widget.insert(tk.INSERT, clip)
            elif isinstance(event.widget, (tk.Entry, ttk.Entry)):
                try:
                    if event.widget.selection_present():
                        i1 = event.widget.index("sel.first")
                        i2 = event.widget.index("sel.last")
                        event.widget.delete(i1, i2)
                except tk.TclError:
                    pass
                event.widget.insert(tk.INSERT, clip)
    except tk.TclError:
        pass
    return "break"


def _select_all_text(event):
    event.widget.tag_add(tk.SEL, "1.0", tk.END)
    event.widget.mark_set(tk.INSERT, "1.0")
    event.widget.see(tk.INSERT)
    return "break"


def _select_all_entry(event):
    event.widget.select_range(0, tk.END)
    event.widget.icursor(tk.END)
    return "break"


def _undo(event):
    try:
        event.widget.edit_undo()
    except tk.TclError:
        pass
    return "break"


def _redo(event):
    try:
        event.widget.edit_redo()
    except tk.TclError:
        pass
    return "break"


_active_app = None


def set_active_app(app):
    global _active_app
    _active_app = app


def handle_control_key(event):
    widget = event.widget.focus_get() or event.widget
    keysym = getattr(event, "keysym", "").lower()
    char = getattr(event, "char", "").lower()
    keycode = getattr(event, "keycode", 0)

    is_c = keysym in ("c", "с") or char in ("c", "с") or keycode == 67
    is_v = keysym in ("v", "м") or char in ("v", "м") or keycode == 86
    is_x = keysym in ("x", "ч") or char in ("x", "ч") or keycode == 88
    is_a = keysym in ("a", "ф") or char in ("a", "ф") or keycode == 65
    is_z = keysym in ("z", "я") or char in ("z", "я") or keycode == 90
    is_y = keysym in ("y", "н") or char in ("y", "н") or keycode == 89

    is_n = keysym in ("n", "т") or char in ("n", "т") or keycode == 78
    is_f = keysym in ("f", "а") or char in ("f", "а") or keycode == 70
    is_s = keysym in ("s", "ы") or char in ("s", "ы") or keycode == 83

    if is_c:
        _copy(event)
        return "break"
    elif is_v:
        _paste(event)
        return "break"
    elif is_x:
        _cut(event)
        return "break"
    elif is_a:
        if isinstance(widget, tk.Text):
            _select_all_text(event)
        elif isinstance(widget, (tk.Entry, ttk.Entry)):
            _select_all_entry(event)
        return "break"
    elif is_z:
        _undo(event)
        return "break"
    elif is_y:
        _redo(event)
        return "break"
    elif is_n:
        if _active_app and hasattr(_active_app, "new_task"):
            _active_app.new_task()
            return "break"
    elif is_f:
        if _active_app and hasattr(_active_app, "search_entry"):
            _active_app.search_entry.focus_set()
            return "break"
    elif is_s:
        try:
            top = widget.winfo_toplevel()
            if hasattr(top, "_dialog_controller") and hasattr(top._dialog_controller, "_save"):
                top._dialog_controller._save()
                return "break"
        except Exception:
            pass


def bind_shortcuts(widget):
    """Глобально привязывает горячие клавиши с Ctrl."""
    try:
        root = widget._root()
        if not getattr(root, "_ctrl_shortcuts_bound", False):
            root.bind_all("<Control-KeyPress>", handle_control_key)
            root._ctrl_shortcuts_bound = True
    except Exception:
        pass


def parse_due(value):
    value = (value or "").strip()
    if not value:
        return ""
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError("bad date")


def format_due(iso):
    if not iso:
        return ""
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except ValueError:
        return iso


def truncate(text, limit):
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"