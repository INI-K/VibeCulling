#!/bin/bash

# VibeCulling macOS 빌드 스크립트 (PyInstaller 기반)
# 사용법: ./build_mac_app.sh

set -e  # 오류 발생 시 스크립트 중단

echo "🔨 VibeCulling PyInstaller 빌드 시작..."

# 가상환경 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  가상환경이 활성화되지 않았습니다. 가상환경을 먼저 활성화하세요."
    echo "   예: source venv/bin/activate"
    exit 1
fi

# 필수 도구 확인
echo "🔍 빌드 환경 확인 중..."
python --version
which python

# PyInstaller 설치 확인
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "📦 PyInstaller 설치 중..."
    pip install pyinstaller
fi

# 의존성 설치 확인
echo "📦 의존성 확인 중..."
pip install -r requirements.txt --quiet

# 이전 빌드 결과 정리
echo "🧹 이전 빌드 결과 정리..."
rm -rf build dist *.spec __pycache__

# PySide6 Qt 플러그인 경로 자동 감지
echo "🔍 PySide6 Qt 플러그인 경로 확인 중..."
QT_PLUGINS_PATH=$(python -c "
try:
    from PySide6.QtCore import QLibraryInfo
    print(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
except:
    import PySide6
    import os
    pyside_path = os.path.dirname(PySide6.__file__)
    plugins_path = os.path.join(pyside_path, 'Qt', 'plugins')
    if os.path.exists(plugins_path):
        print(plugins_path)
    else:
        print('')
" 2>/dev/null)

if [ -n "$QT_PLUGINS_PATH" ] && [ -d "$QT_PLUGINS_PATH" ]; then
    echo "✅ Qt 플러그인 경로: $QT_PLUGINS_PATH"
else
    echo "⚠️  Qt 플러그인 경로를 찾을 수 없습니다."
    QT_PLUGINS_PATH=""
fi

# ExifTool 경로 확인 (macOS용)
EXIFTOOL_PATH=""
if command -v exiftool &> /dev/null; then
    EXIFTOOL_PATH=$(which exiftool)
    echo "✅ ExifTool 발견: $EXIFTOOL_PATH"
else
    echo "⚠️  ExifTool을 찾을 수 없습니다. 'brew install exiftool'로 설치하세요."
fi

# libraw 라이브러리 경로 확인 (rawpy용)
LIBRAW_PATH=""
for path in "/opt/homebrew/lib/libraw.dylib" "/usr/local/lib/libraw.dylib" "/opt/local/lib/libraw.dylib"; do
    if [ -f "$path" ]; then
        LIBRAW_PATH="$path"
        echo "✅ libraw 발견: $LIBRAW_PATH"
        break
    fi
done

if [ -z "$LIBRAW_PATH" ]; then
    echo "⚠️  libraw를 찾을 수 없습니다. 'brew install libraw'로 설치하는 것을 권장합니다."
fi

# PyInstaller로 macOS 앱 빌드
echo "🚀 PyInstaller 빌드 시작..."

# 기본 PyInstaller 옵션들
PYINSTALLER_OPTS=(
    --name="VibeCulling"
    --onedir
    --windowed
    --clean
    --noconfirm
    --icon=app_icon.icns
    --add-data="resources:resources"
)

# ExifTool이 있으면 추가
if [ -n "$EXIFTOOL_PATH" ]; then
    PYINSTALLER_OPTS+=(--add-binary="$EXIFTOOL_PATH:exiftool")
fi

# exiftool 폴더가 있으면 추가
if [ -d "exiftool" ]; then
    PYINSTALLER_OPTS+=(--add-data="exiftool:exiftool")
fi

# libraw가 있으면 추가
if [ -n "$LIBRAW_PATH" ]; then
    PYINSTALLER_OPTS+=(--add-binary="$LIBRAW_PATH:.")
fi

# Qt 플러그인들 추가
if [ -n "$QT_PLUGINS_PATH" ] && [ -d "$QT_PLUGINS_PATH" ]; then
    for plugin_dir in platforms imageformats styles iconengines; do
        if [ -d "$QT_PLUGINS_PATH/$plugin_dir" ]; then
            PYINSTALLER_OPTS+=(--add-data="$QT_PLUGINS_PATH/$plugin_dir:Qt/plugins/$plugin_dir")
        fi
    done
fi

# Hidden imports - 모든 필요한 모듈들을 명시적으로 포함
HIDDEN_IMPORTS=(
    # PySide6 필수 모듈들
    --hidden-import=PySide6.QtCore
    --hidden-import=PySide6.QtGui  
    --hidden-import=PySide6.QtWidgets
    --hidden-import=PySide6.QtSvg
    
    # PIL/Pillow 관련
    --hidden-import=PIL._tkinter_finder
    --hidden-import=PIL.Image
    --hidden-import=PIL.ImageQt
    --hidden-import=PIL.ExifTags
    --hidden-import=PIL.ImageOps
    
    # 이미지 처리 라이브러리들
    --hidden-import=rawpy
    --hidden-import=piexif
    --hidden-import=pillow_heif
    --hidden-import=pillow_heif.HeifImagePlugin
    
    # NumPy 관련
    --hidden-import=numpy
    --hidden-import=numpy.core._methods
    --hidden-import=numpy.lib.format
    
    # 기타 필수 모듈들
    --hidden-import=psutil
    --hidden-import=json
    --hidden-import=logging.handlers
    --hidden-import=multiprocessing.pool
    --hidden-import=concurrent.futures
)

# 서브모듈 수집
COLLECT_SUBMODULES=(
    --collect-submodules=PIL
    --collect-submodules=pillow_heif
    --collect-submodules=rawpy
    --collect-submodules=PySide6
)

# 제외할 모듈들
EXCLUDE_MODULES=(
    --exclude-module=tkinter
    --exclude-module=matplotlib
    --exclude-module=test
    --exclude-module=unittest
    --exclude-module=distutils
    --exclude-module=setuptools
)

# 모든 옵션 결합하여 실행
pyinstaller \
    "${PYINSTALLER_OPTS[@]}" \
    "${HIDDEN_IMPORTS[@]}" \
    "${COLLECT_SUBMODULES[@]}" \
    "${EXCLUDE_MODULES[@]}" \
    main.py

# 빌드 성공 확인
if [ -d "dist/VibeCulling.app" ]; then
    echo "✅ 빌드 완료! 결과물: dist/VibeCulling.app"
    
    # 앱 크기 확인
    APP_SIZE=$(du -sh dist/VibeCulling.app | cut -f1)
    echo "📊 앱 크기: $APP_SIZE"
    
    # 포함된 라이브러리 확인
    echo "🔍 포함된 주요 라이브러리 확인..."
    if [ -d "dist/VibeCulling.app/Contents/MacOS" ]; then
        echo "   - Python 런타임: ✅"
        if find "dist/VibeCulling.app" -name "*PySide6*" | head -1 | grep -q .; then
            echo "   - PySide6: ✅"
        else
            echo "   - PySide6: ❌"
        fi
        if find "dist/VibeCulling.app" -name "*PIL*" -o -name "*Pillow*" | head -1 | grep -q .; then
            echo "   - PIL/Pillow: ✅"
        else
            echo "   - PIL/Pillow: ❌"  
        fi
        if find "dist/VibeCulling.app" -name "*rawpy*" | head -1 | grep -q .; then
            echo "   - rawpy: ✅"
        else
            echo "   - rawpy: ❌"
        fi
        if find "dist/VibeCulling.app" -name "*numpy*" | head -1 | grep -q .; then
            echo "   - NumPy: ✅"
        else
            echo "   - NumPy: ❌"
        fi
    fi
    
    # macOS 코드 사이닝 (개발용)
    echo "🔐 코드 사이닝 중..."
    codesign --force --deep --sign - dist/VibeCulling.app || echo "⚠️  코드 사이닝 실패 (선택사항)"
    
    # 격리 속성 제거
    echo "🔓 격리 속성 제거 중..."
    xattr -rd com.apple.quarantine dist/VibeCulling.app 2>/dev/null || echo "ℹ️  격리 속성이 없습니다"
    
    # 실행 권한 확인
    chmod +x dist/VibeCulling.app/Contents/MacOS/VibeCulling
    
    echo ""
    echo "🎉 VibeCulling macOS 앱 빌드가 성공적으로 완료되었습니다!"
    echo ""
    echo "📍 실행 방법:"
    echo "   open dist/VibeCulling.app"
    echo ""
    echo "📦 배포 방법:"
    echo "   1. dist/VibeCulling.app을 압축하여 배포"
    echo "   2. 사용자는 Applications 폴더로 드래그하여 설치"
    echo ""
    echo "🧪 테스트 권장 사항:"
    echo "   - 다른 macOS 시스템에서 실행 테스트"
    echo "   - RAW 파일 로딩 테스트"
    echo "   - EXIF 정보 읽기 테스트"
    
else
    echo "❌ 빌드 실패! dist/VibeCulling.app을 찾을 수 없습니다."
    echo "build.log를 확인하거나 --log-level DEBUG 옵션을 추가하여 디버깅하세요."
    exit 1
fi

echo ""
echo "🧹 빌드 아티팩트 정리..."
echo "   - build/ 폴더와 .spec 파일은 필요시 수동으로 삭제하세요"
echo "   - dist/VibeCulling.app이 최종 결과물입니다"