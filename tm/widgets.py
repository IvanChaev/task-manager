# -*- coding: utf-8 -*-
"""GUI-виджеты: тег-чипс, карточка задачи, колонка доски."""

import logging
from datetime import date

from tkinter import (
    Frame, Label, Button, Canvas, Menu, Toplevel,
)

from tm.config import (
    ACCENT, BG, BORDER, CARD_BG, COLUMN_BG, DANGER, FONT_FAMILY, HOVER, MUTED,
    PRIORITY_COLORS, STATUS_COLORS, STATUSES, TEXT,
)
from tm.utils import format_due, tag_color, truncate

logger = logging.getLogger(__name__)


class ToolTip:
    """Всплывающая подсказка, показываемая при наведении курсора."""

    DELAY_MS = 400

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Motion>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        if self._after_id is None:
            self._after_id = self.widget.after(self.DELAY_MS, self._show)

    def _on_leave(self, event=None):
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        self._after_id = None
        if self.tip is not None or not self.widget.winfo_exists():
            return

        tip = Toplevel(self.widget)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)

        frame = Frame(tip, bg=BORDER)
        frame.pack(fill="both", expand=True)

        Label(
            frame,
            text=self.text,
            bg=CARD_BG,
            fg=TEXT,
            font=(FONT_FAMILY, 10),
            justify="left",
            anchor="w",
            padx=10,
            pady=8,
            wraplength=380,
        ).pack(fill="both", expand=True)

        tip.update_idletasks()

        margin = 8
        offset = 6
        req_w = tip.winfo_reqwidth()
        req_h = tip.winfo_reqheight()
        screen_w = self.widget.winfo_screenwidth()
        screen_h = self.widget.winfo_screenheight()

        x = self.widget.winfo_rootx()
        y_below = self.widget.winfo_rooty() + self.widget.winfo_height() + offset
        y_above = self.widget.winfo_rooty() - req_h - offset

        if y_below + req_h <= screen_h:
            y = y_below
        elif y_above >= 0:
            y = y_above
        else:
            y = max(margin, screen_h - req_h - margin)

        if x + req_w > screen_w:
            x = screen_w - req_w - margin
        if x < margin:
            x = margin

        tip.geometry("+%d+%d" % (int(x), int(y)))
        self.tip = tip

    def _hide(self):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class TagChip(Label):
    """Кликабельный индикатор тега."""

    def __init__(self, master, text, on_click, font, active=False, color=None):
        self.text = text
        self.color = color or tag_color(text)
        self.active = active
        self._on_click = on_click
        super().__init__(master, text=text, font=font, padx=8, pady=2, cursor="hand2")
        self._paint()
        self.bind("<Button-1>", lambda e: self._on_click(self))

    def _paint(self):
        self.configure(
            bg=self.color if self.active else COLUMN_BG,
            fg="white" if self.active else MUTED,
        )

    def set_active(self, active):
        self.active = active
        self._paint()


class TaskCard(Frame):
    """Карточка одной задачи на доске."""

    def __init__(self, master, app, task):
        super().__init__(master, bg=CARD_BG, bd=1, relief="solid",
                         highlightbackground=BORDER, highlightthickness=1)
        self.app = app
        self.task = task
        done = task["status"] == "Готово"

        Frame(self, bg=PRIORITY_COLORS[task["priority"]], width=5).pack(side="left", fill="y")

        btn_col = Frame(self, bg=CARD_BG)
        btn_col.pack(side="right", fill="y", padx=(2, 6), pady=6)

        self.btn_up = Button(btn_col, text="▲", font=app.font_tiny, bg=COLUMN_BG,
                             fg=MUTED, activebackground=HOVER, activeforeground=TEXT,
                             relief="flat", bd=0, padx=2, pady=0, cursor="hand2",
                             command=lambda: app.move_task(task, -1, self.btn_up))
        self.btn_up.pack(side="top", fill="x", pady=(0, 2))
        self.btn_down = Button(btn_col, text="▼", font=app.font_tiny, bg=COLUMN_BG,
                               fg=MUTED, activebackground=HOVER, activeforeground=TEXT,
                               relief="flat", bd=0, padx=2, pady=0, cursor="hand2",
                               command=lambda: app.move_task(task, 1, self.btn_down))
        self.btn_down.pack(side="top", fill="x")

        body = Frame(self, bg=CARD_BG)
        body.pack(side="left", fill="both", expand=True, padx=8, pady=6)

        title = Label(body, text=task["title"], font=app.font_done if done else app.font_title,
                      bg=CARD_BG, fg=MUTED if done else TEXT, anchor="w", justify="left",
                      wraplength=app.card_wrap)
        title.pack(fill="x")

        if task["description"]:
            Label(body, text=truncate(task["description"], 200), font=app.font_small,
                  bg=CARD_BG, fg=TEXT, anchor="w", justify="left", wraplength=app.card_wrap
                  ).pack(fill="x", pady=2)

        if task["tags"]:
            row = Frame(body, bg=CARD_BG)
            row.pack(fill="x", pady=5)
            for tag in task["tags"]:
                Label(row, text=tag, font=app.font_tag, bg=tag_color(tag), fg="white",
                      padx=6, pady=1).pack(side="left", padx=2)

        due = format_due(task["due"])
        if due:
            overdue = task["due"] < date.today().isoformat() and not done
            Label(body, text="Срок: " + due, font=app.font_tiny, bg=CARD_BG,
                  fg="#ef6e5a" if overdue else MUTED).pack(fill="x", pady=5)

        menu = Menu(self, tearoff=0)
        menu.add_command(label="Редактировать", command=lambda: app.edit_task(task))
        sub = Menu(menu, tearoff=0)
        for s in STATUSES:
            sub.add_command(label=s, command=lambda s=s: app.set_status(task, s))
        menu.add_cascade(label="Переместить в", menu=sub)
        menu.add_separator()
        menu.add_command(label="Удалить", command=lambda: app.delete_task(task))
        self._menu = menu

        self._right_click_timer = None

        def on_right_click(event):
            if self._right_click_timer is not None:
                self.after_cancel(self._right_click_timer)
                self._right_click_timer = None
                app.edit_task(task)
            else:
                x_root, y_root = event.x_root, event.y_root
                self._right_click_timer = self.after(
                    250, lambda: _trigger_menu(x_root, y_root)
                )

        def _trigger_menu(x_root, y_root):
            self._right_click_timer = None
            menu.tk_popup(x_root, y_root)
            menu.grab_release()

        for widget in (self, body, title):
            widget.bind("<Button-3>", on_right_click)
            widget.bind("<ButtonPress-1>", self._dnd_start)
            widget.bind("<ButtonRelease-1>", self._dnd_end)
            widget.bind("<B1-Motion>", self._dnd_move)
        for widget in body.winfo_children():
            widget.bind("<Button-3>", on_right_click)
            if not isinstance(widget, Button):
                widget.bind("<ButtonPress-1>", self._dnd_start)
                widget.bind("<ButtonRelease-1>", self._dnd_end)
                widget.bind("<B1-Motion>", self._dnd_move)

    def _dnd_start(self, event):
        if self.app._drag is not None:
            return
        self.app._drag = self
        self._dnd_index = self.master.pack_slaves().index(self)
        self.pack_forget()

        done = self.task["status"] == "Готово"
        ghost = Toplevel(self.app.root)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)

        outer = Frame(ghost, bg=ACCENT, bd=0)
        outer.pack(fill="both", expand=True)

        card_container = Frame(outer, bg=CARD_BG, bd=0)
        card_container.pack(fill="both", expand=True, padx=1, pady=1)

        Frame(card_container, bg=PRIORITY_COLORS[self.task["priority"]], width=5).pack(side="left", fill="y")
        gbody = Frame(card_container, bg=CARD_BG, padx=10, pady=8)
        gbody.pack(side="left", fill="both", expand=True)
        Label(gbody, text=self.task["title"], font=self.app.font_title,
              bg=CARD_BG, fg=MUTED if done else TEXT, anchor="w",
              wraplength=self.app.card_wrap).pack(fill="x")
        if self.task["description"]:
            Label(gbody, text=truncate(self.task["description"], 120),
                  font=self.app.font_small, bg=CARD_BG, fg=MUTED,
                  anchor="w", wraplength=self.app.card_wrap).pack(fill="x", pady=2)
        ghost.update_idletasks()
        self._ghost = ghost
        self._dnd_move(event)

    def _over_trash_point(self, x_root, y_root):
        if not hasattr(self.app, "trash_can") or not self.app.trash_can.winfo_exists():
            return False
        tc = self.app.trash_can
        x1 = tc.winfo_rootx()
        y1 = tc.winfo_rooty()
        x2 = x1 + tc.winfo_width()
        y2 = y1 + tc.winfo_height()
        return x1 <= x_root <= x2 and y1 <= y_root <= y2

    def _is_over_trash(self, event):
        return self._over_trash_point(event.x_root, event.y_root)

    def _dnd_move(self, event):
        drag = self.app._drag
        if drag is None:
            return
        ghost = getattr(drag, "_ghost", None)
        if ghost is None:
            return
        x = event.x_root - ghost.winfo_width() // 2
        y = event.y_root - ghost.winfo_height() // 2
        ghost.geometry(f"+{x}+{y}")
        self.app.set_trash_active(self._is_over_trash(event))

    def _dnd_end(self, event):
        drag = self.app._drag
        self.app._drag = None
        if drag is None:
            return
        self.app.set_trash_active(False)
        ghost = getattr(drag, "_ghost", None)
        if ghost is not None:
            ghost.destroy()
            drag._ghost = None
        drag.configure(highlightbackground=BORDER, highlightthickness=1)

        if self._is_over_trash(event):
            if not self.app.delete_task(drag.task):
                drag._restore()
        else:
            column = self.app._column_at_xy(event.x_root, event.y_root)
            if column is not None and column.status != drag.task["status"]:
                self.app.reorder_task(drag.task, column.status, len(self.app.store.tasks))
            else:
                drag._restore()

    def _restore(self):
        before = None
        slaves = self.master.pack_slaves()
        idx = getattr(self, "_dnd_index", len(slaves))
        if idx < len(slaves):
            before = slaves[idx]
        self.pack(fill="x", pady=10, before=before)


class BoardColumn(Frame):
    """Одна колонка-доска («К выполнению», «В процессе», «Готово»)."""

    def __init__(self, master, app, status):
        super().__init__(master, bg=BG)
        self.app = app
        self.status = status
        self.wrap = None
        self.cards = {}
        self._last_signatures = None
        self._last_card_wrap = None

        head = Frame(self, bg=BG)
        head.pack(fill="x", pady=8)
        Label(head, text="●", fg=STATUS_COLORS[status], bg=BG,
              font=app.font_small).pack(side="left")
        Label(head, text=status, font=app.font_title, bg=BG, fg=TEXT).pack(side="left", padx=6)
        self.count_lbl = Label(head, text="0", font=app.font_tiny, bg=BORDER,
                               fg=TEXT, padx=6, pady=1)
        self.count_lbl.pack(side="left", padx=8)

        wrap = Frame(self, bg=COLUMN_BG, bd=1, relief="solid", highlightthickness=0)
        wrap.pack(fill="both", expand=True)
        self.wrap = wrap
        self.canvas = Canvas(wrap, bg=COLUMN_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.inner = Frame(self.canvas, bg=COLUMN_BG)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind("<Double-Button-1>", lambda e: app.new_task(self.status))

        col_menu = Menu(self, tearoff=0)
        col_menu.add_command(label="Новая задача", command=lambda: app.new_task(status))
        self._col_menu = col_menu

        def on_column_right_click(event):
            col_menu.tk_popup(event.x_root, event.y_root)
            col_menu.grab_release()

        self.canvas.bind("<Button-3>", on_column_right_click)
        self.inner.bind("<Button-3>", on_column_right_click)
        wrap.bind("<Button-3>", on_column_right_click)

        self._bind_wheel(self.canvas)
        self._bind_wheel(self.inner)

    def _bind_wheel(self, widget):
        widget.bind("<MouseWheel>",
                    lambda e: self.app.scroll_all(e.delta))
        for child in widget.winfo_children():
            self._bind_wheel(child)

    def render(self, tasks):
        card_wrap = getattr(self.app, "card_wrap", None)
        new_ids = [t["id"] for t in tasks]
        task_states = {}
        for t in tasks:
            task_states[t["id"]] = (t["title"], t["description"], t["status"], t["priority"], tuple(t["tags"]), t["due"], card_wrap)

        if (getattr(self, "_last_ids", None) == new_ids and 
            getattr(self, "_last_card_wrap", None) == card_wrap and
            getattr(self, "_last_task_states", None) == task_states):
            return

        self._last_ids = new_ids
        self._last_card_wrap = card_wrap
        self._last_task_states = task_states

        self.count_lbl.config(text=str(len(tasks)))

        for widget in list(self.inner.winfo_children()):
            if isinstance(widget, Label) and widget.cget("text") == "Нет задач":
                widget.destroy()

        for tid in list(self.cards.keys()):
            if tid not in new_ids:
                self.cards[tid].destroy()
                del self.cards[tid]

        if not tasks:
            if not any(isinstance(w, Label) and w.cget("text") == "Нет задач" for w in self.inner.winfo_children()):
                lbl = Label(self.inner, text="Нет задач",
                            bg=COLUMN_BG, fg=MUTED, font=self.app.font_small)
                lbl.bind("<Button-3>", lambda e: self._col_menu.tk_popup(e.x_root, e.y_root))
                lbl.pack(pady=24)
        else:
            total = len(tasks)
            for i, task in enumerate(tasks):
                tid = task["id"]
                t_state = task_states[tid]

                if tid in self.cards:
                    card = self.cards[tid]
                    if getattr(card, "_state", None) != t_state:
                        card.destroy()
                        card = TaskCard(self.inner, self.app, task)
                        card._state = t_state
                        self.cards[tid] = card
                else:
                    card = TaskCard(self.inner, self.app, task)
                    card._state = t_state
                    self.cards[tid] = card

                card.pack_forget()
                card.pack(fill="x", pady=10)
                card._column = self
                card.btn_up.configure(state="disabled" if i == 0 else "normal")
                card.btn_down.configure(state="disabled" if i == total - 1 else "normal")
                self._bind_wheel(card)

        self.inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


class TrashCan(Frame):
    """Корзина для удаления задач перетаскиванием."""

    def __init__(self, master, app):
        super().__init__(master, bg=CARD_BG, bd=2, relief="solid",
                         highlightbackground=BORDER, highlightthickness=1,
                         padx=28, pady=20)
        self.app = app
        self.active = False

        self.lbl = Label(self, text="🗑", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, 24))
        self.lbl.pack()

        tip_text = (
            "Корзина — удаление задачи.\n"
            "Перетащите сюда карточку задачи левой кнопкой мыши, "
            "чтобы безвозвратно удалить её."
        )
        ToolTip(self, tip_text)

    def set_active(self, active):
        if self.active == active:
            return
        self.active = active
        if active:
            self.configure(bg="#dc2626", highlightbackground="#ef4444")
            self.lbl.configure(text="🗑", bg="#dc2626", fg="white", font=(FONT_FAMILY, 32))
        else:
            self.configure(bg=CARD_BG, highlightbackground=BORDER)
            self.lbl.configure(text="🗑", bg=CARD_BG, fg=MUTED, font=(FONT_FAMILY, 24))
