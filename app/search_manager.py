import tkinter as tk
from tkinter import messagebox


# fitz тут більше не потрібен напряму, все через pdf_handler

class SearchManager:
    def __init__(self, app_ref):
        self.app = app_ref
        self.search_term = ""
        self.search_results_map = {}
        self.flat_search_hits = []
        self.current_flat_match_idx = -1
        self.use_ocr_for_current_search = False

    def perform_search(self, search_term_from_ui):
        if not self.app.pdf_handler.pdf_document: return

        self.search_term = search_term_from_ui.strip()
        self.use_ocr_for_current_search = False

        if not self.search_term:
            self.clear_search_results(update_ui=True)
            self.app.ui_manager.search_results_label.config(text="Введіть текст для пошуку")
            return

        self.search_results_map.clear()
        self.flat_search_hits.clear()
        self.current_flat_match_idx = -1
        total_hits = 0

        # Звичайний пошук
        for page_num in range(self.app.pdf_handler.total_pages):
            rects = self.app.pdf_handler.search_on_page(page_num, self.search_term, use_ocr=False)
            if rects:
                self.search_results_map[page_num] = rects
                for i, rect_obj in enumerate(rects):
                    self.flat_search_hits.append((page_num, i, rect_obj))
                total_hits += len(rects)

        if total_hits == 0:
            first_page_has_native_text, _ = self.app.pdf_handler.check_text_layer(0, ocr_fallback=False)
            if not first_page_has_native_text:
                if messagebox.askyesno("Пошук OCR",
                                       "Звичайний пошук не дав результатів.\n"
                                       "Схоже, документ не містить текстового шару.\n"
                                       "Спробувати пошук з розпізнаванням тексту (OCR)?\n"
                                       "(Це може зайняти деякий час)",
                                       parent=self.app.master):
                    self.use_ocr_for_current_search = True
                    self.search_results_map.clear()
                    self.flat_search_hits.clear()

                    # Пошук з OCR
                    for page_num in range(self.app.pdf_handler.total_pages):
                        self.app.master.update_idletasks()
                        self.app.ui_manager.search_results_label.config(text=f"OCR стор. {page_num + 1}...")
                        # Вказуємо мову 'ukr+eng' для кращого розпізнавання змішаного тексту
                        rects = self.app.pdf_handler.search_on_page(page_num, self.search_term, use_ocr=True,
                                                                    ocr_lang='ukr+eng')
                        if rects:
                            self.search_results_map[page_num] = rects
                            for i, rect_obj in enumerate(rects):
                                self.flat_search_hits.append((page_num, i, rect_obj))
                            total_hits += len(rects)

        self.app.ui_manager.search_results_label.config(text=f"Збігів: {total_hits}")

        if total_hits > 0:
            self.app.ui_manager.btn_clear_search.config(state=tk.NORMAL)
            self.show_next_match(from_start=True)
        else:
            self.app.ui_manager.search_results_label.config(text="Збігів: 0 (Нічого не знайдено)")
            self.app.ui_manager.btn_clear_search.config(state=tk.DISABLED)
            self.app.ui_manager.update_search_nav_buttons_state(0)
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
        self.use_ocr_for_current_search = False
        if update_ui and hasattr(self.app, 'ui_manager') and self.app.ui_manager:
            self.app.ui_manager.search_results_label.config(text="Збігів: 0")
            self.app.ui_manager.search_entry.delete(0, tk.END)
            self.app.ui_manager.btn_clear_search.config(state=tk.DISABLED)
            self.app.ui_manager.update_search_nav_buttons_state(0)
            if self.app.pdf_handler.pdf_document:
                self.app.display_page()