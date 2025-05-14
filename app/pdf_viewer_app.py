import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import fitz
import pyperclip
import os
import platform
import pytesseract
import subprocess
import threading
import queue
import shlex
import sys

from .pdf_handler import PDFHandler
from .ui_manager import UIManager
from .bookmark_manager import BookmarkManager
from .search_manager import SearchManager


class PDFViewerApp:
    def __init__(self, master):

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Якщо програма "заморожена" PyInstaller
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Два os.path.dirname, щоб вийти з app/
        self.lectures_dir = os.path.join(self.base_path, "lectures")  # Повний шлях до папки лекцій
        self.lectures_files = []
        self.master = master
        master.title("Розширений PDF Рідер (Модульний + Термінал + Нові Закладки)")

        self.window_width = 1100
        self.base_ui_height = 580  # Висота для верхньої частини (PDF + ліва панель)
        self.terminal_ui_height = 200  # Висота терміналу з UIManager

        self.tk_image = None
        self.current_pil_image_for_ocr_selection = None
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

        self.current_working_directory = os.getcwd()
        self.command_queue = queue.Queue()

        self.lectures_dir = "lectures"
        self.lectures_files = []

        self.pdf_handler = PDFHandler()
        self.bookmark_manager = BookmarkManager(self)
        self.search_manager = SearchManager(self)
        self.ui_manager = UIManager(master, self)

        total_window_height = self.base_ui_height + self.terminal_ui_height + 20
        master.geometry(f"{self.window_width}x{total_window_height}")
        master.resizable(True, True)  # Дозволяємо змінювати розмір

        self.image_on_canvas = self.ui_manager.canvas.create_image(0, 0, anchor=tk.NW)

        self._setup_event_bindings()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing_command)

        self._update_terminal_cwd_ui()
        self._check_command_queue()
        self.refresh_lectures_list_command()  # Завантажуємо список лекцій
        self.ui_manager.update_all_button_states()

    def _setup_event_bindings(self):
        canvas = self.ui_manager.canvas
        canvas.bind("<ButtonPress-3>", self.start_pan_right_btn_command)
        canvas.bind("<B3-Motion>", self.do_pan_right_btn_command)
        canvas.bind("<ButtonRelease-3>", self.end_pan_right_btn_command)

        if platform.system() == "Linux":
            canvas.bind("<Button-4>", self.on_mouse_wheel_command)
            canvas.bind("<Button-5>", self.on_mouse_wheel_command)
        else:
            canvas.bind("<MouseWheel>", self.on_mouse_wheel_command)

        canvas.bind("<ButtonPress-1>", self.start_text_selection_command)
        canvas.bind("<B1-Motion>", self.do_text_selection_command)
        canvas.bind("<ButtonRelease-1>", self.end_text_selection_and_action_command)

    def _update_terminal_cwd_ui(self):
        if hasattr(self, 'ui_manager') and self.ui_manager:
            self.ui_manager.update_terminal_cwd_label(self.current_working_directory)

    def execute_terminal_command_command(self, event=None, command_to_execute=None):
        if command_to_execute is None:
            command = self.ui_manager.terminal_input_entry.get()
            self.ui_manager.terminal_input_entry.delete(0, tk.END)
        else:
            command = command_to_execute
            self.ui_manager.terminal_input_entry.delete(0, tk.END)
            self.ui_manager.terminal_input_entry.insert(0, command)
            # Ми не виконуємо команду автоматично, користувач натисне Enter
            # Якщо потрібно автоматично, розкоментуйте наступне і приберіть 'return'
            # self.ui_manager.append_to_terminal(f"{self.current_working_directory}> {command}\n", "command")
            # # Далі логіка запуску... (повтор з нижньої гілки)
            return

        if not command.strip():
            return

        self.ui_manager.append_to_terminal(f"{self.current_working_directory}> {command}\n", "command")

        if command.strip().lower().startswith("cd "):
            try:
                new_dir_part = command.strip()[3:].strip()
                if not new_dir_part:
                    if platform.system() == "Windows":
                        self.ui_manager.append_to_terminal(f"{self.current_working_directory}\n", "output")
                        return
                    else:
                        new_dir_part = os.path.expanduser("~")

                if not os.path.isabs(new_dir_part):
                    new_dir = os.path.abspath(os.path.join(self.current_working_directory, new_dir_part))
                else:
                    new_dir = new_dir_part

                os.chdir(new_dir)
                self.current_working_directory = os.getcwd()
                self.ui_manager.append_to_terminal(f"Нова директорія: {self.current_working_directory}\n", "info")
                self._update_terminal_cwd_ui()
            except FileNotFoundError:
                self.ui_manager.append_to_terminal(f"Помилка: Директорію не знайдено: {new_dir_part}\n", "error")
            except Exception as e:
                self.ui_manager.append_to_terminal(f"Помилка cd: {e}\n", "error")
        elif command.strip().lower() == "exit":
            self.ui_manager.append_to_terminal("Завершення роботи імітації терміналу (команда exit)...\n", "info")
        else:
            thread = threading.Thread(target=self._run_command_in_thread, args=(command,))
            thread.daemon = True
            thread.start()

    def _run_command_in_thread(self, command_str):
        try:
            if platform.system() == "Windows":
                process = subprocess.Popen(f'cmd /c "{command_str}"',
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           text=False,
                                           cwd=self.current_working_directory,
                                           creationflags=subprocess.CREATE_NO_WINDOW,
                                           shell=False)

                console_encoding = 'cp1251'
                try:
                    import locale
                    console_encoding = locale.getpreferredencoding(False)
                except:
                    pass

                for line_bytes in iter(process.stdout.readline, b''):
                    try:
                        line = line_bytes.decode(console_encoding, errors='replace')
                        self.command_queue.put(line)
                    except Exception as dec_err:
                        self.command_queue.put(f"[Decoding Error: {dec_err}] {line_bytes[:50]}...\n")
            else:
                args = shlex.split(command_str)
                process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           text=True, cwd=self.current_working_directory,
                                           encoding='utf-8', errors='replace')
                for line in iter(process.stdout.readline, ''):
                    self.command_queue.put(line)

            process.stdout.close()
            return_code = process.wait()
            if return_code != 0:
                self.command_queue.put(f"\nПроцес завершився з кодом: {return_code}\n")
        except FileNotFoundError:
            self.command_queue.put(f"Помилка: Команду або програму не знайдено: '{command_str.split()[0]}'\n")
        except Exception as e:
            self.command_queue.put(f"Помилка виконання команди '{command_str}': {e}\n")

    def _check_command_queue(self):
        try:
            while True:
                line = self.command_queue.get_nowait()
                tag = "output"
                line_lower = line.lower()
                if "помилка" in line_lower or "error" in line_lower or "не знайдено" in line_lower or "failed" in line_lower:
                    tag = "error"
                elif " попередження" in line_lower or "warning" in line_lower:
                    tag = "info"
                self.ui_manager.append_to_terminal(line, tag)
        except queue.Empty:
            pass
        finally:
            self.master.after(100, self._check_command_queue)

    def open_pdf_dialog_command(self):  # Перейменовано, щоб відрізняти від відкриття лекції
        filepath = filedialog.askopenfilename(
            title="Виберіть PDF файл", filetypes=(("PDF файли", "*.pdf"), ("Всі файли", "*.*"))
        )
        if filepath:
            self._open_pdf_internal(filepath)

    def _get_lectures_from_dir(self):
        if not os.path.exists(self.lectures_dir):
            try:
                os.makedirs(self.lectures_dir)
                messagebox.showinfo("Папка лекцій",
                                    f"Створено папку '{self.lectures_dir}'.\n"
                                    "Покладіть ваші PDF лекції туди та натисніть 'Оновити список'.",
                                    parent=self.master)
            except Exception as e:
                messagebox.showerror("Помилка створення папки",
                                     f"Не вдалося створити папку '{self.lectures_dir}':\n{e}", parent=self.master)
            return []

        pdf_files = []
        try:
            for item in os.listdir(self.lectures_dir):
                if item.lower().endswith(".pdf"):
                    pdf_files.append(item)
        except Exception as e:
            messagebox.showerror("Помилка читання лекцій",
                                 f"Не вдалося прочитати вміст папки '{self.lectures_dir}':\n{e}", parent=self.master)
        return pdf_files

    def refresh_lectures_list_command(self):
        self.lectures_files = self._get_lectures_from_dir()
        self.ui_manager.populate_lectures_treeview(self.lectures_files)

    def open_selected_lecture_command(self, event=None):
        if not self.ui_manager.lectures_treeview: return
        selected_item_id = self.ui_manager.lectures_treeview.focus()
        if not selected_item_id: return

        item_details = self.ui_manager.lectures_treeview.item(selected_item_id)
        if not item_details or not item_details.get('values'): return

        filename = item_details['values'][0]
        filepath = os.path.join(self.lectures_dir, filename)

        if os.path.exists(filepath):
            self._open_pdf_internal(filepath, is_lecture=True, lecture_filename=filename)
        else:
            messagebox.showerror("Помилка", f"Файл лекції не знайдено: {filepath}", parent=self.master)
            self.refresh_lectures_list_command()

    def _open_pdf_internal(self, filepath, is_lecture=False, lecture_filename=None):
        """Внутрішній метод для відкриття PDF, викликається з діалогу або зі списку лекцій."""
        self.clear_all_state_before_open()
        if self.pdf_handler.open_pdf_file(filepath):
            has_text, msg = self.pdf_handler.check_text_layer(0, ocr_fallback=True, ocr_lang='ukr+eng')
            if "ПОМИЛКА: Tesseract не знайдено" in msg:
                messagebox.showerror("Помилка Tesseract", msg, parent=self.master)
            elif "Помилка OCR" in msg:
                messagebox.showwarning("Інформація про OCR", msg, parent=self.master)
            elif not has_text:
                messagebox.showwarning("Інформація про PDF", msg, parent=self.master)

            self.current_page_num = 0
            display_filename = lecture_filename if is_lecture else os.path.basename(filepath)
            self.master.title(f"PDF Рідер - {display_filename}")
            self.fit_page_to_canvas_and_set_default()
            self.display_page()
        else:
            messagebox.showerror("Помилка", f"Не вдалося відкрити PDF файл: {filepath}", parent=self.master)
        self.ui_manager.update_all_button_states()

    def copy_current_page_text_command(self):
        if not self.pdf_handler.pdf_document: return
        try:
            text = self.pdf_handler.get_page_text(self.current_page_num, use_ocr_if_needed=True, ocr_lang='ukr+eng')
            if "ПОМИЛКА_OCR" in text:
                messagebox.showerror("Помилка OCR", f"Не вдалося розпізнати текст: {text.replace('ПОМИЛКА_OCR_', '')}",
                                     parent=self.master)
                return
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

    def perform_search_command(self, event=None):
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

    def fit_page_to_canvas_and_set_default(self):
        if not self.pdf_handler.pdf_document or self.pdf_handler.total_pages == 0:
            calculated_zoom = 1.0
        else:
            page_to_fit = self.pdf_handler.get_page(0)
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

                    if canvas_width <= 1 or canvas_height <= 1:
                        self.ui_manager.right_pdf_panel.update_idletasks()
                        approx_pdf_display_width = self.master.winfo_width() - self.ui_manager.left_controls_panel.winfo_width() - 20
                        v_scroll_w = self.ui_manager.v_scrollbar.winfo_width() if self.ui_manager.v_scrollbar.winfo_exists() and self.ui_manager.v_scrollbar.winfo_ismapped() else 20
                        h_scroll_h = self.ui_manager.h_scrollbar_canvas.winfo_height() if self.ui_manager.h_scrollbar_canvas.winfo_exists() and self.ui_manager.h_scrollbar_canvas.winfo_ismapped() else 20
                        canvas_width = max(1, approx_pdf_display_width - v_scroll_w - 5)
                        canvas_height = max(1, self.base_ui_height - h_scroll_h - 5)

                    padding_factor = 0.98
                    zoom_x = (canvas_width * padding_factor) / page_width_points
                    zoom_y = (canvas_height * padding_factor) / page_height_points
                    calculated_zoom = min(zoom_x, zoom_y)

        self.current_zoom = max(self.min_zoom, min(calculated_zoom, self.max_zoom))
        self.default_zoom_for_file = self.current_zoom
        if hasattr(self, 'ui_manager') and self.ui_manager:
            self.ui_manager.update_zoom_buttons_state()

    def display_page(self):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document or self.pdf_handler.total_pages == 0:
            canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
            self.current_pil_image_for_ocr_selection = None
            canvas.coords(self.image_on_canvas, 0, 0)
            canvas.config(scrollregion=(0, 0, 0, 0))
            self.ui_manager.update_navigation_buttons_state()
            return
        try:
            zoom_matrix = fitz.Matrix(self.current_zoom, self.current_zoom)
            pix = self.pdf_handler.get_page_pixmap(self.current_page_num, zoom_matrix)

            if not pix:
                self.current_pil_image_for_ocr_selection = None
                raise ValueError("Не вдалося отримати Pixmap для сторінки.")

            self.current_pil_image_for_ocr_selection = Image.frombytes(
                "RGB", [pix.width, pix.height], pix.samples
            ).convert("RGBA")

            pil_image_for_display = self.current_pil_image_for_ocr_selection.copy()
            draw = ImageDraw.Draw(pil_image_for_display)

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

            self.tk_image = ImageTk.PhotoImage(pil_image_for_display.convert("RGB"))

            img_width, img_height = self.tk_image.width(), self.tk_image.height()
            self.master.update_idletasks()
            canvas_width, canvas_height = canvas.winfo_width(), canvas.winfo_height()
            pos_x, pos_y = (canvas_width - img_width) / 2, (canvas_height - img_height) / 2

            canvas.itemconfig(self.image_on_canvas, image=self.tk_image)
            canvas.coords(self.image_on_canvas, pos_x, pos_y)
            self.master.update_idletasks()
            bbox = canvas.bbox(self.image_on_canvas)
            canvas.config(scrollregion=bbox if bbox else (0, 0, 0, 0))

            self.ui_manager.update_navigation_buttons_state()
            self.ui_manager.update_zoom_buttons_state()

        except Exception as e:
            self.current_pil_image_for_ocr_selection = None
            messagebox.showerror("Помилка відображення", f"Не вдалося відобразити сторінку: {e}", parent=self.master)
            # import traceback # Для детальної діагностики
            # traceback.print_exc()
            canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
            canvas.coords(self.image_on_canvas, 0, 0)
            canvas.config(scrollregion=(0, 0, 0, 0))

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

        delta = 0
        if platform.system() == "Linux":
            if event.num == 4:
                delta = 120
            elif event.num == 5:
                delta = -120
        else:
            delta = event.delta

        if delta > 0:
            self.zoom_in_command()
        elif delta < 0:
            self.zoom_out_command()

    def start_text_selection_command(self, event):
        canvas = self.ui_manager.canvas
        if not self.pdf_handler.pdf_document: return
        if not self.current_pil_image_for_ocr_selection and not self.bookmark_manager.is_adding_bookmark_mode:
            return

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

    def end_text_selection_and_action_command(self, event):
        canvas = self.ui_manager.canvas
        is_adding_bookmark_now = hasattr(self.bookmark_manager,
                                         'is_adding_bookmark_mode') and self.bookmark_manager.is_adding_bookmark_mode

        if not self.pdf_handler.pdf_document or not self.is_selecting_text:
            if self.selection_rect_id:
                canvas.delete(self.selection_rect_id)
                self.selection_rect_id = None
            self.is_selecting_text = False
            if is_adding_bookmark_now:
                self.bookmark_manager.is_adding_bookmark_mode = False
                self.ui_manager.update_status_bar("")
            return

        self.is_selecting_text = False
        final_x_canvas = canvas.canvasx(event.x)
        final_y_canvas = canvas.canvasy(event.y)

        if self.selection_rect_id:
            canvas.delete(self.selection_rect_id)
            self.selection_rect_id = None

        x0_canvas = min(self.selection_rect_start_x, final_x_canvas)
        y0_canvas = min(self.selection_rect_start_y, final_y_canvas)
        x1_canvas = max(self.selection_rect_start_x, final_x_canvas)
        y1_canvas = max(self.selection_rect_start_y, final_y_canvas)

        if abs(x1_canvas - x0_canvas) < 5 or abs(y1_canvas - y0_canvas) < 5:
            if is_adding_bookmark_now:
                self.bookmark_manager.is_adding_bookmark_mode = False
                self.ui_manager.update_status_bar("")
                messagebox.showwarning("Додавання закладки", "Виділення занадто мале.", parent=self.master)
            return

        if not self.current_pil_image_for_ocr_selection:
            if is_adding_bookmark_now:
                self.bookmark_manager.is_adding_bookmark_mode = False
                self.ui_manager.update_status_bar("Немає зображення для OCR.")
            return

        img_bbox_on_canvas = canvas.bbox(self.image_on_canvas)
        if not img_bbox_on_canvas:
            if is_adding_bookmark_now:
                self.bookmark_manager.is_adding_bookmark_mode = False
                self.ui_manager.update_status_bar("")
            return

        img_offset_x_on_canvas, img_offset_y_on_canvas = img_bbox_on_canvas[0], img_bbox_on_canvas[1]
        sel_x0_on_displayed_img = int(x0_canvas - img_offset_x_on_canvas)
        sel_y0_on_displayed_img = int(y0_canvas - img_offset_y_on_canvas)
        sel_x1_on_displayed_img = int(x1_canvas - img_offset_x_on_canvas)
        sel_y1_on_displayed_img = int(y1_canvas - img_offset_y_on_canvas)

        pil_w = self.current_pil_image_for_ocr_selection.width
        pil_h = self.current_pil_image_for_ocr_selection.height
        sel_x0_on_displayed_img = max(0, sel_x0_on_displayed_img)
        sel_y0_on_displayed_img = max(0, sel_y0_on_displayed_img)
        sel_x1_on_displayed_img = min(pil_w, sel_x1_on_displayed_img)
        sel_y1_on_displayed_img = min(pil_h, sel_y1_on_displayed_img)

        if sel_x1_on_displayed_img <= sel_x0_on_displayed_img or \
                sel_y1_on_displayed_img <= sel_y0_on_displayed_img:
            if is_adding_bookmark_now:
                self.bookmark_manager.is_adding_bookmark_mode = False
                self.ui_manager.update_status_bar("Помилка виділення для OCR.")
            return

        selected_text_content = ""
        try:
            selected_pil_region = self.current_pil_image_for_ocr_selection.crop(
                (sel_x0_on_displayed_img, sel_y0_on_displayed_img,
                 sel_x1_on_displayed_img, sel_y1_on_displayed_img)
            )
            selected_text_content = pytesseract.image_to_string(selected_pil_region, lang='ukr+eng')
        except pytesseract.TesseractNotFoundError:
            messagebox.showerror("Помилка Tesseract", "Tesseract OCR не знайдено.", parent=self.master)
            if is_adding_bookmark_now: self.bookmark_manager.is_adding_bookmark_mode = False; self.ui_manager.update_status_bar(
                "")
            return
        except Exception as e_ocr:
            messagebox.showerror("Помилка OCR", f"Помилка під час OCR: {e_ocr}", parent=self.master)
            if is_adding_bookmark_now: self.bookmark_manager.is_adding_bookmark_mode = False; self.ui_manager.update_status_bar(
                "")
            return

        if is_adding_bookmark_now:
            self.bookmark_manager.finalize_add_bookmark(selected_text_content)
        else:
            if selected_text_content.strip():
                try:
                    pyperclip.copy(selected_text_content)
                    messagebox.showinfo("OCR Копіювання",
                                        f"Розпізнаний текст скопійовано.",
                                        parent=self.master)
                except pyperclip.PyperclipException as e_pyperclip:
                    messagebox.showerror("Помилка копіювання", f"pyperclip не налаштований: {e_pyperclip}",
                                         parent=self.master)
            elif self.pdf_handler.pdf_document:  # Тільки якщо документ завантажено, але OCR нічого не дав
                messagebox.showinfo("OCR Копіювання", "Не вдалося розпізнати текст у виділеній області.",
                                    parent=self.master)

    def clear_all_state_before_open(self):
        self.pdf_handler.close_pdf()
        self.current_page_num = 0
        self.current_zoom = 1.0
        self.default_zoom_for_file = 1.0
        self.current_pil_image_for_ocr_selection = None

        self.bookmark_manager.clear_bookmarks()
        self.search_manager.clear_search_results(update_ui=False)

        canvas = self.ui_manager.canvas
        if hasattr(self, 'tk_image') and self.tk_image:
            canvas.itemconfig(self.image_on_canvas, image="")
            self.tk_image = None
        canvas.coords(self.image_on_canvas, 0, 0)
        canvas.config(scrollregion=(0, 0, 0, 0))

    def on_closing_command(self):
        self.pdf_handler.close_pdf()
        self.master.destroy()