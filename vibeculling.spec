# -*- mode: python ; coding: utf-8 -*-
# VibeCulling PyInstaller Spec 파일
# 사용법: pyinstaller vibeculling.spec

import sys
import os
from pathlib import Path

# 현재 디렉토리 설정
block_cipher = None
project_root = Path(__file__).parent

# PySide6 Qt 플러그인 경로 자동 감지
def get_qt_plugins_path():
    try:
        from PySide6.QtCore import QLibraryInfo
        return QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
    except:
        try:
            import PySide6
            pyside_path = Path(PySide6.__file__).parent
            plugins_path = pyside_path / 'Qt' / 'plugins'
            if plugins_path.exists():
                return str(plugins_path)
        except:
            pass
    return None

# 데이터 파일들 수집
datas = []

# 리소스 폴더 추가
if (project_root / 'resources').exists():
    datas.append(('resources', 'resources'))

# ExifTool 관련 파일들 추가
if (project_root / 'exiftool').exists():
    datas.append(('exiftool', 'exiftool'))

# Qt 플러그인들 추가
qt_plugins_path = get_qt_plugins_path()
if qt_plugins_path and Path(qt_plugins_path).exists():
    qt_plugins_path = Path(qt_plugins_path)
    for plugin_dir in ['platforms', 'imageformats', 'styles', 'iconengines']:
        plugin_path = qt_plugins_path / plugin_dir
        if plugin_path.exists():
            datas.append((str(plugin_path), f'Qt/plugins/{plugin_dir}'))

# 바이너리 파일들 수집
binaries = []

# ExifTool 바이너리 추가 (macOS/Linux)
import shutil
exiftool_path = shutil.which('exiftool')
if exiftool_path:
    binaries.append((exiftool_path, 'exiftool'))

# libraw 라이브러리 추가 (macOS용)
if sys.platform == 'darwin':
    for path in ['/opt/homebrew/lib/libraw.dylib', '/usr/local/lib/libraw.dylib']:
        if Path(path).exists():
            binaries.append((path, '.'))
            break

# Hidden imports - 모든 필요한 모듈들을 명시적으로 포함
hiddenimports = [
    # PySide6 필수 모듈들
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    
    # PIL/Pillow 관련
    'PIL._tkinter_finder',
    'PIL.Image',
    'PIL.ImageQt',
    'PIL.ExifTags',
    'PIL.ImageOps',
    
    # 이미지 처리 라이브러리들
    'rawpy',
    'piexif',
    'pillow_heif',
    'pillow_heif.HeifImagePlugin',
    
    # NumPy 관련
    'numpy',
    'numpy.core._methods',
    'numpy.lib.format',
    
    # 기타 필수 모듈들
    'psutil',
    'json',
    'logging.handlers',
    'multiprocessing.pool',
    'concurrent.futures',
]

# 제외할 모듈들
excludes = [
    'tkinter',
    'matplotlib',
    'test',
    'unittest',
    'distutils',
    'setuptools',
]

# 분석 단계
a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

# PYZ 생성 (Python 바이트코드 아카이브)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 플랫폼별 설정
if sys.platform == 'darwin':
    # macOS 앱 번들
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='VibeCulling',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='app_icon.icns',
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='VibeCulling',
    )
    
    app = BUNDLE(
        coll,
        name='VibeCulling.app',
        icon='app_icon.icns',
        bundle_identifier='com.vibeculling.app',
        version='1.0.0',
    )
    
elif sys.platform == 'win32':
    # Windows 단일 실행파일
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='VibeCulling',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='app_icon.ico',
    )
    
else:
    # Linux/기타 플랫폼
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='VibeCulling',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
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
        name='VibeCulling',
    )