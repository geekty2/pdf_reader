import tkinter as tk  # Для simpledialog та messagebox
from tkinter import simpledialog, messagebox


class BookmarkManager:
    def __init__(self, app_ref):
        self.app = app_ref  # Посилання на головний додаток для доступу до GUI та стану
        self.bookmarks = {}

    def add_bookmark(self):
        if not self.app.pdf_handler.pdf_document: return
        bookmark_name = simpledialog.askstring(
            "Додати закладку",
            "Введіть назву теми/питання:",
            parent=self.app.master
        )
        if bookmark_name and bookmark_name.strip():
            self.bookmarks[bookmark_name.strip()] = self.app.current_page_num
            self.app.ui_manager.update_bookmark_combo_list(self.bookmarks)  # Оновлюємо UI через ui_manager
            self.app.ui_manager.bookmark_combo.set(bookmark_name.strip())
            self.app.ui_manager.btn_remove_bookmark.config(state=tk.NORMAL)
        elif bookmark_name is not None:
            messagebox.showwarning(
                "Помилка",
                "Назва закладки не може бути порожньою.",
                parent=self.app.master
            )

    def remove_bookmark(self):
        selected_bookmark = self.app.ui_manager.bookmark_combo.get()
        if selected_bookmark and selected_bookmark in self.bookmarks:
            if messagebox.askyesno(
                    "Видалити закладку",
                    f"Видалити закладку '{selected_bookmark}'?",
                    parent=self.app.master
            ):
                del self.bookmarks[selected_bookmark]
                self.app.ui_manager.update_bookmark_combo_list(self.bookmarks)
                self.app.ui_manager.bookmark_combo.set('')
                if not self.bookmarks:
                    self.app.ui_manager.btn_remove_bookmark.config(state=tk.DISABLED)
        elif selected_bookmark:
            messagebox.showwarning(
                "Помилка",
                "Закладка не знайдена для видалення.",
                parent=self.app.master
            )

    def go_to_bookmark(self, event=None):
        selected_bookmark = self.app.ui_manager.bookmark_combo.get()
        if selected_bookmark in self.bookmarks:
            target_page = self.bookmarks[selected_bookmark]
            if self.app.pdf_handler.pdf_document and \
                    0 <= target_page < self.app.pdf_handler.total_pages:
                self.app.current_page_num = target_page
                self.app.display_page()  # Головний клас відповідає за відображення
                self.app.ui_manager.update_navigation_buttons_state()  # Оновлення кнопок навігації
            else:
                messagebox.showerror(
                    "Помилка",
                    f"Некоректний номер сторінки для закладки: {target_page + 1}",
                    parent=self.app.master
                )
        elif selected_bookmark:
            messagebox.showwarning(
                "Помилка",
                f"Закладка '{selected_bookmark}' не знайдена.",
                parent=self.app.master
            )

    def clear_bookmarks(self):
        self.bookmarks.clear()
        if hasattr(self.app, 'ui_manager') and self.app.ui_manager:  # Перевірка наявності ui_manager
            self.app.ui_manager.update_bookmark_combo_list(self.bookmarks)