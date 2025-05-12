import fitz  # PyMuPDF


class PDFHandler:
    def __init__(self):
        self.pdf_document = None
        self.total_pages = 0

    def open_pdf_file(self, filepath):
        if self.pdf_document:
            self.pdf_document.close()

        try:
            self.pdf_document = fitz.open(filepath)
            self.total_pages = self.pdf_document.page_count
            return True
        except Exception as e:
            print(f"Помилка відкриття PDF в PDFHandler: {e}")
            self.pdf_document = None
            self.total_pages = 0
            return False

    def close_pdf(self):
        if self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None
            self.total_pages = 0

    def get_page(self, page_num):
        if self.pdf_document and 0 <= page_num < self.total_pages:
            return self.pdf_document.load_page(page_num)
        return None

    def get_page_text(self, page_num):
        page = self.get_page(page_num)
        if page:
            return page.get_text("text")
        return ""

    def get_page_pixmap(self, page_num, zoom_matrix):
        page = self.get_page(page_num)
        if page:
            return page.get_pixmap(matrix=zoom_matrix, alpha=False)
        return None

    def check_text_layer(self, page_num=0):
        """Перевіряє наявність текстового шару на заданій сторінці."""
        if not self.pdf_document or not (0 <= page_num < self.total_pages):
            return False, "Документ не відкритий або номер сторінки невірний."

        page = self.pdf_document.load_page(page_num)
        text = page.get_text()
        if not text.strip():
            return False, "Сторінка не містить видобутого тексту (можливо, скан без OCR)."
        return True, f"Текст знайдено (перші 50 символів): {text[:50].strip()}..."

    # Пошук поки що залишимо в головному класі, бо він сильно зав'язаний на GUI-оновлення
    # Але в майбутньому search_for_text може бути тут:
    # def search_for_text_on_page(self, page_num, search_term, flags):
    #     page = self.get_page(page_num)
    #     if page:
    #         return page.search_for(search_term, quads=True, flags=flags)
    #     return []