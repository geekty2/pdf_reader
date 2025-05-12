# Файл: app/ui_manager.py

import tkinter as tk
from tkinter import ttk


class UIManager:
    def __init__(self, master, app_ref):
        self.master = master  # Головне вікно Tk
        self.app = app_ref  # Посилання на головний клас PDFViewerApp

        # Кольори для підсвітки пошуку (перенесено з PDFViewerApp)
        self.highlight_color_search_current_stroke = (0, 0, 255)
        self.highlight_color_search_current_fill = (173, 216, 230, 100)
        self.highlight_color_search_other_stroke = (100, 149, 237)
        self.highlight_color_search_other_fill = (173, 216, 230, 70)
        self.highlight_stroke_width = 1

        # Кольори для виділення тексту
        self.selection_color_fill_hex = "#add8e6"
        self.selection_outline_color = "blue"

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.left_controls_panel = ttk.Frame(main_frame, width=250)
        self.left_controls_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.left_controls_panel.pack_propagate(False)

        # --- Секція Файл ---
        ttk.Label(self.left_controls_panel, text="Файл", font=("Arial", 10, "bold")).pack(pady=(5, 2), anchor=tk.W)
        self.btn_open = ttk.Button(self.left_controls_panel, text="Відкрити PDF", command=self.app.open_pdf_command)
        self.btn_open.pack(fill=tk.X, pady=2)
        self.btn_copy_page_text = ttk.Button(self.left_controls_panel, text="Копіювати текст сторінки",
                                             command=self.app.copy_current_page_text_command, state=tk.DISABLED)
        self.btn_copy_page_text.pack(fill=tk.X, pady=2)

        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- Секція Навігація сторінками ---
        ttk.Label(self.left_controls_panel, text="Навігація сторінками", font=("Arial", 10, "bold")).pack(pady=(5, 2),
                                                                                                          anchor=tk.W)
        self.btn_prev = ttk.Button(self.left_controls_panel, text="< Попередня", command=self.app.prev_page_command,
                                   state=tk.DISABLED)
        self.btn_prev.pack(fill=tk.X, pady=2)
        self.page_info_label = ttk.Label(self.left_controls_panel, text="Сторінка: - / -")
        self.page_info_label.pack(pady=2)
        self.btn_next = ttk.Button(self.left_controls_panel, text="Наступна >", command=self.app.next_page_command,
                                   state=tk.DISABLED)
        self.btn_next.pack(fill=tk.X, pady=2)

        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- Секція Закладки (Теми/Питання) ---
        ttk.Label(self.left_controls_panel, text="Закладки (Теми/Питання)", font=("Arial", 10, "bold")).pack(
            pady=(5, 2), anchor=tk.W)
        # ВИПРАВЛЕННЯ: postcommand викликає метод UIManager
        self.bookmark_combo = ttk.Combobox(self.left_controls_panel, state="readonly",
                                           postcommand=self._update_bookmark_combo_values_from_manager)
        self.bookmark_combo.pack(fill=tk.X, pady=2)
        self.bookmark_combo.bind("<<ComboboxSelected>>", self.app.bookmark_manager.go_to_bookmark)
        bookmark_buttons_frame = ttk.Frame(self.left_controls_panel)
        bookmark_buttons_frame.pack(fill=tk.X)
        self.btn_add_bookmark = ttk.Button(bookmark_buttons_frame, text="Додати закладку",
                                           command=self.app.bookmark_manager.add_bookmark, state=tk.DISABLED)
        self.btn_add_bookmark.pack(side=tk.LEFT, expand=True, fill=tk.X, pady=2, padx=(0, 1))
        self.btn_remove_bookmark = ttk.Button(bookmark_buttons_frame, text="Видалити",
                                              command=self.app.bookmark_manager.remove_bookmark, state=tk.DISABLED,
                                              width=8)
        self.btn_remove_bookmark.pack(side=tk.LEFT, fill=tk.X, pady=2, padx=(1, 0))

        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- Секція Пошук по тексту ---
        ttk.Label(self.left_controls_panel, text="Пошук по тексту", font=("Arial", 10, "bold")).pack(pady=(5, 2),
                                                                                                     anchor=tk.W)
        self.search_entry = ttk.Entry(self.left_controls_panel)
        self.search_entry.pack(fill=tk.X, pady=2)
        self.search_entry.bind("<Return>", self.app.perform_search_command)
        search_buttons_frame = ttk.Frame(self.left_controls_panel)
        search_buttons_frame.pack(fill=tk.X)
        self.btn_search = ttk.Button(search_buttons_frame, text="Знайти", command=self.app.perform_search_command,
                                     state=tk.DISABLED)
        self.btn_search.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 1))
        self.btn_clear_search = ttk.Button(search_buttons_frame, text="Очистити",
                                           command=self.app.clear_search_results_command, state=tk.DISABLED, width=8)
        self.btn_clear_search.pack(side=tk.LEFT, fill=tk.X, padx=(1, 0))
        self.search_results_label = ttk.Label(self.left_controls_panel, text="Збігів: 0")
        self.search_results_label.pack(pady=2)
        search_nav_frame = ttk.Frame(self.left_controls_panel)
        search_nav_frame.pack(fill=tk.X)
        self.btn_prev_match = ttk.Button(search_nav_frame, text="<", command=self.app.search_manager.show_prev_match,
                                         state=tk.DISABLED, width=3)
        self.btn_prev_match.pack(side=tk.LEFT, padx=(0, 1))
        self.btn_next_match = ttk.Button(search_nav_frame, text=">", command=self.app.search_manager.show_next_match,
                                         state=tk.DISABLED, width=3)
        self.btn_next_match.pack(side=tk.LEFT, padx=(1, 0))

        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- Секція Масштаб ---
        ttk.Label(self.left_controls_panel, text="Масштаб", font=("Arial", 10, "bold")).pack(pady=(5, 2), anchor=tk.W)
        zoom_buttons_frame = ttk.Frame(self.left_controls_panel)
        zoom_buttons_frame.pack(fill=tk.X)
        self.btn_zoom_out = ttk.Button(zoom_buttons_frame, text="-", command=self.app.zoom_out_command,
                                       state=tk.DISABLED, width=3)
        self.btn_zoom_out.pack(side=tk.LEFT, padx=(0, 2))
        self.btn_reset_zoom = ttk.Button(zoom_buttons_frame, text="⟲", command=self.app.reset_zoom_to_default_command,
                                         state=tk.DISABLED, width=3)
        self.btn_reset_zoom.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.btn_zoom_in = ttk.Button(zoom_buttons_frame, text="+", command=self.app.zoom_in_command, state=tk.DISABLED,
                                      width=3)
        self.btn_zoom_in.pack(side=tk.LEFT, padx=(2, 0))
        self.zoom_label = ttk.Label(self.left_controls_panel, text=f"Масштаб: {int(self.app.current_zoom * 100)}%")
        self.zoom_label.pack(pady=2)

        # --- Права панель для PDF ---
        self.right_pdf_panel = ttk.Frame(main_frame)
        self.right_pdf_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas_frame = ttk.Frame(self.right_pdf_panel)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="lightgrey", cursor="arrow")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar = ttk.Scrollbar(self.right_pdf_panel, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

    def _update_bookmark_combo_values_from_manager(self):
        """Отримує актуальні закладки від BookmarkManager і оновлює Combobox."""
        # Переконуємося, що bookmark_manager існує, перш ніж звертатися до нього
        if hasattr(self.app, 'bookmark_manager') and self.app.bookmark_manager is not None:
            bookmarks_dict = self.app.bookmark_manager.bookmarks
            self.update_bookmark_combo_list(bookmarks_dict)
        else:
            # Якщо bookmark_manager ще не створено, можна просто очистити комбобокс
            # або нічого не робити, якщо це викликається до повної ініціалізації.
            self.update_bookmark_combo_list({})  # Передати порожній словник

    def update_navigation_buttons_state(self):
        pdf_doc_exists = self.app.pdf_handler.pdf_document is not None
        total_pages = self.app.pdf_handler.total_pages if pdf_doc_exists else 0
        current_page = self.app.current_page_num

        state = tk.NORMAL if pdf_doc_exists and total_pages > 0 else tk.DISABLED
        self.btn_prev.config(state=state if current_page > 0 else tk.DISABLED)
        self.btn_next.config(state=state if current_page < total_pages - 1 else tk.DISABLED)
        self.page_info_label.config(
            text=f"Сторінка: {current_page + 1 if pdf_doc_exists and total_pages > 0 else '-'} / {total_pages if pdf_doc_exists and total_pages > 0 else '-'}")

    def update_zoom_buttons_state(self):
        pdf_doc_exists = self.app.pdf_handler.pdf_document is not None
        if pdf_doc_exists:
            self.btn_zoom_in.config(
                state=tk.NORMAL if self.app.current_zoom < self.app.max_zoom - self.app.epsilon else tk.DISABLED)
            self.btn_zoom_out.config(
                state=tk.NORMAL if self.app.current_zoom > self.app.min_zoom + self.app.epsilon else tk.DISABLED)
            self.btn_reset_zoom.config(state=tk.NORMAL if abs(
                self.app.current_zoom - self.app.default_zoom_for_file) > self.app.epsilon else tk.DISABLED)
        else:
            self.btn_zoom_in.config(state=tk.DISABLED)
            self.btn_zoom_out.config(state=tk.DISABLED)
            self.btn_reset_zoom.config(state=tk.DISABLED)
        self.zoom_label.config(text=f"Масштаб: {int(self.app.current_zoom * 100)}%")

    def update_bookmark_buttons_state(self):
        pdf_doc_exists = self.app.pdf_handler.pdf_document is not None
        # Перевіряємо, чи bookmark_manager вже створено
        bookmarks_exist = hasattr(self.app,
                                  'bookmark_manager') and self.app.bookmark_manager and self.app.bookmark_manager.bookmarks

        self.btn_add_bookmark.config(state=tk.NORMAL if pdf_doc_exists else tk.DISABLED)
        self.btn_remove_bookmark.config(state=tk.NORMAL if pdf_doc_exists and bookmarks_exist else tk.DISABLED)

    def update_search_buttons_state(self, search_active=False, has_results=False):
        pdf_doc_exists = self.app.pdf_handler.pdf_document is not None
        self.btn_search.config(state=tk.NORMAL if pdf_doc_exists else tk.DISABLED)
        self.btn_clear_search.config(state=tk.NORMAL if pdf_doc_exists and search_active else tk.DISABLED)

    def update_search_nav_buttons_state(self, num_hits):
        state = tk.NORMAL if num_hits > 0 else tk.DISABLED
        self.btn_next_match.config(state=state)
        self.btn_prev_match.config(state=state)

    def update_bookmark_combo_list(self, bookmarks_dict):
        sorted_bookmark_names = sorted(bookmarks_dict.keys())
        self.bookmark_combo['values'] = sorted_bookmark_names
        if not sorted_bookmark_names:
            self.bookmark_combo.set('')
        elif self.bookmark_combo.get() not in sorted_bookmark_names:
            self.bookmark_combo.set('')

    def update_all_button_states(self):
        self.update_navigation_buttons_state()
        self.update_zoom_buttons_state()
        self.update_bookmark_buttons_state()

        search_manager_exists = hasattr(self.app, 'search_manager') and self.app.search_manager is not None
        has_search_results = search_manager_exists and len(self.app.search_manager.flat_search_hits) > 0
        search_term_active = search_manager_exists and bool(self.app.search_manager.search_term)

        self.update_search_buttons_state(search_active=search_term_active, has_results=has_search_results)
        self.update_search_nav_buttons_state(
            len(self.app.search_manager.flat_search_hits) if search_manager_exists else 0)

        pdf_doc_exists = self.app.pdf_handler.pdf_document is not None
        self.btn_copy_page_text.config(state=tk.NORMAL if pdf_doc_exists else tk.DISABLED)