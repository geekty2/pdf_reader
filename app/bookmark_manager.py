import tkinter as tk
from tkinter import simpledialog, messagebox, Menu


class BookmarkManager:
    def __init__(self, app_ref):
        self.app = app_ref
        self.bookmarks_text_content = {}
        self.is_adding_bookmark_mode = False
        self.pending_bookmark_text = None

    def initiate_add_bookmark(self):
        # ... (як раніше) ...
        if not self.app.pdf_handler.pdf_document:
            messagebox.showwarning("Увага", "Спочатку відкрийте PDF файл.", parent=self.app.master)
            return

        self.is_adding_bookmark_mode = True
        self.pending_bookmark_text = None
        messagebox.showinfo(
            "Додавання закладки",
            "Тепер виділіть текст на сторінці лівою кнопкою миші.\nПісля виділення вам буде запропоновано назвати закладку.",
            parent=self.app.master
        )
        self.app.ui_manager.update_status_bar("Режим додавання закладки: виділіть текст...")

    def finalize_add_bookmark(self, selected_text):
        if not self.is_adding_bookmark_mode:
            self.app.ui_manager.update_status_bar("")
            return

        if not selected_text or not selected_text.strip():
            messagebox.showwarning("Додавання закладки", "Виділений текст порожній або не вдалося розпізнати.",
                                   parent=self.app.master)
            self.is_adding_bookmark_mode = False
            self.app.ui_manager.update_status_bar("")
            return

        self.pending_bookmark_text = selected_text.strip()

        bookmark_name = simpledialog.askstring(
            "Назва закладки",
            f"Введіть назву для закладки з текстом:\n'{self.pending_bookmark_text[:50]}{'...' if len(self.pending_bookmark_text) > 50 else ''}'",
            parent=self.app.master
        )

        if bookmark_name and bookmark_name.strip():
            actual_bookmark_name = bookmark_name.strip()
            print(
                f"BookmarkManager: Додавання закладки '{actual_bookmark_name}' з вмістом: '{self.pending_bookmark_text[:30]}...'")
            self.bookmarks_text_content[actual_bookmark_name] = self.pending_bookmark_text
            self.app.ui_manager.update_bookmark_treeview(self.bookmarks_text_content)
        elif bookmark_name is not None:
            messagebox.showwarning("Помилка", "Назва закладки не може бути порожньою.", parent=self.app.master)

        self.is_adding_bookmark_mode = False
        self.pending_bookmark_text = None
        self.app.ui_manager.update_status_bar("")

    def remove_bookmark_by_name(self, bookmark_name):
        print(f"BookmarkManager: Спроба видалити закладку: '{bookmark_name}'")
        if bookmark_name and bookmark_name in self.bookmarks_text_content:
            if messagebox.askyesno(
                    "Видалити закладку",
                    f"Видалити закладку '{bookmark_name}'?",
                    parent=self.app.master
            ):
                del self.bookmarks_text_content[bookmark_name]
                print(f"BookmarkManager: Закладку '{bookmark_name}' видалено зі словника.")
                self.app.ui_manager.update_bookmark_treeview(self.bookmarks_text_content)
        else:
            print(f"BookmarkManager: Закладка '{bookmark_name}' не знайдена в словнику для видалення.")

    def use_bookmark_text_in_terminal(self, bookmark_name):
        print(f"BookmarkManager: Спроба використати закладку: '{bookmark_name}'")
        if bookmark_name and bookmark_name in self.bookmarks_text_content:
            text_to_use = self.bookmarks_text_content[bookmark_name]
            print(f"BookmarkManager: Текст для вставки: '{text_to_use}'")

            self.app.ui_manager.terminal_input_entry.delete(0, tk.END)
            self.app.ui_manager.terminal_input_entry.insert(0, text_to_use)
            self.app.ui_manager.terminal_input_entry.focus_set()
            self.app.ui_manager.update_status_bar(f"Текст закладки '{bookmark_name}' вставлено в термінал.")
        else:
            print(f"BookmarkManager: Закладка '{bookmark_name}' не знайдена для використання.")

    def clear_bookmarks(self):
        # ... (як раніше) ...
        self.bookmarks_text_content.clear()
        self.is_adding_bookmark_mode = False
        self.pending_bookmark_text = None
        if hasattr(self.app, 'ui_manager') and self.app.ui_manager:
            self.app.ui_manager.update_bookmark_treeview(self.bookmarks_text_content)
            self.app.ui_manager.update_status_bar("")

    def get_selected_bookmark_name_from_treeview(self):
        if hasattr(self.app, 'ui_manager') and self.app.ui_manager.bookmark_treeview:
            selected_item_id = self.app.ui_manager.bookmark_treeview.focus()
            print(
                f"BookmarkManager (get_selected): focus() iid: '{selected_item_id}', тип: {type(selected_item_id)}")

            if selected_item_id:
                item_details = self.app.ui_manager.bookmark_treeview.item(selected_item_id)
                print(
                    f"BookmarkManager (get_selected): item_details для iid '{selected_item_id}': {item_details}")

                if isinstance(selected_item_id, str) and selected_item_id:
                    print(
                        f"BookmarkManager (get_selected): Повертаємо iid як назву: '{selected_item_id}'")
                    return selected_item_id  # ПОВЕРТАЄМО IID

                if item_details and 'values' in item_details and item_details['values']:
                    bookmark_name_from_values = item_details['values'][0]
                    print(
                        f"BookmarkManager (get_selected): Отримано назву з values: '{bookmark_name_from_values}', тип: {type(bookmark_name_from_values)}")  # ДІАГНОСТИКА
                    return bookmark_name_from_values

        print("BookmarkManager (get_selected): Не вдалося отримати вибрану закладку.")
        return None