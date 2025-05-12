import fitz  # PyMuPDF
import tkinter as tk  # Для messagebox
from tkinter import messagebox


class SearchManager:
    def __init__(self, app_ref):
        self.app = app_ref
        self.search_term = ""
        self.search_results_map = {}
        self.flat_search_hits = []
        self.current_flat_match_idx = -1

    def perform_search(self, search_term_from_ui):
        if not self.app.pdf_handler.pdf_document: return

        self.search_term = search_term_from_ui
        # print(f"SearchManager: Пошуковий запит: '{self.search_term}'")

        if not self.search_term.strip():
            self.clear_search_results(update_ui=True)  # Передаємо прапорець для оновлення UI
            self.app.ui_manager.search_results_label.config(text="Введіть текст для пошуку")
            return

        self.search_results_map.clear()
        self.flat_search_hits.clear()
        self.current_flat_match_idx = -1
        total_hits = 0

        search_flags = 1  # Ігнорувати регістр

        for page_num in range(self.app.pdf_handler.total_pages):
            page = self.app.pdf_handler.get_page(page_num)
            if not page: continue

            hit_quads = page.search_for(self.search_term, quads=True, flags=search_flags)

            if hit_quads:
                page_rects = []
                for i, quad in enumerate(hit_quads):
                    rect = quad.rect
                    page_rects.append(rect)
                    self.flat_search_hits.append((page_num, i, rect))
                self.search_results_map[page_num] = page_rects
                total_hits += len(hit_quads)

        self.app.ui_manager.search_results_label.config(text=f"Збігів: {total_hits}")

        if total_hits > 0:
            self.app.ui_manager.btn_clear_search.config(state=tk.NORMAL)
            self.show_next_match(from_start=True)
        else:
            self.app.ui_manager.search_results_label.config(text="Збігів: 0 (Нічого не знайдено)")
            self.app.ui_manager.btn_clear_search.config(state=tk.DISABLED)
            self.app.ui_manager.update_search_nav_buttons_state(0)  # 0 збігів
            self.app.display_page()

    def show_next_match(self, from_start=False):
        if not self.flat_search_hits: return
        if from_start:
            self.current_flat_match_idx = 0
        else:
            self.current_flat_match_idx += 1

        if self.current_flat_match_idx >= len(self.flat_search_hits):
            self.current_flat_match_idx = 0
            messagebox.showinfo("Пошук", "Досягнуто кінця збігів, починаємо знову.", parent=self.app.master)

        self._navigate_to_current_match()

    def show_prev_match(self):
        if not self.flat_search_hits: return
        self.current_flat_match_idx -= 1

        if self.current_flat_match_idx < 0:
            self.current_flat_match_idx = len(self.flat_search_hits) - 1
            messagebox.showinfo("Пошук", "Досягнуто початку збігів, переходимо до останнього.", parent=self.app.master)

        self._navigate_to_current_match()

    def _navigate_to_current_match(self):
        if not (0 <= self.current_flat_match_idx < len(self.flat_search_hits)):
            self.app.ui_manager.update_search_nav_buttons_state(len(self.flat_search_hits))
            return

        page_num, _, _ = self.flat_search_hits[self.current_flat_match_idx]
        if self.app.current_page_num != page_num:
            self.app.current_page_num = page_num

        self.app.display_page()
        self.app.ui_manager.update_navigation_buttons_state()
        self.app.ui_manager.update_search_nav_buttons_state(len(self.flat_search_hits))

    def clear_search_results(self, update_ui=True):
        self.search_term = ""
        self.search_results_map.clear()
        self.flat_search_hits.clear()
        self.current_flat_match_idx = -1
        if update_ui and hasattr(self.app, 'ui_manager') and self.app.ui_manager:
            self.app.ui_manager.search_results_label.config(text="Збігів: 0")
            self.app.ui_manager.search_entry.delete(0, tk.END)
            self.app.ui_manager.btn_clear_search.config(state=tk.DISABLED)
            self.app.ui_manager.update_search_nav_buttons_state(0)
            if self.app.pdf_handler.pdf_document:
                self.app.display_page()  # Перемалювати без підсвітки