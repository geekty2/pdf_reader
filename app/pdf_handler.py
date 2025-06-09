import fitz
from PIL import Image
import pytesseract
import io
import os
import sys
import platform


class PDFHandler:
    def __init__(self):
        self.pdf_document = None
        self.total_pages = 0
        self._configure_tesseract()

    def _get_bundle_dir(self):
        """ Повертає шлях до папки, де знаходиться .exe або скрипт. """
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        else:
            return os.path.dirname(os.path.abspath(__file__))


    def _configure_tesseract(self):
        tesseract_path_in_bundle = ""
        tesseract_exe_name = "tesseract.exe" if platform.system() == "Windows" else "tesseract"

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            bundle_dir = sys._MEIPASS
            tesseract_path_in_bundle = os.path.join(bundle_dir, tesseract_exe_name)
            tessdata_dir = os.path.join(bundle_dir, 'tessdata')
            if os.path.isdir(tessdata_dir):
                os.environ['TESSDATA_PREFIX'] = tessdata_dir
                print(f"PDFHandler: TESSDATA_PREFIX встановлено на: {tessdata_dir}")
            else:
                print(f"PDFHandler: ПОПЕРЕДЖЕННЯ - папка tessdata не знайдена в: {tessdata_dir}")

        else:

            system_platform = platform.system()
            common_paths = []
            if system_platform == "Windows":
                common_paths = [r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe']
            elif system_platform == "Linux":
                common_paths = ['/usr/bin/tesseract', '/usr/local/bin/tesseract']
            elif system_platform == "Darwin":
                common_paths = ['/opt/homebrew/bin/tesseract', '/usr/local/bin/tesseract']

            for path_option in common_paths:
                if os.path.exists(path_option):
                    tesseract_path_in_bundle = path_option
                    break

        if tesseract_path_in_bundle and os.path.exists(tesseract_path_in_bundle):
            try:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path_in_bundle
                print(f"PDFHandler: Використовується Tesseract: {tesseract_path_in_bundle}")
            except Exception as e:
                print(f"PDFHandler: Помилка при встановленні шляху Tesseract '{tesseract_path_in_bundle}': {e}")
        else:
            print("PDFHandler: ПОПЕРЕДЖЕННЯ - Tesseract OCR не вдалося знайти.")
            print("           Функції OCR можуть не працювати.")


    def _configure_tesseract(self):
        tesseract_path = ""
        system_platform = platform.system()

        if system_platform == "Windows":
            common_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
            ]
        elif system_platform == "Linux":
            common_paths = ['/usr/bin/tesseract', '/usr/local/bin/tesseract']
        elif system_platform == "Darwin":
            common_paths = ['/opt/homebrew/bin/tesseract', '/usr/local/bin/tesseract']

        for path in common_paths:
            if os.path.exists(path):
                tesseract_path = path
                break

        if tesseract_path:
            try:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                print(f"PDFHandler: Використовується Tesseract: {tesseract_path}")
            except Exception as e:
                print(f"PDFHandler: Помилка при встановленні шляху Tesseract '{tesseract_path}': {e}")
                tesseract_path = ""

        if not tesseract_path:
            print("PDFHandler: ПОПЕРЕДЖЕННЯ - Tesseract OCR не знайдено автоматично або не вдалося налаштувати.")
            print("           Функції OCR можуть не працювати. Переконайтеся, що Tesseract встановлено")
            print("           і знаходиться в системному PATH, або вкажіть шлях у PDFHandler._configure_tesseract().")

    def open_pdf_file(self, filepath):
        if self.pdf_document:
            try:
                self.pdf_document.close()
            except Exception as e:
                print(f"PDFHandler: Помилка при закритті попереднього PDF: {e}")

        try:
            self.pdf_document = fitz.open(filepath)
            self.total_pages = self.pdf_document.page_count
            return True
        except Exception as e:
            print(f"PDFHandler: Помилка відкриття PDF '{filepath}': {e}")
            self.pdf_document = None
            self.total_pages = 0
            return False

    def close_pdf(self):
        if self.pdf_document:
            try:
                self.pdf_document.close()
            except Exception as e:
                print(f"PDFHandler: Помилка при закритті PDF: {e}")
            self.pdf_document = None
            self.total_pages = 0

    def get_page(self, page_num):
        if self.pdf_document and 0 <= page_num < self.total_pages:
            try:
                return self.pdf_document.load_page(page_num)
            except Exception as e:
                print(f"PDFHandler: Помилка завантаження сторінки {page_num}: {e}")
        return None

    def _get_page_text_ocr(self, page_num, lang='ukr'):
        page = self.get_page(page_num)
        if not page: return ""

        try:
            zoom_matrix = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=zoom_matrix, alpha=False)
            if not pix: return "ПОМИЛКА_OCR_CANNOT_GET_PIXMAP"
            pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(pil_img, lang=lang)
            return text
        except pytesseract.TesseractNotFoundError:
            print("PDFHandler: ПОМИЛКА OCR - Tesseract не знайдено.")
            return "ПОМИЛКА_OCR_TESSERACT_NOT_FOUND"
        except Exception as e:
            print(f"PDFHandler: Помилка OCR на сторінці {page_num + 1}: {e}")
            return f"ПОМИЛКА_OCR_{type(e).__name__}"

    def get_page_text(self, page_num, use_ocr_if_needed=True, ocr_lang='ukr'):
        page = self.get_page(page_num)
        if not page: return ""

        text_normal = page.get_text("text")
        if text_normal.strip() and len(text_normal.strip()) > 30:
            return text_normal
        elif use_ocr_if_needed:
            return self._get_page_text_ocr(page_num, lang=ocr_lang)
        else:
            return text_normal

    def get_page_pixmap(self, page_num, zoom_matrix):
        page = self.get_page(page_num)
        if page:
            try:
                return page.get_pixmap(matrix=zoom_matrix, alpha=False)
            except Exception as e:
                print(f"PDFHandler: Помилка отримання Pixmap для сторінки {page_num}: {e}")
        return None

    def check_text_layer(self, page_num=0, ocr_fallback=False, ocr_lang='ukr'):
        if not self.pdf_document or not (0 <= page_num < self.total_pages):
            return False, "Документ не відкритий або номер сторінки невірний."

        text = self.get_page_text(page_num, use_ocr_if_needed=ocr_fallback, ocr_lang=ocr_lang)

        if "ПОМИЛКА_OCR_TESSERACT_NOT_FOUND" in text:
            return False, "ПОМИЛКА: Tesseract не знайдено для OCR."
        if "ПОМИЛКА_OCR_" in text:
            return False, f"Сталася помилка під час OCR: {text.replace('ПОМИЛКА_OCR_', '')}"
        if not text.strip():
            return False, "Сторінка не містить тексту (навіть після можливої спроби OCR)."

        return True, f"Текст знайдено (перші 50 симв.): {text[:50].strip()}..."

    def search_on_page(self, page_num, search_term, use_ocr=False, ocr_lang='ukr'):
        page = self.get_page(page_num)
        if not page: return []

        search_flags = 1

        if not use_ocr:
            quads = page.search_for(search_term, quads=True, flags=search_flags)
            return [q.rect for q in quads]
        else:
            try:
                ocr_zoom_matrix = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=ocr_zoom_matrix, alpha=False)
                if not pix: return []
                pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_data = pytesseract.image_to_data(pil_img, lang=ocr_lang, output_type=pytesseract.Output.DICT)

                found_rects = []
                search_term_lower = search_term.lower()
                inv_ocr_zoom_matrix = ~ocr_zoom_matrix

                for i in range(len(ocr_data['text'])):
                    word = ocr_data['text'][i]
                    conf = int(ocr_data['conf'][i])

                    if conf > 40 and search_term_lower in word.lower():
                        x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], \
                            ocr_data['width'][i], ocr_data['height'][i]
                        if w <= 0 or h <= 0: continue

                        p1_pdf = fitz.Point(x, y) * inv_ocr_zoom_matrix
                        p2_pdf = fitz.Point(x + w, y + h) * inv_ocr_zoom_matrix
                        rect_pdf = fitz.Rect(p1_pdf, p2_pdf).normalize()
                        if not rect_pdf.is_empty:
                            found_rects.append(rect_pdf)

                return found_rects
            except pytesseract.TesseractNotFoundError:
                print("PDFHandler: ПОМИЛКА OCR - Tesseract не знайдено під час пошуку.")
                return []
            except Exception as e:
                print(f"PDFHandler: Помилка OCR під час пошуку на сторінці {page_num + 1}: {e}")
                return []