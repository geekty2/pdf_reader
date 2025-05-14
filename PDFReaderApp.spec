# PDFReaderApp.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os

# Визначаємо базову директорію .spec файлу
# SPECPATH - це змінна, яку PyInstaller встановлює для шляху до .spec файлу
# Якщо SPECPATH не визначено (дуже рідко), можна використати os.getcwd(),
# припускаючи, що pyinstaller запускається з кореня проекту.
try:
    SPEC_DIR = SPECPATH
except NameError:
    SPEC_DIR = os.getcwd()

print(f"INFO: SPECPATH (або getcwd) для .spec файлу: {SPEC_DIR}")


# Шлях до папки з Tesseract у вашому проекті
tesseract_project_subdir = 'tesseract_files'
# Використовуємо SPEC_DIR для побудови абсолютного шляху
tesseract_data_path_abs = os.path.join(SPEC_DIR, tesseract_project_subdir)

# Дані, які потрібно включити
datas = []

if os.path.isdir(tesseract_data_path_abs):
    # Перевіряємо існування tessdata всередині tesseract_data_path_abs
    tessdata_full_path = os.path.join(tesseract_data_path_abs, 'tessdata')
    if os.path.isdir(tessdata_full_path):
        datas += [(tessdata_full_path, 'tessdata')]
        print(f"INFO: Including Tesseract tessdata from: {tessdata_full_path}")
    else:
        print(f"WARNING: 'tessdata' subdirectory not found in {tesseract_data_path_abs}")

    # Включаємо решту файлів з tesseract_data_path_abs (наприклад, tesseract.exe, DLLs)
    # Копіюємо їх в корінь збірки '.'
    # Це можна уточнити, якщо ви знаєте точний список необхідних файлів
    # Наприклад, для Windows:
    # executable_name = 'tesseract.exe'
    # required_dlls = ['libtesseract-5.dll', 'liblept-5.dll', ...] # Список потрібних DLL
    # for item_name in [executable_name] + required_dlls:
    #    item_path = os.path.join(tesseract_data_path_abs, item_name)
    #    if os.path.exists(item_path):
    #        datas += [(item_path, '.')] # Копіювати в корінь
    #    else:
    #        print(f"WARNING: Tesseract file {item_path} not found.")
    # Поки що залишимо копіювання всієї папки, якщо вона є:
    datas += [(tesseract_data_path_abs, '.')]
    print(f"INFO: Including other Tesseract files from: {tesseract_data_path_abs} to root")
else:
    print(f"WARNING: Tesseract data path not found at {tesseract_data_path_abs}")


# Включення папки lectures
lectures_project_subdir = 'lectures'
lectures_path_abs = os.path.join(SPEC_DIR, lectures_project_subdir) # Використовуємо SPEC_DIR

if os.path.isdir(lectures_path_abs):
    datas += [
        (lectures_path_abs, 'lectures')
    ]
    print(f"INFO: Including lectures from: {lectures_path_abs}")
else:
    print(f"WARNING: Lectures directory not found at {lectures_path_abs}. It will be created empty by the app if needed.")


a = Analysis(['main.py'],
             pathex=[SPEC_DIR], # Додаємо директорію .spec до шляхів пошуку Python
             binaries=[],
             datas=datas,
             hiddenimports=[
                 'pytesseract',
                 'PIL._tkinter_finder',
                 'tkinter.filedialog',
                 'tkinter.messagebox',
                 'tkinter.simpledialog',
                 'tkinter.scrolledtext',
                 'queue',
                 'threading',
                 'shlex',
                 'platform',
                 'locale'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# Шлях до іконки (використовуємо SPEC_DIR)
icon_path = os.path.join(SPEC_DIR, 'assets', 'icon.ico') # Припускаючи, що іконка в assets/
if not os.path.exists(icon_path):
    print(f"WARNING: Icon file not found at {icon_path}. Using default icon.")
    icon_path = None


exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='PDFReaderApp',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon=icon_path
          )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='PDFReaderApp_collected')