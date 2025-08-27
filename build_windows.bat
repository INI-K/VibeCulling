@echo off
setlocal enabledelayedexpansion
REM VibeCulling Windows 빌드 스크립트 (PyInstaller 기반)
REM 사용법: build_windows.bat

echo 🔨 VibeCulling PyInstaller 빌드 시작...

REM 가상환경 확인
if "%VIRTUAL_ENV%"=="" (
    echo ⚠️  가상환경이 활성화되지 않았습니다. 가상환경을 먼저 활성화하세요.
    echo    예: venv\Scripts\activate
    pause
    exit /b 1
)

REM 필수 도구 확인
echo 🔍 빌드 환경 확인 중...
python --version
where python

REM PyInstaller 설치 확인
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 📦 PyInstaller 설치 중...
    pip install pyinstaller
)

REM 의존성 설치 확인
echo 📦 의존성 확인 중...
pip install -r requirements.txt --quiet

REM 이전 빌드 결과 정리
echo 🧹 이전 빌드 결과 정리...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec
if exist __pycache__ rmdir /s /q __pycache__

REM PySide6 Qt 플러그인 경로 자동 감지
echo 🔍 PySide6 Qt 플러그인 경로 확인 중...
for /f "delims=" %%i in ('python -c "try: from PySide6.QtCore import QLibraryInfo; print(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)); except: import PySide6, os; pyside_path = os.path.dirname(PySide6.__file__); plugins_path = os.path.join(pyside_path, 'Qt', 'plugins'); print(plugins_path if os.path.exists(plugins_path) else '')"') do (
    set QT_PLUGINS_PATH=%%i
)

if exist "!QT_PLUGINS_PATH!" (
    echo ✅ Qt 플러그인 경로: !QT_PLUGINS_PATH!
) else (
    echo ⚠️  Qt 플러그인 경로를 찾을 수 없습니다.
    set QT_PLUGINS_PATH=
)

REM ExifTool 경로 확인 (Windows용)
set EXIFTOOL_PATH=
where exiftool >nul 2>nul
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('where exiftool') do set EXIFTOOL_PATH=%%i
    echo ✅ ExifTool 발견: !EXIFTOOL_PATH!
) else (
    echo ⚠️  ExifTool을 찾을 수 없습니다. 다운로드하여 설치하거나 PATH에 추가하세요.
)

REM PyInstaller로 Windows 실행파일 빌드
echo 🚀 PyInstaller 빌드 시작...

REM 기본 옵션들 설정
set BASIC_OPTS=--name="VibeCulling" --onefile --windowed --clean --noconfirm --icon=app_icon.ico
set DATA_OPTS=--add-data="resources;resources"

REM ExifTool이 있으면 추가
if not "!EXIFTOOL_PATH!"=="" (
    set DATA_OPTS=!DATA_OPTS! --add-binary="!EXIFTOOL_PATH!;exiftool"
)

REM exiftool 폴더가 있으면 추가
if exist "exiftool" (
    set DATA_OPTS=!DATA_OPTS! --add-data="exiftool;exiftool"
)

REM Qt 플러그인들 추가
if not "!QT_PLUGINS_PATH!"=="" (
    for %%d in (platforms imageformats styles iconengines) do (
        if exist "!QT_PLUGINS_PATH!\%%d" (
            set DATA_OPTS=!DATA_OPTS! --add-data="!QT_PLUGINS_PATH!\%%d;Qt\plugins\%%d"
        )
    )
)

REM Hidden imports - 모든 필요한 모듈들을 명시적으로 포함
set HIDDEN_IMPORTS=^
--hidden-import=PySide6.QtCore ^
--hidden-import=PySide6.QtGui ^
--hidden-import=PySide6.QtWidgets ^
--hidden-import=PySide6.QtSvg ^
--hidden-import=PIL._tkinter_finder ^
--hidden-import=PIL.Image ^
--hidden-import=PIL.ImageQt ^
--hidden-import=PIL.ExifTags ^
--hidden-import=PIL.ImageOps ^
--hidden-import=rawpy ^
--hidden-import=piexif ^
--hidden-import=pillow_heif ^
--hidden-import=pillow_heif.HeifImagePlugin ^
--hidden-import=numpy ^
--hidden-import=numpy.core._methods ^
--hidden-import=numpy.lib.format ^
--hidden-import=psutil ^
--hidden-import=json ^
--hidden-import=logging.handlers ^
--hidden-import=multiprocessing.pool ^
--hidden-import=concurrent.futures

REM 서브모듈 수집
set COLLECT_OPTS=^
--collect-submodules=PIL ^
--collect-submodules=pillow_heif ^
--collect-submodules=rawpy ^
--collect-submodules=PySide6

REM 제외할 모듈들
set EXCLUDE_OPTS=^
--exclude-module=tkinter ^
--exclude-module=matplotlib ^
--exclude-module=test ^
--exclude-module=unittest ^
--exclude-module=distutils ^
--exclude-module=setuptools

REM 모든 옵션 결합하여 실행
pyinstaller %BASIC_OPTS% %DATA_OPTS% %HIDDEN_IMPORTS% %COLLECT_OPTS% %EXCLUDE_OPTS% main.py

REM 빌드 성공 확인
if exist "dist\VibeCulling.exe" (
    echo ✅ 빌드 완료! 결과물: dist\VibeCulling.exe
    
    REM 파일 크기 확인
    for %%A in ("dist\VibeCulling.exe") do echo 📊 실행파일 크기: %%~zA bytes
    
    REM 포함된 라이브러리 확인 (간접적)
    echo 🔍 포함된 주요 라이브러리 확인...
    echo    - Python 런타임: ✅
    echo    - PySide6: ✅ (수집됨)
    echo    - PIL/Pillow: ✅ (수집됨)
    echo    - rawpy: ✅ (수집됨)
    echo    - NumPy: ✅ (수집됨)
    
    echo.
    echo 🎉 VibeCulling Windows 실행파일 빌드가 성공적으로 완료되었습니다!
    echo.
    echo 📍 실행 방법:
    echo    dist\VibeCulling.exe
    echo.
    echo 📦 배포 방법:
    echo    1. dist\VibeCulling.exe를 단독 실행파일로 배포
    echo    2. 모든 라이브러리가 포함되어 있어 별도 설치 불필요
    echo.
    echo 🧪 테스트 권장 사항:
    echo    - 다른 Windows 시스템에서 실행 테스트
    echo    - RAW 파일 로딩 테스트  
    echo    - EXIF 정보 읽기 테스트
    echo    - 메모리 사용량 확인
    
) else (
    echo ❌ 빌드 실패! dist\VibeCulling.exe를 찾을 수 없습니다.
    echo build.log를 확인하거나 --log-level DEBUG 옵션을 추가하여 디버깅하세요.
    pause
    exit /b 1
)

echo.
echo 🧹 빌드 아티팩트 정리...
echo    - build\ 폴더와 .spec 파일은 필요시 수동으로 삭제하세요
echo    - dist\VibeCulling.exe가 최종 결과물입니다

pause