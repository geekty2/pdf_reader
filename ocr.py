import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import pytesseract
import os
import platform

# --- Налаштування Tesseract ---
# !!! ВАЖЛИВО: Вкажіть правильний шлях до встановленого Tesseract OCR !!!
tesseract_path = ""
system = platform.system()

if system == "Windows":
    # Типовий шлях для Windows. Змініть, якщо ви встановили в інше місце.
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
elif system == "Linux":
    # Спробуйте знайти tesseract автоматично, або вкажіть шлях вручну
    # Наприклад: '/usr/bin/tesseract' або '/usr/local/bin/tesseract'
    if os.path.exists('/usr/bin/tesseract'):
        tesseract_path = '/usr/bin/tesseract'
    elif os.path.exists('/usr/local/bin/tesseract'):
         tesseract_path = '/usr/local/bin/tesseract'
    else:
        print("Не вдалося автоматично знайти Tesseract на Linux. Вкажіть шлях вручну у змінній tesseract_path.")
elif system == "Darwin": # macOS
    # Спробуйте знайти tesseract автоматично, або вкажіть шлях вручну
    # Наприклад: '/opt/homebrew/bin/tesseract' (Apple Silicon) or '/usr/local/bin/tesseract' (Intel)
    if os.path.exists('/opt/homebrew/bin/tesseract'):
         tesseract_path = '/opt/homebrew/bin/tesseract'
    elif os.path.exists('/usr/local/bin/tesseract'):
        tesseract_path = '/usr/local/bin/tesseract'
    else:
         print("Не вдалося автоматично знайти Tesseract на macOS (brew?). Вкажіть шлях вручну у змінній tesseract_path.")

# Перевірка чи існує вказаний шлях
if tesseract_path and os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"Використовується Tesseract: {tesseract_path}")
else:
    messagebox.showerror("Помилка Tesseract",
                         f"Не вдалося знайти виконуваний файл Tesseract за шляхом: '{tesseract_path}'.\n"
                         "Будь ласка, встановіть Tesseract OCR та вкажіть правильний шлях у коді.")
    exit() # Вихід, якщо Tesseract не знайдено

# --- Глобальні змінні для Tkinter ---
selection_coords = {}
rect_id = None
canvas = None
root = None
original_pil_image = None # Зберігаємо оригінальне PIL зображення

# --- Функції ---
def select_pdf_file():
    """Відкриває діалог вибору PDF файлу."""
    file_path = filedialog.askopenfilename(
        title="Оберіть PDF файл",
        filetypes=[("PDF files", "*.pdf")]
    )
    return file_path

def get_page_number(max_pages):
    """Запитує номер сторінки у користувача."""
    page_num = simpledialog.askinteger(
        "Номер сторінки",
        f"Введіть номер сторінки (1-{max_pages}):",
        minvalue=1,
        maxvalue=max_pages
    )
    return page_num

def render_pdf_page(pdf_path, page_num_user):
    """Відкриває PDF, рендерить сторінку як зображення PIL."""
    try:
        doc = fitz.open(pdf_path)
        if not 1 <= page_num_user <= len(doc):
            messagebox.showerror("Помилка", f"Невірний номер сторінки: {page_num_user}. У документі {len(doc)} сторінок.")
            return None, None

        page_num_zero_based = page_num_user - 1 # PyMuPDF використовує 0-індексацію
        page = doc.load_page(page_num_zero_based)

        # Рендеринг з вищою роздільною здатністю для кращого OCR
        zoom = 2.0 # Збільшення в 2 рази (200%) -> 144 DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Конвертація в PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img, pix # Повертаємо і PIL Image, і Pixmap

    except Exception as e:
        messagebox.showerror("Помилка читання PDF", f"Не вдалося відкрити або обробити PDF: {e}")
        return None, None

def perform_ocr(image_region):
    """Виконує OCR на переданому зображенні (PIL Image)."""
    try:
        # Вказуємо мови: українська + англійська
        # Переконайтесь, що у вас встановлені відповідні мовні пакети для Tesseract!
        custom_config = r'--oem 3 --psm 6 -l ukr+eng'
        text = pytesseract.image_to_string(image_region, config=custom_config)
        print("\n--- Розпізнаний текст ---")
        print(text)
        print("-------------------------\n")
        messagebox.showinfo("Результат OCR", f"Розпізнаний текст:\n\n{text}" if text else "Текст не розпізнано.")

    except pytesseract.TesseractNotFoundError:
         messagebox.showerror("Помилка Tesseract",
                              "Команду 'tesseract' не знайдено.\n"
                              "Переконайтеся, що Tesseract OCR встановлено та шлях до нього вказано правильно у коді.")
    except Exception as e:
        messagebox.showerror("Помилка OCR", f"Під час розпізнавання сталася помилка: {e}")

# --- Обробники подій миші для Tkinter ---
def on_mouse_press(event):
    global selection_coords, rect_id, canvas
    # Початок виділення
    selection_coords['x1'] = event.x
    selection_coords['y1'] = event.y
    # Створюємо прямокутник (поки що нульового розміру)
    if rect_id:
        canvas.delete(rect_id)
    rect_id = canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                      outline='red', width=2, tags="selection_rect")

def on_mouse_drag(event):
    global selection_coords, rect_id, canvas
    # Оновлення координат прямокутника під час руху миші
    if rect_id:
        canvas.coords(rect_id, selection_coords['x1'], selection_coords['y1'], event.x, event.y)

def on_mouse_release(event):
    global selection_coords, rect_id, canvas, root, original_pil_image
    # Завершення виділення
    selection_coords['x2'] = event.x
    selection_coords['y2'] = event.y

    # Переконуємось, що x1 < x2 та y1 < y2
    x1 = min(selection_coords['x1'], selection_coords['x2'])
    y1 = min(selection_coords['y1'], selection_coords['y2'])
    x2 = max(selection_coords['x1'], selection_coords['x2'])
    y2 = max(selection_coords['y1'], selection_coords['y2'])

    # Ігноруємо дуже маленькі виділення (випадкові кліки)
    if abs(x1 - x2) < 5 or abs(y1 - y2) < 5:
        print("Виділення занадто мале, ігнорується.")
        canvas.delete(rect_id) # Видалити намальований прямокутник
        rect_id = None
        return

    print(f"Виділена область (координати на Canvas): ({x1}, {y1}) - ({x2}, {y2})")

    if original_pil_image:
        try:
            # Вирізаємо область з оригінального PIL зображення
            # Координати Canvas напряму відповідають пікселям зображення, якщо воно не масштабувалося у Tkinter
            selected_region = original_pil_image.crop((x1, y1, x2, y2))
            # selected_region.show() # Показати вирізану область (для налагодження)

            # Виконуємо OCR
            perform_ocr(selected_region)

        except Exception as e:
             messagebox.showerror("Помилка обрізки", f"Не вдалося вирізати область: {e}")

    # Видаляємо прямокутник і закриваємо вікно після обробки
    if rect_id:
        canvas.delete(rect_id)
        rect_id = None
    if root:
       root.quit() # Зупиняє mainloop
       root.destroy() # Закриває вікно

# --- Основна логіка ---
if __name__ == "__main__":
    root_tk = tk.Tk()
    root_tk.withdraw() # Сховати головне порожнє вікно спочатку

    pdf_file = select_pdf_file()
    if not pdf_file:
        print("Файл не вибрано.")
        root_tk.destroy()
        exit()

    # Тимчасово відкриваємо PDF, щоб дізнатися кількість сторінок
    try:
        temp_doc = fitz.open(pdf_file)
        num_pages = len(temp_doc)
        temp_doc.close()
        if num_pages == 0:
             messagebox.showerror("Помилка", "PDF файл порожній.")
             root_tk.destroy()
             exit()
    except Exception as e:
        messagebox.showerror("Помилка", f"Не вдалося прочитати кількість сторінок: {e}")
        root_tk.destroy()
        exit()


    page_to_process = get_page_number(num_pages)
    if not page_to_process:
        print("Номер сторінки не введено.")
        root_tk.destroy()
        exit()

    # Рендеримо обрану сторінку
    original_pil_image, _ = render_pdf_page(pdf_file, page_to_process) # Зберігаємо оригінал

    if original_pil_image:
        # Створюємо нове вікно Toplevel для відображення сторінки
        root = tk.Toplevel(root_tk)
        root.title(f"Сторінка {page_to_process} з '{os.path.basename(pdf_file)}' - Виділіть область")

        # Конвертуємо PIL Image в ImageTk для Tkinter
        img_tk = ImageTk.PhotoImage(original_pil_image)

        # Створюємо Canvas і розміщуємо зображення
        canvas = tk.Canvas(root, width=img_tk.width(), height=img_tk.height(), cursor="cross")
        canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        canvas.pack()

        # Зберігаємо посилання на зображення, щоб воно не було видалено збирачем сміття Python
        canvas.image = img_tk

        # Прив'язуємо події миші до Canvas
        canvas.bind("<ButtonPress-1>", on_mouse_press) # Ліва кнопка натиснута
        canvas.bind("<B1-Motion>", on_mouse_drag)      # Ліва кнопка натиснута і рухається
        canvas.bind("<ButtonRelease-1>", on_mouse_release) # Ліва кнопка відпущена

        # Запускаємо головний цикл Tkinter (чекаємо на дії користувача)
        print("Будь ласка, виділіть область на зображенні за допомогою миші.")
        root.mainloop()

    # Закриваємо приховане головне вікно, якщо воно ще існує
    if root_tk:
       try:
           root_tk.destroy()
       except tk.TclError:
           pass # Вікно могло бути вже закрите

    print("Програма завершила роботу.")