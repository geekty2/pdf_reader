import tkinter as tk
from tkinter import ttk, Menu
import tkinter.scrolledtext as scrolledtext


class UIManager:
    def __init__(self, master_tk_window, app_ref):
        self.master_tk_window = master_tk_window
        self.app = app_ref

        self.highlight_color_search_current_stroke = (0, 0, 255)
        self.highlight_color_search_current_fill = (173, 216, 230, 100)
        self.highlight_color_search_other_stroke = (100, 149, 237)
        self.highlight_color_search_other_fill = (173, 216, 230, 70)
        self.highlight_stroke_width = 1

        self.selection_color_fill_hex = "#add8e6"
        self.selection_outline_color = "blue"

        self.terminal_output_text = None
        self.terminal_input_entry = None
        self.current_dir_label = None

        self.bookmark_treeview = None
        self.lectures_treeview = None
        self.status_bar_label = None

        self._create_widgets()
        self._create_bookmark_context_menu()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.master_tk_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.left_controls_panel = ttk.Frame(main_frame, width=250)
        self.left_controls_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.left_controls_panel.pack_propagate(False)

        ttk.Label(self.left_controls_panel, text="Файл", font=("Arial", 10, "bold")).pack(pady=(5, 2), anchor=tk.W)
        self.btn_open = ttk.Button(self.left_controls_panel, text="Відкрити PDF (з файлу)",
                                   command=self.app.open_pdf_dialog_command)
        self.btn_open.pack(fill=tk.X, pady=2)
        self.btn_copy_page_text = ttk.Button(self.left_controls_panel, text="Копіювати текст сторінки",
                                             command=self.app.copy_current_page_text_command, state=tk.DISABLED)
        self.btn_copy_page_text.pack(fill=tk.X, pady=2)
        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(self.left_controls_panel, text="Лекції", font=("Arial", 10, "bold")).pack(pady=(5, 2), anchor=tk.W)
        lectures_frame = ttk.Frame(self.left_controls_panel)
        lectures_frame.pack(fill=tk.BOTH, expand=True, pady=2, ipady=5)

        lectures_scrollbar_y = ttk.Scrollbar(lectures_frame, orient=tk.VERTICAL)
        self.lectures_treeview = ttk.Treeview(lectures_frame,
                                              columns=('filename',),
                                              show='headings',
                                              yscrollcommand=lectures_scrollbar_y.set,
                                              selectmode=tk.BROWSE, height=5)
        lectures_scrollbar_y.config(command=self.lectures_treeview.yview)

        self.lectures_treeview.heading('filename', text='Назва файлу')
        self.lectures_treeview.column('filename', stretch=tk.YES, anchor=tk.W)

        lectures_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.lectures_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.lectures_treeview.bind("<Double-1>", self.app.open_selected_lecture_command)
        self.btn_refresh_lectures = ttk.Button(self.left_controls_panel, text="Оновити список лекцій",
                                               command=self.app.refresh_lectures_list_command)
        self.btn_refresh_lectures.pack(fill=tk.X, pady=(5, 2))
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

        ttk.Label(self.left_controls_panel, text="Закладки (Текст)", font=("Arial", 10, "bold")).pack(pady=(5, 2),
                                                                                                      anchor=tk.W)
        self.btn_init_add_bookmark = ttk.Button(self.left_controls_panel, text="Додати закладку (виділити текст)",
                                                command=self.app.bookmark_manager.initiate_add_bookmark,
                                                state=tk.DISABLED)
        self.btn_init_add_bookmark.pack(fill=tk.X, pady=2)
        bookmark_tree_frame = ttk.Frame(self.left_controls_panel)
        bookmark_tree_frame.pack(fill=tk.BOTH, expand=True, pady=2, ipady=5)

        self.bookmark_tree_scrollbar_y = ttk.Scrollbar(bookmark_tree_frame, orient=tk.VERTICAL)
        self.bookmark_tree_scrollbar_x = ttk.Scrollbar(bookmark_tree_frame, orient=tk.HORIZONTAL)
        columns = ('name', 'content_preview')
        self.bookmark_treeview = ttk.Treeview(bookmark_tree_frame,
                                              columns=columns, show='headings',
                                              yscrollcommand=self.bookmark_tree_scrollbar_y.set,
                                              xscrollcommand=self.bookmark_tree_scrollbar_x.set,
                                              selectmode=tk.BROWSE, height=5)
        self.bookmark_tree_scrollbar_y.config(command=self.bookmark_treeview.yview)
        self.bookmark_tree_scrollbar_x.config(command=self.bookmark_treeview.xview)
        self.bookmark_treeview.heading('name', text='Назва')
        self.bookmark_treeview.heading('content_preview', text='Вміст')
        self.bookmark_treeview.column('name', width=80, minwidth=60, stretch=tk.NO, anchor=tk.W)
        self.bookmark_treeview.column('content_preview', width=150, minwidth=100, anchor=tk.W)
        self.bookmark_tree_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.bookmark_tree_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.bookmark_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bookmark_treeview.bind("<Button-3>", self._show_bookmark_context_menu)
        self.bookmark_treeview.bind("<Button-2>", self._show_bookmark_context_menu)
        self.bookmark_treeview.bind("<Double-1>", self._use_selected_bookmark_from_event)
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

        self.right_panel = ttk.Frame(main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.pdf_display_frame = ttk.Frame(self.right_panel)
        self.pdf_display_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 5))
        self.canvas_frame = ttk.Frame(self.pdf_display_frame)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, bg="lightgrey", cursor="arrow")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar_canvas = ttk.Scrollbar(self.pdf_display_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar_canvas.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar_canvas.set)
        self.terminal_frame = ttk.Labelframe(self.right_panel, text="Термінал", height=200)
        self.terminal_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False, pady=(5, 0), padx=2)
        self.terminal_frame.pack_propagate(False)
        self.terminal_output_text = scrolledtext.ScrolledText(
            self.terminal_frame, wrap=tk.WORD, state=tk.DISABLED, height=10,
            font=("Courier New", 9), bg="black", fg="lightgreen"
        )
        self.terminal_output_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.terminal_output_text.tag_config("command", foreground="yellow")
        self.terminal_output_text.tag_config("output", foreground="lightgreen")
        self.terminal_output_text.tag_config("error", foreground="red")
        self.terminal_output_text.tag_config("info", foreground="lightblue")
        terminal_input_frame = ttk.Frame(self.terminal_frame)
        terminal_input_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        self.current_dir_label = ttk.Label(terminal_input_frame, text="CWD: >", font=("Courier New", 9))
        self.current_dir_label.pack(side=tk.LEFT, padx=(0, 3))
        self.terminal_input_entry = ttk.Entry(terminal_input_frame, font=("Courier New", 9))
        self.terminal_input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.terminal_input_entry.bind("<Return>", self.app.execute_terminal_command_command)
        self.status_bar_label = ttk.Label(self.master_tk_window, text="", anchor=tk.W)
        self.status_bar_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(2, 0))

    def _create_bookmark_context_menu(self):
        self.bookmark_context_menu = Menu(self.master_tk_window, tearoff=0)

        self.bookmark_context_menu.add_command(label="Використати в терміналі",
                                               command=self._use_selected_bookmark_from_context_menu)
        self.bookmark_context_menu.add_command(label="Видалити закладку",
                                               command=self._remove_selected_bookmark_from_context_menu)
        self.bookmark_context_menu.add_separator()
        self.bookmark_context_menu.add_command(label="Скасувати")

    def _show_bookmark_context_menu(self, event):
        item_id = self.bookmark_treeview.identify_row(event.y)
        if item_id:
            if not self.bookmark_treeview.selection() or item_id not in self.bookmark_treeview.selection():
                self.bookmark_treeview.selection_set(item_id)
            self.bookmark_treeview.focus(item_id)
            try:
                self.bookmark_context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.bookmark_context_menu.grab_release()

    def _use_selected_bookmark_from_context_menu(self):
        bookmark_name = self.app.bookmark_manager.get_selected_bookmark_name_from_treeview()
        print(f"UIManager (context menu): Спроба використати закладку: '{bookmark_name}'")
        if bookmark_name:
            self.app.bookmark_manager.use_bookmark_text_in_terminal(bookmark_name)

    def _remove_selected_bookmark_from_context_menu(self):
        bookmark_name = self.app.bookmark_manager.get_selected_bookmark_name_from_treeview()
        print(f"UIManager (context menu): Спроба видалити закладку: '{bookmark_name}'")
        if bookmark_name:
            self.app.bookmark_manager.remove_bookmark_by_name(bookmark_name)

    def _use_selected_bookmark_from_event(self, event):

        selected_items = self.bookmark_treeview.selection()
        if not selected_items: return

        item_id = selected_items[0]
        self.bookmark_treeview.focus(item_id)

        bookmark_name = self.app.bookmark_manager.get_selected_bookmark_name_from_treeview()
        print(f"UIManager (double-click): Спроба використати закладку: '{bookmark_name}'")
        if bookmark_name:
            self.app.bookmark_manager.use_bookmark_text_in_terminal(bookmark_name)

    def update_bookmark_treeview(self, bookmarks_text_content_dict):
        if not self.bookmark_treeview: return

        current_selection_iid = self.bookmark_treeview.focus()


        for item in self.bookmark_treeview.get_children():
            self.bookmark_treeview.delete(item)

        sorted_bookmark_names = sorted(bookmarks_text_content_dict.keys())
        for name in sorted_bookmark_names:
            content = bookmarks_text_content_dict[name]
            preview_content = (content[:35] + '...') if len(content) > 35 else content
            self.bookmark_treeview.insert('', tk.END, iid=name, values=(name, preview_content.replace('\n', ' ')))

        if current_selection_iid and self.bookmark_treeview.exists(current_selection_iid):
            self.bookmark_treeview.focus(current_selection_iid)
            self.bookmark_treeview.selection_set(current_selection_iid)


        self.update_bookmark_related_ui_state()

    def update_status_bar(self, message):
        if self.status_bar_label:
            self.status_bar_label.config(text=message)

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

    def update_bookmark_related_ui_state(self):
        pdf_doc_exists = self.app.pdf_handler.pdf_document is not None
        if hasattr(self, 'btn_init_add_bookmark'):  # Перевірка наявності кнопки
            self.btn_init_add_bookmark.config(state=tk.NORMAL if pdf_doc_exists else tk.DISABLED)

    def update_search_buttons_state(self, search_active=False, has_results=False):
        pdf_doc_exists = self.app.pdf_handler.pdf_document is not None
        self.btn_search.config(state=tk.NORMAL if pdf_doc_exists else tk.DISABLED)
        self.btn_clear_search.config(state=tk.NORMAL if pdf_doc_exists and search_active else tk.DISABLED)

    def update_search_nav_buttons_state(self, num_hits):
        state = tk.NORMAL if num_hits > 0 else tk.DISABLED
        self.btn_next_match.config(state=state)
        self.btn_prev_match.config(state=state)

    def update_all_button_states(self):
        self.update_navigation_buttons_state()
        self.update_zoom_buttons_state()
        self.update_bookmark_related_ui_state()

        search_manager_exists = hasattr(self.app, 'search_manager') and self.app.search_manager is not None
        has_search_results = search_manager_exists and len(self.app.search_manager.flat_search_hits) > 0
        search_term_active = search_manager_exists and bool(self.app.search_manager.search_term)

        self.update_search_buttons_state(search_active=search_term_active, has_results=has_search_results)
        self.update_search_nav_buttons_state(
            len(self.app.search_manager.flat_search_hits) if search_manager_exists else 0)

        pdf_doc_exists = self.app.pdf_handler.pdf_document is not None
        self.btn_copy_page_text.config(state=tk.NORMAL if pdf_doc_exists else tk.DISABLED)

    def append_to_terminal(self, text, tag=None):
        if self.terminal_output_text:
            self.terminal_output_text.config(state=tk.NORMAL)
            if tag:
                self.terminal_output_text.insert(tk.END, text, tag)
            else:
                self.terminal_output_text.insert(tk.END, text, "output")
            self.terminal_output_text.see(tk.END)
            self.terminal_output_text.config(state=tk.DISABLED)

    def update_terminal_cwd_label(self, cwd_path):
        if self.current_dir_label:
            max_len = 35
            display_path = cwd_path
            if len(cwd_path) > max_len:
                display_path = "..." + cwd_path[-(max_len - 3):]
            self.current_dir_label.config(text=f"{display_path}> ")

    def populate_lectures_treeview(self, lectures_files):
        """Заповнює Treeview списком файлів лекцій."""
        if self.lectures_treeview:

            for item in self.lectures_treeview.get_children():
                self.lectures_treeview.delete(item)

            for filename in sorted(lectures_files):
                self.lectures_treeview.insert('', tk.END, iid=filename, values=(filename,))
