import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import os
import platform
import pyperclip  # Для копіювання в буфер обміну (pip install pyperclip)


class PDFViewerApp:
    def __init__(self, master):
        self.master = master
        master.title("Розширений PDF Рідер")

        self.window_width = 1100
        self.window_height = 750
        master.geometry(f"{self.window_width}x{self.window_height}")
        master.resizable(False, False)

        self.pdf_document = None
        self.current_page_num = 0
        self.total_pages = 0
        self.tk_image = None

        self.current_zoom = 1.0
        self.default_zoom_for_file = 1.0
        self.zoom_step = 0.1
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.epsilon = 0.001

        # Панорамування правою кнопкою
        self.is_panning_right_btn = False
        self.pan_start_x_right_btn = 0
        self.pan_start_y_right_btn = 0

        # Для закладок
        self.bookmarks = {}

        # Для пошуку
        self.search_term = ""
        self.search_results_map = {}
        self.flat_search_hits = []
        self.current_flat_match_idx = -1

        # Кольори для підсвітки пошуку (блакитні)
        self.highlight_color_search_current_stroke = (0, 0, 255)  # Синій контур для поточного
        self.highlight_color_search_current_fill = (173, 216, 230,
                                                    100)  # Світло-блакитний напівпрозорий для поточного (LightBlue з alpha)
        self.highlight_color_search_other_stroke = (100, 149, 237)  # Блакитний (CornflowerBlue) контур для інших
        self.highlight_color_search_other_fill = (173, 216, 230, 70)  # Світло-блакитний з меншою прозорістю для інших
        self.highlight_stroke_width = 1

        # Для виділення тексту лівою кнопкою
        self.is_selecting_text = False
        self.selection_rect_start_x = 0
        self.selection_rect_start_y = 0
        self.selection_rect_id = None
        self.selection_color_fill_hex = "#add8e6"  # Світло-блакитний для stipple
        self.selection_outline_color = "blue"

        # --- Головна структура ---
        main_frame = ttk.Frame(master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Ліва панель керування ---
        self.left_controls_panel = ttk.Frame(main_frame, width=250)
        self.left_controls_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.left_controls_panel.pack_propagate(False)

        # --- Секція Файл ---
        ttk.Label(self.left_controls_panel, text="Файл", font=("Arial", 10, "bold")).pack(pady=(5, 2), anchor=tk.W)
        self.btn_open = ttk.Button(self.left_controls_panel, text="Відкрити PDF", command=self.open_pdf)
        self.btn_open.pack(fill=tk.X, pady=2)
        self.btn_copy_page_text = ttk.Button(self.left_controls_panel, text="Копіювати текст сторінки",
                                             command=self.copy_current_page_text, state=tk.DISABLED)
        self.btn_copy_page_text.pack(fill=tk.X, pady=2)

        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- Секція Навігація сторінками ---
        ttk.Label(self.left_controls_panel, text="Навігація сторінками", font=("Arial", 10, "bold")).pack(pady=(5, 2),
                                                                                                          anchor=tk.W)
        self.btn_prev = ttk.Button(self.left_controls_panel, text="< Попередня", command=self.prev_page,
                                   state=tk.DISABLED)
        self.btn_prev.pack(fill=tk.X, pady=2)
        self.page_info_label = ttk.Label(self.left_controls_panel, text="Сторінка: - / -")
        self.page_info_label.pack(pady=2)
        self.btn_next = ttk.Button(self.left_controls_panel, text="Наступна >", command=self.next_page,
                                   state=tk.DISABLED)
        self.btn_next.pack(fill=tk.X, pady=2)

        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- Секція Закладки (Теми/Питання) ---
        ttk.Label(self.left_controls_panel, text="Закладки (Теми/Питання)", font=("Arial", 10, "bold")).pack(
            pady=(5, 2), anchor=tk.W)
        self.bookmark_combo = ttk.Combobox(self.left_controls_panel, state="readonly",
                                           postcommand=self.update_bookmark_combo_list)
        self.bookmark_combo.pack(fill=tk.X, pady=2)
        self.bookmark_combo.bind("<<ComboboxSelected>>", self.go_to_bookmark)
        bookmark_buttons_frame = ttk.Frame(self.left_controls_panel)
        bookmark_buttons_frame.pack(fill=tk.X)
        self.btn_add_bookmark = ttk.Button(bookmark_buttons_frame, text="Додати закладку", command=self.add_bookmark,
                                           state=tk.DISABLED)
        self.btn_add_bookmark.pack(side=tk.LEFT, expand=True, fill=tk.X, pady=2, padx=(0, 1))
        self.btn_remove_bookmark = ttk.Button(bookmark_buttons_frame, text="Видалити", command=self.remove_bookmark,
                                              state=tk.DISABLED, width=8)
        self.btn_remove_bookmark.pack(side=tk.LEFT, fill=tk.X, pady=2, padx=(1, 0))

        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- Секція Пошук по тексту ---
        ttk.Label(self.left_controls_panel, text="Пошук по тексту", font=("Arial", 10, "bold")).pack(pady=(5, 2),
                                                                                                     anchor=tk.W)
        self.search_entry = ttk.Entry(self.left_controls_panel)
        self.search_entry.pack(fill=tk.X, pady=2)
        self.search_entry.bind("<Return>", self.perform_search)
        search_buttons_frame = ttk.Frame(self.left_controls_panel)
        search_buttons_frame.pack(fill=tk.X)
        self.btn_search = ttk.Button(search_buttons_frame, text="Знайти", command=self.perform_search,
                                     state=tk.DISABLED)
        self.btn_search.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 1))
        self.btn_clear_search = ttk.Button(search_buttons_frame, text="Очистити", command=self.clear_search_results,
                                           state=tk.DISABLED, width=8)
        self.btn_clear_search.pack(side=tk.LEFT, fill=tk.X, padx=(1, 0))
        self.search_results_label = ttk.Label(self.left_controls_panel, text="Збігів: 0")
        self.search_results_label.pack(pady=2)
        search_nav_frame = ttk.Frame(self.left_controls_panel)
        search_nav_frame.pack(fill=tk.X)
        self.btn_prev_match = ttk.Button(search_nav_frame, text="<", command=self.show_prev_match, state=tk.DISABLED,
                                         width=3)
        self.btn_prev_match.pack(side=tk.LEFT, padx=(0, 1))
        self.btn_next_match = ttk.Button(search_nav_frame, text=">", command=self.show_next_match, state=tk.DISABLED,
                                         width=3)
        self.btn_next_match.pack(side=tk.LEFT, padx=(1, 0))

        ttk.Separator(self.left_controls_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- Секція Масштаб ---
        ttk.Label(self.left_controls_panel, text="Масштаб", font=("Arial", 10, "bold")).pack(pady=(5, 2), anchor=tk.W)
        zoom_buttons_frame = ttk.Frame(self.left_controls_panel)
        zoom_buttons_frame.pack(fill=tk.X)
        self.btn_zoom_out = ttk.Button(zoom_buttons_frame, text="-", command=self.zoom_out, state=tk.DISABLED, width=3)
        self.btn_zoom_out.pack(side=tk.LEFT, padx=(0, 2))
        self.btn_reset_zoom = ttk.Button(zoom_buttons_frame, text="⟲", command=self.reset_zoom_to_default,
                                         state=tk.DISABLED, width=3)
        self.btn_reset_zoom.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.btn_zoom_in = ttk.Button(zoom_buttons_frame, text="+", command=self.zoom_in, state=tk.DISABLED, width=3)
        self.btn_zoom_in.pack(side=tk.LEFT, padx=(2, 0))
        self.zoom_label = ttk.Label(self.left_controls_panel, text=f"Масштаб: {int(self.current_zoom * 100)}%")
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
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor=tk.NW)

        # --- Прив'язки подій миші ---
        self.canvas.bind("<ButtonPress-3>", self.start_pan_right_btn)
        self.canvas.bind("<B3-Motion>", self.do_pan_right_btn)
        self.canvas.bind("<ButtonRelease-3>", self.end_pan_right_btn)

        if platform.system() == "Linux":
            self.canvas.bind("<Button-4>", self.on_mouse_wheel_linux)
            self.canvas.bind("<Button-5>", self.on_mouse_wheel_linux)
        else:
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.canvas.bind("<ButtonPress-1>", self.start_text_selection)
        self.canvas.bind("<B1-Motion>", self.do_text_selection)
        self.canvas.bind("<ButtonRelease-1>", self.end_text_selection_and_copy)

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_pdf(self):
        filepath = filedialog.askopenfilename(
            title="Виберіть PDF файл", filetypes=(("PDF файли", "*.pdf"), ("Всі файли", "*.*"))
        )
        if not filepath: return
        try:
            if self.pdf_document: self.pdf_document.close()
            self.clear_bookmarks()
            self.clear_search_results()

            self.pdf_document = fitz.open(filepath)
            # Діагностика наявності тексту
            try:
                test_page_text = self.pdf_document.load_page(0).get_text()
                if not test_page_text.strip():
                    messagebox.showwarning("Інформація про PDF",
                                           "Увага: Перша сторінка PDF не містить видобутого тексту. "
                                           "Можливо, це сканований документ без OCR, і пошук тексту не працюватиме.",
                                           parent=self.master)
                    print("ПОПЕРЕДЖЕННЯ: Текст на першій сторінці не знайдено!")
                # else:
                #     print(f"Текст з першої сторінки (перші 100 символів): {test_page_text[:100]}")
            except Exception as e_text:
                print(f"Помилка при отриманні тексту з першої сторінки: {e_text}")

            self.total_pages = self.pdf_document.page_count
            self.current_page_num = 0
            self.master.title(f"PDF Рідер - {os.path.basename(filepath)}")

            self.fit_page_to_canvas_and_set_default()
            self.display_page()

            self.update_navigation_buttons()
            self.update_all_zoom_buttons_state()
            self.btn_add_bookmark.config(state=tk.NORMAL)
            self.btn_remove_bookmark.config(state=tk.NORMAL if self.bookmarks else tk.DISABLED)
            self.btn_search.config(state=tk.NORMAL)
            self.btn_clear_search.config(state=tk.DISABLED)
            self.btn_copy_page_text.config(state=tk.NORMAL)
            self.update_bookmark_combo_list()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити PDF файл: {e}", parent=self.master)
            self.clear_display()

    def copy_current_page_text(self):
        if not self.pdf_document: return
        try:
            page = self.pdf_document.load_page(self.current_page_num)
            text = page.get_text("text")
            pyperclip.copy(text)
            messagebox.showinfo("Копіювання", "Текст поточної сторінки скопійовано.", parent=self.master)
        except pyperclip.PyperclipException as e:
            messagebox.showerror("Помилка копіювання", f"Не вдалося скопіювати: pyperclip не налаштований.\n{e}",
                                 parent=self.master)
        except Exception as e:
            messagebox.showerror("Помилка копіювання", f"Не вдалося скопіювати текст: {e}", parent=self.master)

    def add_bookmark(self):
        if not self.pdf_document: return
        bookmark_name = simpledialog.askstring("Додати закладку", "Введіть назву теми/питання:", parent=self.master)
        if bookmark_name and bookmark_name.strip():
            self.bookmarks[bookmark_name.strip()] = self.current_page_num
            self.update_bookmark_combo_list()
            self.bookmark_combo.set(bookmark_name.strip())
            self.btn_remove_bookmark.config(state=tk.NORMAL)
        elif bookmark_name is not None:
            messagebox.showwarning("Помилка", "Назва закладки не може бути порожньою.", parent=self.master)

    def remove_bookmark(self):
        selected_bookmark = self.bookmark_combo.get()
        if selected_bookmark and selected_bookmark in self.bookmarks:
            if messagebox.askyesno("Видалити закладку", f"Видалити закладку '{selected_bookmark}'?",
                                   parent=self.master):
                del self.bookmarks[selected_bookmark]
                self.update_bookmark_combo_list()
                self.bookmark_combo.set('')
                if not self.bookmarks: self.btn_remove_bookmark.config(state=tk.DISABLED)
        elif selected_bookmark:
            messagebox.showwarning("Помилка", "Закладка не знайдена для видалення.", parent=self.master)

    def go_to_bookmark(self, event=None):
        selected_bookmark = self.bookmark_combo.get()
        if selected_bookmark in self.bookmarks:
            target_page = self.bookmarks[selected_bookmark]
            if 0 <= target_page < self.total_pages:
                self.current_page_num = target_page
                self.display_page()
                self.update_navigation_buttons()
            else:
                messagebox.showerror("Помилка", f"Некоректний номер сторінки: {target_page + 1}", parent=self.master)
        elif selected_bookmark:
            messagebox.showwarning("Помилка", f"Закладка '{selected_bookmark}' не знайдена.", parent=self.master)

    def update_bookmark_combo_list(self):
        sorted_bookmark_names = sorted(self.bookmarks.keys())
        self.bookmark_combo['values'] = sorted_bookmark_names
        if not sorted_bookmark_names:
            self.bookmark_combo.set('')
            self.btn_remove_bookmark.config(state=tk.DISABLED)
        elif self.bookmark_combo.get() not in sorted_bookmark_names:
            self.bookmark_combo.set('')

    def clear_bookmarks(self):
        self.bookmarks.clear()
        self.update_bookmark_combo_list()

    def perform_search(self, event=None):
        if not self.pdf_document: return
        self.search_term = self.search_entry.get()
        # print(f"\n--- Початок пошуку ---") # Менше логування за замовчуванням
        # print(f"Пошуковий запит: '{self.search_term}'")

        if not self.search_term.strip():
            self.clear_search_results()
            self.search_results_label.config(text="Введіть текст для пошуку")
            # print("--- Кінець пошуку (порожній запит) ---")
            return

        self.search_results_map.clear()
        self.flat_search_hits.clear()
        self.current_flat_match_idx = -1
        total_hits = 0
        search_flags = 1  # TEXT_SEARCH_CASE_INSENSITIVE (ігнорувати регістр)
        # search_flags = search_flags | 2 # TEXT_SEARCH_NORMALIZE_WHITESPACE (нормалізувати пробіли, якщо потрібно)
        # Якщо ви хочете обидва, то:
        # search_flags = 1 | 2
        for page_num in range(self.total_pages):
            page = self.pdf_document.load_page(page_num)
            hit_quads = page.search_for(self.search_term, quads=True, flags=search_flags)

            if hit_quads:
                # print(f"  Сторінка {page_num + 1}: знайдено {len(hit_quads)} квадів для '{self.search_term}'")
                page_rects = []
                for i, quad in enumerate(hit_quads):
                    rect = quad.rect
                    page_rects.append(rect)
                    self.flat_search_hits.append((page_num, i, rect))
                    # print(f"    Квад {i}: {quad}, Прямокутник: {rect}")
                self.search_results_map[page_num] = page_rects
                total_hits += len(hit_quads)

        self.search_results_label.config(text=f"Збігів: {total_hits}")
        # print(f"Загальна кількість збігів: {total_hits}")

        if total_hits > 0:
            self.btn_clear_search.config(state=tk.NORMAL)
            self.show_next_match(from_start=True)
        else:
            self.search_results_label.config(text="Збігів: 0 (Нічого не знайдено)")
            self.btn_clear_search.config(state=tk.DISABLED)
            self.update_search_nav_buttons_state()
            self.display_page()
        # print(f"--- Кінець пошуку ---")

    def show_next_match(self, from_start=False):
        if not self.flat_search_hits: return
        if from_start:
            self.current_flat_match_idx = 0
        else:
            self.current_flat_match_idx += 1
        if self.current_flat_match_idx >= len(self.flat_search_hits):
            self.current_flat_match_idx = 0
            messagebox.showinfo("Пошук", "Досягнуто кінця збігів, починаємо знову.", parent=self.master)
        self._navigate_to_current_match()

    def show_prev_match(self):
        if not self.flat_search_hits: return
        self.current_flat_match_idx -= 1
        if self.current_flat_match_idx < 0:
            self.current_flat_match_idx = len(self.flat_search_hits) - 1
            messagebox.showinfo("Пошук", "Досягнуто початку збігів, переходимо до останнього.", parent=self.master)
        self._navigate_to_current_match()

    def _navigate_to_current_match(self):
        if not (0 <= self.current_flat_match_idx < len(self.flat_search_hits)):
            self.update_search_nav_buttons_state()
            return
        page_num, _, _ = self.flat_search_hits[self.current_flat_match_idx]
        if self.current_page_num != page_num: self.current_page_num = page_num
        self.display_page()
        self.update_navigation_buttons()
        self.update_search_nav_buttons_state()

    def update_search_nav_buttons_state(self):
        num_hits = len(self.flat_search_hits)
        state = tk.NORMAL if num_hits > 0 else tk.DISABLED
        self.btn_next_match.config(state=state)
        self.btn_prev_match.config(state=state)

    def clear_search_results(self, event=None):
        self.search_term = ""
        self.search_results_map.clear()
        self.flat_search_hits.clear()
        self.current_flat_match_idx = -1
        self.search_results_label.config(text="Збігів: 0")
        self.search_entry.delete(0, tk.END)
        self.btn_clear_search.config(state=tk.DISABLED)
        self.update_search_nav_buttons_state()
        if self.pdf_document: self.display_page()

    def fit_page_to_canvas_and_set_default(self):
        if not self.pdf_document or self.total_pages == 0:
            calculated_zoom = 1.0
        else:
            page_to_fit = self.pdf_document.load_page(0)
            page_width_points = page_to_fit.rect.width
            page_height_points = page_to_fit.rect.height
            if page_width_points == 0 or page_height_points == 0:
                calculated_zoom = 1.0
            else:
                self.master.update_idletasks()
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                if canvas_width <= 1 or canvas_height <= 1:
                    self.right_pdf_panel.update_idletasks()
                    parent_width = self.right_pdf_panel.winfo_width()
                    parent_height = self.right_pdf_panel.winfo_height()
                    v_scroll_w = self.v_scrollbar.winfo_width() if self.v_scrollbar.winfo_exists() and self.v_scrollbar.winfo_ismapped() else 20
                    h_scroll_h = self.h_scrollbar.winfo_height() if self.h_scrollbar.winfo_exists() and self.h_scrollbar.winfo_ismapped() else 20
                    canvas_width = max(1, parent_width - v_scroll_w - 5)
                    canvas_height = max(1, parent_height - h_scroll_h - 5)
                padding_factor = 0.98
                zoom_x = (canvas_width * padding_factor) / page_width_points
                zoom_y = (canvas_height * padding_factor) / page_height_points
                calculated_zoom = min(zoom_x, zoom_y)
        self.current_zoom = max(self.min_zoom, min(calculated_zoom, self.max_zoom))
        self.default_zoom_for_file = self.current_zoom
        self.zoom_label.config(text=f"Масштаб: {int(self.current_zoom * 100)}%")

    def display_page(self):
        if not self.pdf_document or self.total_pages == 0:
            self.canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
            self.canvas.coords(self.image_on_canvas, 0, 0)
            self.canvas.config(scrollregion=(0, 0, 0, 0))
            return
        try:
            # print(f"\n--- Відображення сторінки {self.current_page_num + 1} ---")
            page = self.pdf_document.load_page(self.current_page_num)
            zoom_matrix = fitz.Matrix(self.current_zoom, self.current_zoom)
            # print(f"Матриця масштабування: {zoom_matrix}")

            pix = page.get_pixmap(matrix=zoom_matrix, alpha=False)
            # print(f"Розміри Pixmap: {pix.width}x{pix.height}")

            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")
            draw = ImageDraw.Draw(pil_image)

            # Підсвітка результатів пошуку
            if self.current_page_num in self.search_results_map:
                rects_on_this_page = self.search_results_map[self.current_page_num]
                # print(f"Сторінка {self.current_page_num + 1} (в display_page): знайдено {len(rects_on_this_page)} прямокутників для підсвітки.")

                current_match_page_num_from_flat_list = -1
                current_match_rect_idx_on_page_from_flat_list = -1

                if 0 <= self.current_flat_match_idx < len(self.flat_search_hits):
                    current_match_page_num_from_flat_list, current_match_rect_idx_on_page_from_flat_list, _ = \
                    self.flat_search_hits[self.current_flat_match_idx]

                for i, fitz_rect_original in enumerate(rects_on_this_page):
                    top_left_scaled = fitz_rect_original.tl * zoom_matrix
                    bottom_right_scaled = fitz_rect_original.br * zoom_matrix
                    x0, y0 = top_left_scaled.x, top_left_scaled.y
                    x1, y1 = bottom_right_scaled.x, bottom_right_scaled.y

                    if abs(x1 - x0) < 1 or abs(y1 - y0) < 1:
                        continue

                    is_current_active_match = (self.current_page_num == current_match_page_num_from_flat_list and
                                               i == current_match_rect_idx_on_page_from_flat_list)

                    outline_color = self.highlight_color_search_current_stroke if is_current_active_match else self.highlight_color_search_other_stroke
                    fill_color = self.highlight_color_search_current_fill if is_current_active_match else self.highlight_color_search_other_fill

                    draw.rectangle([x0, y0, x1, y1],
                                   outline=outline_color,
                                   fill=fill_color,
                                   width=self.highlight_stroke_width)

            self.tk_image = ImageTk.PhotoImage(pil_image.convert("RGB"))

            img_width, img_height = self.tk_image.width(), self.tk_image.height()
            self.master.update_idletasks()
            canvas_width, canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
            pos_x, pos_y = (canvas_width - img_width) / 2, (canvas_height - img_height) / 2
            self.canvas.itemconfig(self.image_on_canvas, image=self.tk_image)
            self.canvas.coords(self.image_on_canvas, pos_x, pos_y)
            self.master.update_idletasks()
            bbox = self.canvas.bbox(self.image_on_canvas)
            self.canvas.config(scrollregion=bbox if bbox else (0, 0, 0, 0))
            self.page_info_label.config(text=f"Сторінка: {self.current_page_num + 1} / {self.total_pages}")
            self.zoom_label.config(text=f"Масштаб: {int(self.current_zoom * 100)}%")
            # print(f"--- Кінець відображення сторінки {self.current_page_num + 1} ---")
        except Exception as e:
            # print(f"КРИТИЧНА ПОМИЛКА в display_page: {e}")
            # import traceback
            # traceback.print_exc()
            messagebox.showerror("Помилка відображення", f"Не вдалося відобразити сторінку: {e}", parent=self.master)
            self.canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
            self.canvas.coords(self.image_on_canvas, 0, 0)
            self.canvas.config(scrollregion=(0, 0, 0, 0))

    # --- Методи для виділення тексту лівою кнопкою ---
    def start_text_selection(self, event):
        if not self.pdf_document: return
        self.is_selecting_text = True
        self.selection_rect_start_x = self.canvas.canvasx(event.x)
        self.selection_rect_start_y = self.canvas.canvasy(event.y)

        if self.selection_rect_id:
            self.canvas.delete(self.selection_rect_id)

        self.selection_rect_id = self.canvas.create_rectangle(
            self.selection_rect_start_x, self.selection_rect_start_y,
            self.selection_rect_start_x, self.selection_rect_start_y,
            fill=self.selection_color_fill_hex,
            stipple="gray50",  # "gray12", "gray25", "gray50", "gray75"
            outline=self.selection_outline_color,
            width=1
        )

    def do_text_selection(self, event):
        if not self.pdf_document or not self.is_selecting_text: return
        current_x = self.canvas.canvasx(event.x)
        current_y = self.canvas.canvasy(event.y)
        if self.selection_rect_id:
            self.canvas.coords(self.selection_rect_id,
                               self.selection_rect_start_x, self.selection_rect_start_y,
                               current_x, current_y)

    def end_text_selection_and_copy(self, event):
        if not self.pdf_document or not self.is_selecting_text:
            if self.selection_rect_id:
                self.canvas.delete(self.selection_rect_id)
                self.selection_rect_id = None
            self.is_selecting_text = False
            return

        self.is_selecting_text = False
        final_x = self.canvas.canvasx(event.x)
        final_y = self.canvas.canvasy(event.y)

        if self.selection_rect_id:
            x0_canvas = min(self.selection_rect_start_x, final_x)
            y0_canvas = min(self.selection_rect_start_y, final_y)
            x1_canvas = max(self.selection_rect_start_x, final_x)
            y1_canvas = max(self.selection_rect_start_y, final_y)
            self.canvas.delete(self.selection_rect_id)
            self.selection_rect_id = None

            if abs(x1_canvas - x0_canvas) < 3 or abs(y1_canvas - y0_canvas) < 3:
                return

            if not self.tk_image: return
            img_bbox_on_canvas = self.canvas.bbox(self.image_on_canvas)
            if not img_bbox_on_canvas: return

            img_x_on_canvas = img_bbox_on_canvas[0]
            img_y_on_canvas = img_bbox_on_canvas[1]

            sel_x0_on_img = x0_canvas - img_x_on_canvas
            sel_y0_on_img = y0_canvas - img_y_on_canvas
            sel_x1_on_img = x1_canvas - img_x_on_canvas
            sel_y1_on_img = y1_canvas - img_y_on_canvas

            zoom_matrix = fitz.Matrix(self.current_zoom, self.current_zoom)
            try:
                inv_zoom_matrix = ~zoom_matrix
            except ZeroDivisionError:
                return

            pdf_p0 = fitz.Point(sel_x0_on_img, sel_y0_on_img) * inv_zoom_matrix
            pdf_p1 = fitz.Point(sel_x1_on_img, sel_y1_on_img) * inv_zoom_matrix
            selection_rect_pdf = fitz.Rect(pdf_p0, pdf_p1).normalize()  # нормалізуємо прямокутник

            try:
                page = self.pdf_document.load_page(self.current_page_num)
                selected_text = page.get_text("text", clip=selection_rect_pdf, sort=True)  # sort=True може допомогти

                if selected_text.strip():
                    pyperclip.copy(selected_text)
                    messagebox.showinfo("Копіювання", f"Виділений текст скопійовано.", parent=self.master)
            except pyperclip.PyperclipException as e_pyperclip:
                messagebox.showerror("Помилка копіювання", f"pyperclip не налаштований: {e_pyperclip}",
                                     parent=self.master)
            except Exception as e_text:
                messagebox.showerror("Помилка", "Не вдалося отримати текст з виділеної області.", parent=self.master)

    def prev_page(self):
        if self.pdf_document and self.current_page_num > 0:
            self.current_page_num -= 1
            self.display_page()
            self.update_navigation_buttons()

    def next_page(self):
        if self.pdf_document and self.current_page_num < self.total_pages - 1:
            self.current_page_num += 1
            self.display_page()
            self.update_navigation_buttons()

    def update_navigation_buttons(self):
        state = tk.NORMAL if self.pdf_document and self.total_pages > 0 else tk.DISABLED
        self.btn_prev.config(state=state if self.current_page_num > 0 else tk.DISABLED)
        self.btn_next.config(state=state if self.current_page_num < self.total_pages - 1 else tk.DISABLED)

    def zoom_in(self, event=None):
        if self.pdf_document and self.current_zoom < self.max_zoom:
            new_zoom = round(self.current_zoom + self.zoom_step, 2)
            self.current_zoom = min(new_zoom, self.max_zoom)
            self.display_page()
            self.update_all_zoom_buttons_state()

    def zoom_out(self, event=None):
        if self.pdf_document and self.current_zoom > self.min_zoom:
            new_zoom = round(self.current_zoom - self.zoom_step, 2)
            self.current_zoom = max(new_zoom, self.min_zoom)
            self.display_page()
            self.update_all_zoom_buttons_state()

    def reset_zoom_to_default(self, event=None):
        if self.pdf_document:
            self.current_zoom = self.default_zoom_for_file
            self.display_page()
            self.update_all_zoom_buttons_state()

    def update_all_zoom_buttons_state(self):
        if self.pdf_document:
            self.btn_zoom_in.config(
                state=tk.NORMAL if self.current_zoom < self.max_zoom - self.epsilon else tk.DISABLED)
            self.btn_zoom_out.config(
                state=tk.NORMAL if self.current_zoom > self.min_zoom + self.epsilon else tk.DISABLED)
            self.btn_reset_zoom.config(
                state=tk.NORMAL if abs(self.current_zoom - self.default_zoom_for_file) > self.epsilon else tk.DISABLED)
        else:
            self.btn_zoom_in.config(state=tk.DISABLED)
            self.btn_zoom_out.config(state=tk.DISABLED)
            self.btn_reset_zoom.config(state=tk.DISABLED)

    def clear_display(self):
        if self.pdf_document:
            try:
                self.pdf_document.close()
            except Exception:
                pass
        self.pdf_document = None
        self.total_pages = 0
        self.current_page_num = 0
        self.current_zoom = 1.0
        self.default_zoom_for_file = 1.0
        self.clear_bookmarks()
        self.clear_search_results()
        self.page_info_label.config(text="Сторінка: - / -")
        self.zoom_label.config(text=f"Масштаб: {int(self.current_zoom * 100)}%")
        if hasattr(self, 'tk_image') and self.tk_image:
            self.canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
        self.canvas.coords(self.image_on_canvas, 0, 0)
        self.canvas.config(scrollregion=(0, 0, 0, 0))
        self.update_navigation_buttons()
        self.update_all_zoom_buttons_state()
        self.btn_add_bookmark.config(state=tk.DISABLED)
        self.btn_remove_bookmark.config(state=tk.DISABLED)
        self.btn_search.config(state=tk.DISABLED)
        self.btn_clear_search.config(state=tk.DISABLED)
        self.update_search_nav_buttons_state()
        self.btn_copy_page_text.config(state=tk.DISABLED)

    def start_pan_right_btn(self, event):
        if not self.pdf_document: return
        # Якщо зараз відбувається виділення тексту, не починати панорамування
        if self.is_selecting_text: return
        self.canvas.config(cursor="fleur")
        self.canvas.scan_mark(event.x, event.y)
        self.is_panning_right_btn = True

    def do_pan_right_btn(self, event):
        if not self.pdf_document or not self.is_panning_right_btn: return
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def end_pan_right_btn(self, event):
        if not self.pdf_document: return  # or not self.is_panning_right_btn: # Цю перевірку можна прибрати, якщо cursor завжди скидається
        self.canvas.config(cursor="arrow")
        self.is_panning_right_btn = False

    def on_mouse_wheel(self, event):
        if not self.pdf_document: return
        # Запобігання масштабуванню під час виділення тексту
        if self.is_selecting_text: return
        if event.delta > 0:
            self.zoom_in()
        elif event.delta < 0:
            self.zoom_out()

    def on_mouse_wheel_linux(self, event):
        if not self.pdf_document: return
        if self.is_selecting_text: return
        if event.num == 4:
            self.zoom_in()
        elif event.num == 5:
            self.zoom_out()

    def on_closing(self):
        if self.pdf_document:
            try:
                self.pdf_document.close()
            except Exception as e:
                print(f"Помилка при закритті PDF: {e}")
        self.master.destroy()


if __name__ == "__main__":
    try:
        pyperclip.copy("test")
        pyperclip.paste()
    except pyperclip.PyperclipException as e:
        print(f"ПОПЕРЕДЖЕННЯ: pyperclip не налаштований належним чином для вашої системи.")
        print(f"Помилка: {e}")
    root = tk.Tk()
    app = PDFViewerApp(root)
    root.mainloop()