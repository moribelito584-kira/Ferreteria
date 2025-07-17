# -*- mode: python ; coding: utf-8 -*-

# Importaciones que PyInstaller añade automáticamente
# No los borres a menos que sepas lo que haces
# import sys
# import os
# from PyInstaller.utils.hooks import collect_data_files

# AQUI DEBE ESTAR LA DEFINICION DE block_cipher
block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['D:\\Ferreteria\\inventario_ferreteria'], # Asegúrate de que esta ruta sea correcta
    binaries=[],
    datas=[
        ('D:\\Ferreteria\\inventario_ferreteria\\.env', '.'), # Incluye el .env en la raíz del bundle
        ('D:\\Ferreteria\\inventario_ferreteria\\ferreteriabr-555f7-firebase-adminsdk-fbsvc-fb763add61.json', '.'), # Incluye tu JSON en la raíz del bundle
        ('D:\\Ferreteria\\inventario_ferreteria\\templates', 'templates'), # Incluye toda la carpeta templates
        ('D:\\Ferreteria\\inventario_ferreteria\\static', 'static'),      # Incluye toda la carpeta static
    ],
    hiddenimports=['waitress'], # <--- ¡ESTO ES LO QUE HACIA FALTA!
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='InventarioFerreteria', # Nombre de tu ejecutable
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Importante: mantiene la ventana de consola para ver el servidor Flask
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='InventarioFerreteria',
)