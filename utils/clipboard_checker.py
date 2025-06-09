import pyperclip
import tkinter as tk
from tkinter import messagebox

def check_pyperclip_configured():
    try:
        pyperclip.copy("test_clipboard_check_startup")
        if pyperclip.paste() != "test_clipboard_check_startup":
            pyperclip.copy("test_clipboard_check_startup_2")
            if pyperclip.paste() != "test_clipboard_check_startup_2":
                raise pyperclip.PyperclipException("Перевірка буфера обміну не вдалася: вміст не збігається.")
        print("Pyperclip налаштований коректно.")
        return True
    except pyperclip.PyperclipException as e:
        warning_message = (
            f"ПОПЕРЕДЖЕННЯ: pyperclip не налаштований належним чином для вашої системи.\n"
            f"Помилка: {e}\n"
            f"Функція копіювання тексту може не працювати.\n"
            f"Будь ласка, встановіть один з механізмів копіювання/вставки:\n"
            f"  Linux: sudo apt-get install xclip або sudo apt-get install xsel\n"
            f"  Windows: зазвичай працює 'з коробки'\n"
            f"  macOS: зазвичай працює 'з коробки'"
        )
        print(warning_message)
        return False