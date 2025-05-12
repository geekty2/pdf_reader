import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import fitz  # PyMuPDF
import pyperclip
import os  # Для os.path.basename

# Імпортуємо наші нові модулі
from .pdf_handler import PDFHandler
from .ui_manager import UIManager
from .bookmark_manager import BookmarkManager
from .search_manager import SearchManager


# from .event_handlers import EventHandlers # Якщо будемо використовувати

class PDFViewerApp:
    def __init__(self, master):
        self.master = master
        master.title("Розширений PDF Рідер (Модульний)")

        # ... (ініціалізація атрибутів стану) ...
        self.window_width = 1100
        self.window_height = 750
        self.tk_image = None
        self.current_page_num = 0
        self.current_zoom = 1.0
        self.default_zoom_for_file = 1.0
        self.zoom_step = 0.1
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.epsilon = 0.001
        self.is_panning_right_btn = False
        self.pan_start_x_right_btn = 0
        self.pan_start_y_right_btn = 0
        self.is_selecting_text = False
        self.selection_rect_start_x = 0
        self.selection_rect_start_y = 0
        self.selection_rect_id = None

        # Ініціалізація менеджерів - ЗМІНЕНО ПОРЯДОК
        self.pdf_handler = PDFHandler()
        self.bookmark_manager = BookmarkManager(self)  # Створюємо ДО UIManager
        self.search_manager = SearchManager(self)  # Створюємо ДО UIManager

        # Тепер створюємо UIManager, коли інші менеджери вже існують
        self.ui_manager = UIManager(master, self)
        # self.event_handler = EventHandlers(self) # Якщо будемо використовувати

        # Встановлюємо геометрію та resizable після створення UIManager
        master.geometry(f"{self.window_width}x{self.window_height}")
        master.resizable(False, False)

        # image_on_canvas тепер створюється в UIManager, але нам потрібне посилання
        self.image_on_canvas = self.ui_manager.canvas.create_image(0, 0, anchor=tk.NW)

        self._setup_event_bindings()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing_command)
        self.ui_manager.update_all_button_states()  # Початковий стан кнопок

    def _setup_event_bindings(self):
        """Налаштування прив'язок подій до віджетів (зокрема Canvas)."""
        canvas = self.ui_manager.canvas  # Отримуємо canvas від UIManager

        canvas.bind("<ButtonPress-3>", self.start_pan_right_btn_command)
        canvas.bind("<B3-Motion>", self.do_pan_right_btn_command)
        canvas.bind("<ButtonRelease-3>", self.end_pan_right_btn_command)

        # Використовуємо platform для обробки колеса миші
        # (Можна винести в EventHandlers)
        import platform
        if platform.system() == "Linux":
            canvas.bind("<Button-4>", self.on_mouse_wheel_command)
            canvas.bind("<Button-5>", self.on_mouse_wheel_command)
        else:
            canvas.bind("<MouseWheel>", self.on_mouse_wheel_command)

        canvas.bind("<ButtonPress-1>", self.start_text_selection_command)
        canvas.bind("<B1-Motion>", self.do_text_selection_command)
        canvas.bind("<ButtonRelease-1>", self.end_text_selection_and_copy_command)

    # --- Команди, що викликаються з UI (методи-обгортки) ---
    def open_pdf_command(self):
        filepath = filedialog.askopenfilename(
            title="Виберіть PDF файл", filetypes=(("PDF файли", "*.pdf"), ("Всі файли", "*.*"))
        )
        if not filepath: return

        # Спочатку очищаємо стан попереднього документа
        self.clear_all_state_before_open()

        if self.pdf_handler.open_pdf_file(filepath):
            # Перевірка текстового шару
            has_text, msg = self.pdf_handler.check_text_layer(0)
            if not has_text:
                messagebox.showwarning("Інформація про PDF", msg, parent=self.master)

            self.current_page_num = 0
            self.master.title(f"PDF Рідер - {os.path.basename(filepath)}")
            self.fit_page_to_canvas_and_set_default()  # Розрахунок масштабу
            self.display_page()  # Відображення першої сторінки
        else:
            messagebox.showerror("Помилка", f"Не вдалося відкрити PDF файл: {filepath}", parent=self.master)

        self.ui_manager.update_all_button_states()

    def copy_current_page_text_command(self):
        if not self.pdf_handler.pdf_document: return
        try:
            text = self.pdf_handler.get_page_text(self.current_page_num)
            pyperclip.copy(text)
            messagebox.showinfo("Копіювання", "Текст поточної сторінки скопійовано.", parent=self.master)
        except pyperclip.PyperclipException as e:
            messagebox.showerror("Помилка копіювання", f"pyperclip не налаштований: {e}", parent=self.master)
        except Exception as e:
            messagebox.showerror("Помилка копіювання", f"Не вдалося скопіювати текст: {e}", parent=self.master)

    def prev_page_command(self):
        if self.pdf_handler.pdf_document and self.current_page_num > 0:
            self.current_page_num -= 1
            self.display_page()
            self.ui_manager.update_navigation_buttons_state()

    def next_page_command(self):
        if self.pdf_handler.pdf_document and self.current_page_num < self.pdf_handler.total_pages - 1:
            self.current_page_num += 1
            self.display_page()
            self.ui_manager.update_navigation_buttons_state()

    def perform_search_command(self, event=None):  # event для прив'язки Enter
        search_term = self.ui_manager.search_entry.get()
        self.search_manager.perform_search(search_term)

    def clear_search_results_command(self):
        self.search_manager.clear_search_results(update_ui=True)

    def zoom_in_command(self, event=None):
        if self.pdf_handler.pdf_document and self.current_zoom < self.max_zoom:
            new_zoom = round(self.current_zoom + self.zoom_step, 2)
            self.current_zoom = min(new_zoom, self.max_zoom)
            self.display_page()
            self.ui_manager.update_zoom_buttons_state()

    def zoom_out_command(self, event=None):
        if self.pdf_handler.pdf_document and self.current_zoom > self.min_zoom:
            new_zoom = round(self.current_zoom - self.zoom_step, 2)
            self.current_zoom = max(new_zoom, self.min_zoom)
            self.display_page()
            self.ui_manager.update_zoom_buttons_state()

    def reset_zoom_to_default_command(self, event=None):
        if self.pdf_handler.pdf_document:
            self.current_zoom = self.default_zoom_for_file
            self.display_page()
            self.ui_manager.update_zoom_buttons_state()

    # --- Логіка відображення та розрахунків ---
    def fit_page_to_canvas_and_set_default(self):
        if not self.pdf_handler.pdf_document or self.pdf_handler.total_pages == 0:
            calculated_zoom = 1.0
        else:
            page_to_fit = self.pdf_handler.get_page(0)  # Використовуємо pdf_handler
            if not page_to_fit:
                calculated_zoom = 1.0
            else:
                page_width_points = page_to_fit.rect.width
                page_height_points = page_to_fit.rect.height
                if page_width_points == 0 or page_height_points == 0:
                    calculated_zoom = 1.0
                else:
                    self.master.update_idletasks()
                    canvas = self.ui_manager.canvas
                    canvas_width = canvas.winfo_width()
                    canvas_height = canvas.winfo_height()

                    if canvas_width <= 1 or canvas_height <= 1:  # Запасний варіант
                        self.ui_manager.right_pdf_panel.update_idletasks()
                        parent_width = self.ui_manager.right_pdf_panel.winfo_width()
                        parent_height = self.ui_manager.right_pdf_panel.winfo_height()
                        v_scroll_w = self.ui_manager.v_scrollbar.winfo_width() if self.ui_manager.v_scrollbar.winfo_exists() and self.ui_manager.v_scrollbar.winfo_ismapped() else 20
                        h_scroll_h = self.ui_manager.h_scrollbar.winfo_height() if self.ui_manager.h_scrollbar.winfo_exists() and self.ui_manager.h_scrollbar.winfo_ismapped() else 20
                        canvas_width = max(1, parent_width - v_scroll_w - 5)
                        canvas_height = max(1, parent_height - h_scroll_h - 5)

                    padding_factor = 0.98
                    zoom_x = (canvas_width * padding_factor) / page_width_points
                    zoom_y = (canvas_height * padding_factor) / page_height_points
                    calculated_zoom = min(zoom_x, zoom_y)

        self.current_zoom = max(self.min_zoom, min(calculated_zoom, self.max_zoom))
        self.default_zoom_for_file = self.current_zoom
        # Оновлення мітки масштабу тепер робить UIManager
        if hasattr(self, 'ui_manager') and self.ui_manager:
            self.ui_manager.update_zoom_buttons_state()

    def display_page(self):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document or self.pdf_handler.total_pages == 0:
            canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
            canvas.coords(self.image_on_canvas, 0, 0)
            canvas.config(scrollregion=(0, 0, 0, 0))
            self.ui_manager.update_navigation_buttons_state()  # Оновити інфо про сторінку
            return
        try:
            zoom_matrix = fitz.Matrix(self.current_zoom, self.current_zoom)
            pix = self.pdf_handler.get_page_pixmap(self.current_page_num, zoom_matrix)

            if not pix:
                raise ValueError("Не вдалося отримати Pixmap для сторінки.")

            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")
            draw = ImageDraw.Draw(pil_image)

            # Підсвітка результатів пошуку
            search_map = self.search_manager.search_results_map
            if self.current_page_num in search_map:
                rects_on_this_page = search_map[self.current_page_num]
                current_match_page_num = -1
                current_match_idx_on_page = -1

                if 0 <= self.search_manager.current_flat_match_idx < len(self.search_manager.flat_search_hits):
                    current_match_page_num, current_match_idx_on_page, _ = self.search_manager.flat_search_hits[
                        self.search_manager.current_flat_match_idx]

                for i, fitz_rect_original in enumerate(rects_on_this_page):
                    top_left_scaled = fitz_rect_original.tl * zoom_matrix
                    bottom_right_scaled = fitz_rect_original.br * zoom_matrix
                    x0, y0 = top_left_scaled.x, top_left_scaled.y
                    x1, y1 = bottom_right_scaled.x, bottom_right_scaled.y

                    if abs(x1 - x0) < 1 or abs(y1 - y0) < 1: continue

                    is_current = (self.current_page_num == current_match_page_num and
                                  i == current_match_idx_on_page)

                    o_color = self.ui_manager.highlight_color_search_current_stroke if is_current else self.ui_manager.highlight_color_search_other_stroke
                    f_color = self.ui_manager.highlight_color_search_current_fill if is_current else self.ui_manager.highlight_color_search_other_fill

                    draw.rectangle([x0, y0, x1, y1],
                                   outline=o_color, fill=f_color,
                                   width=self.ui_manager.highlight_stroke_width)

            self.tk_image = ImageTk.PhotoImage(pil_image.convert("RGB"))

            img_width, img_height = self.tk_image.width(), self.tk_image.height()
            self.master.update_idletasks()
            canvas_width, canvas_height = canvas.winfo_width(), canvas.winfo_height()
            pos_x, pos_y = (canvas_width - img_width) / 2, (canvas_height - img_height) / 2

            canvas.itemconfig(self.image_on_canvas, image=self.tk_image)
            canvas.coords(self.image_on_canvas, pos_x, pos_y)
            self.master.update_idletasks()
            bbox = canvas.bbox(self.image_on_canvas)
            canvas.config(scrollregion=bbox if bbox else (0, 0, 0, 0))

            # Оновлення міток через UIManager
            self.ui_manager.update_navigation_buttons_state()
            self.ui_manager.update_zoom_buttons_state()

        except Exception as e:
            messagebox.showerror("Помилка відображення", f"Не вдалося відобразити сторінку: {e}", parent=self.master)
            # Скидання Canvas
            canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
            canvas.coords(self.image_on_canvas, 0, 0)
            canvas.config(scrollregion=(0, 0, 0, 0))

    # --- Обробники подій миші (передають керування або виконують дію) ---
    def start_pan_right_btn_command(self, event):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document: return
        if self.is_selecting_text: return
        canvas.config(cursor="fleur")
        canvas.scan_mark(event.x, event.y)
        self.is_panning_right_btn = True

    def do_pan_right_btn_command(self, event):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document or not self.is_panning_right_btn: return
        canvas.scan_dragto(event.x, event.y, gain=1)

    def end_pan_right_btn_command(self, event):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document: return
        canvas.config(cursor="arrow")
        self.is_panning_right_btn = False

    def on_mouse_wheel_command(self, event):
        if not self.pdf_handler.pdf_document: return
        if self.is_selecting_text: return

        # Для Linux delta немає, є event.num
        delta = 0
        if platform.system() == "Linux":
            if event.num == 4:
                delta = 120  # Умовна прокрутка вгору
            elif event.num == 5:
                delta = -120  # Умовна прокрутка вниз
        else:
            delta = event.delta

        if delta > 0:
            self.zoom_in_command()
        elif delta < 0:
            self.zoom_out_command()

    def start_text_selection_command(self, event):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document: return
        self.is_selecting_text = True
        self.selection_rect_start_x = canvas.canvasx(event.x)
        self.selection_rect_start_y = canvas.canvasy(event.y)

        if self.selection_rect_id:
            canvas.delete(self.selection_rect_id)

        self.selection_rect_id = canvas.create_rectangle(
            self.selection_rect_start_x, self.selection_rect_start_y,
            self.selection_rect_start_x, self.selection_rect_start_y,
            fill=self.ui_manager.selection_color_fill_hex,
            stipple="gray50",
            outline=self.ui_manager.selection_outline_color,
            width=1
        )

    def do_text_selection_command(self, event):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document or not self.is_selecting_text: return
        current_x = canvas.canvasx(event.x)
        current_y = canvas.canvasy(event.y)
        if self.selection_rect_id:
            canvas.coords(self.selection_rect_id,
                          self.selection_rect_start_x, self.selection_rect_start_y,
                          current_x, current_y)

    def end_text_selection_and_copy_command(self, event):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document or not self.is_selecting_text:
            if self.selection_rect_id:
                canvas.delete(self.selection_rect_id)
                self.selection_rect_id = None
            self.is_selecting_text = False
            return

        self.is_selecting_text = False
        final_x = canvas.canvasx(event.x)
        final_y = canvas.canvasy(event.y)

        if self.selection_rect_id:
            x0_canvas = min(self.selection_rect_start_x, final_x)
            y0_canvas = min(self.selection_rect_start_y, final_y)
            x1_canvas = max(self.selection_rect_start_x, final_x)
            y1_canvas = max(self.selection_rect_start_y, final_y)
            canvas.delete(self.selection_rect_id)
            self.selection_rect_id = None

            if abs(x1_canvas - x0_canvas) < 3 or abs(y1_canvas - y0_canvas) < 3: return
            if not self.tk_image: return

            img_bbox_on_canvas = canvas.bbox(self.image_on_canvas)
            if not img_bbox_on_canvas: return

            img_x_on_canvas, img_y_on_canvas = img_bbox_on_canvas[0], img_bbox_on_canvas[1]
            sel_x0_img, sel_y0_img = x0_canvas - img_x_on_canvas, y0_canvas - img_y_on_canvas
            sel_x1_img, sel_y1_img = x1_canvas - img_x_on_canvas, y1_canvas - img_y_on_canvas

            zoom_matrix = fitz.Matrix(self.current_zoom, self.current_zoom)
            try:
                inv_zoom_matrix = ~zoom_matrix
            except ZeroDivisionError:
                return

            pdf_p0 = fitz.Point(sel_x0_img, sel_y0_img) * inv_zoom_matrix
            pdf_p1 = fitz.Point(sel_x1_img, sel_y1_img) * inv_zoom_matrix
            selection_rect_pdf = fitz.Rect(pdf_p0, pdf_p1).normalize()

            try:
                page = self.pdf_handler.get_page(self.current_page_num)
                if not page: return
                selected_text = page.get_text("text", clip=selection_rect_pdf, sort=True)

                if selected_text.strip():
                    pyperclip.copy(selected_text)
                    messagebox.showinfo("Копіювання", f"Виділений текст скопійовано.", parent=self.master)
            except pyperclip.PyperclipException as e_pyperclip:
                messagebox.showerror("Помилка копіювання", f"pyperclip не налаштований: {e_pyperclip}",
                                     parent=self.master)
            except Exception as e_text:
                messagebox.showerror("Помилка", "Не вдалося отримати текст з виділеної області.", parent=self.master)

    # --- Очищення та закриття ---
    def clear_all_state_before_open(self):
        """Скидає стан перед відкриттям нового PDF."""
        self.pdf_handler.close_pdf()  # Закриває попередній документ
        self.current_page_num = 0
        self.current_zoom = 1.0  # Скидання масштабу до дефолтного
        self.default_zoom_for_file = 1.0

        self.bookmark_manager.clear_bookmarks()
        self.search_manager.clear_search_results(update_ui=False)  # UI оновиться пізніше

        # Очищення Canvas
        canvas = self.ui_manager.canvas
        if hasattr(self, 'tk_image') and self.tk_image:
            canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
        canvas.coords(self.image_on_canvas, 0, 0)
        canvas.config(scrollregion=(0, 0, 0, 0))
        # Початковий стан UI буде встановлено після відкриття або в open_pdf

    def on_closing_command(self):
        self.pdf_handler.close_pdf()
        self.master.destroy()