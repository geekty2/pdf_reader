import tkinter as tk
from app.pdf_viewer_app import PDFViewerApp
from utils.clipboard_checker import check_pyperclip_configured

if __name__ == "__main__":
    check_pyperclip_configured() # Перевірка pyperclip

    root = tk.Tk()
    app = PDFViewerApp(root)
    root.mainloop()