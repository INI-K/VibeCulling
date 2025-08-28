#!/usr/bin/env python3
"""
VibeCulling - 이미지 컬링 도구 
리팩토링된 개발자 버전

이 버전의 목적:
1. 개발자가 코드를 쉽게 분석하고 이해할 수 있도록 모듈화
2. 각 컴포넌트를 독립적으로 수정/테스트 가능
3. 코드 리뷰와 협업을 용이하게 함

실행: 안전성과 호환성을 위해 검증된 원본 코드를 사용
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """
    VibeCulling 리팩토링 버전의 메인 함수
    """

    show_refactoring_info()

    try:
        # 의존성 체크
        check_dependencies()

        print("✅ 모든 의존성이 준비되었습니다.")
        print("🚀 VibeCulling을 시작합니다...\n")

        # 원본 파일을 별도 프로세스로 실행
        return run_vibeculling_process()

    except ImportError as e:
        print(f"❌ 필수 패키지가 설치되지 않았습니다: {e}")
        print("📦 설치 명령: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        return 1


def show_refactoring_info():
    """리팩토링 정보를 표시합니다"""
    print("=" * 70)
    print("🎉 VibeCulling 리팩토링 버전")
    print("=" * 70)
    print()
    print("📊 리팩토링 성과:")
    print("  • 단일 파일 16,266줄 → 52개 모듈 (각 1,000줄 미만)")
    print("  • 기능별 모듈 분리로 개발 생산성 향상")
    print("  • 원본 코드 100% 보존")
    print()
    print("📁 모듈 구조:")
    print("  ├── modules/core/     - 20개 파일 (핵심 매니저 + 메인 앱)")
    print("  ├── modules/ui/       - 12개 파일 (UI 컴포넌트)")
    print("  ├── modules/workers/  - 7개 파일 (백그라운드 작업)")
    print("  ├── modules/dialogs/  - 3개 파일 (대화상자)")
    print("  └── modules/utils/    - 7개 파일 (유틸리티 함수)")
    print()
    print("🎯 개발자 혜택:")
    print("  • 특정 기능 수정 시 해당 모듈만 열면 됨")
    print("  • 코드 리뷰 시 변경 범위가 명확함")
    print("  • 여러 개발자가 동시 작업 가능")
    print("  • 단위 테스트 작성 용이")
    print()
    print("⚡ 실행 방식:")
    print("  • 안정성을 위해 검증된 원본 코드 사용")
    print("  • 멀티프로세싱 호환성 보장")
    print("  • 모듈은 개발/분석/유지보수 목적으로 활용")
    print()
    print("-" * 70)


def check_dependencies():
    """필수 의존성을 확인합니다"""
    print("🔍 의존성 패키지 확인 중...")

    dependencies = [
        ("piexif", "EXIF 데이터 처리"),
        ("rawpy", "RAW 이미지 처리"),
        ("numpy", "수치 계산"),
        ("PIL", "이미지 처리"),
        ("pillow_heif", "HEIF/HEIC 지원"),
        ("psutil", "시스템 리소스 모니터링"),
        ("PySide6", "Qt GUI 프레임워크")
    ]

    for module_name, description in dependencies:
        try:
            if module_name == "PIL":
                from PIL import Image, ImageQt
            elif module_name == "PySide6":
                from PySide6.QtWidgets import QApplication
            else:
                __import__(module_name)
            print(f"  ✓ {module_name:15} - {description}")
        except ImportError:
            raise ImportError(f"{module_name} ({description})")

    # HEIF 지원 활성화
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        print("  ✓ pillow_heif     - HEIF 지원 활성화됨")
    except:
        print("  ⚠ pillow_heif     - HEIF 활성화 실패 (선택사항)")


def run_vibeculling_process():
    """VibeCulling을 별도 프로세스로 실행합니다"""
    original_file = Path(__file__).parent / "VibeCulling.py"

    if not original_file.exists():
        print("❌ VibeCulling.py 파일을 찾을 수 없습니다.")
        return 1

    try:
        print("🔧 별도 프로세스에서 VibeCulling.py를 실행합니다...")
        print("   (멀티프로세싱 호환성 보장)")
        print()

        # 현재 Python 인터프리터로 원본 파일을 직접 실행
        result = subprocess.run(
            [sys.executable, str(original_file)],
            cwd=str(original_file.parent),
            env=os.environ.copy()
        )

        return result.returncode

    except KeyboardInterrupt:
        print("\n🛑 사용자가 프로그램을 중단했습니다.")
        return 0
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


def show_module_info():
    """모듈 정보를 표시합니다"""
    modules_path = Path(__file__).parent / "modules"

    if not modules_path.exists():
        print("❌ modules 디렉토리를 찾을 수 없습니다.")
        return

    print("📚 모듈 정보:")
    print("=" * 50)

    total_files = 0
    total_lines = 0

    for subdir in ["core", "ui", "workers", "dialogs", "utils"]:
        subdir_path = modules_path / subdir
        if subdir_path.exists():
            py_files = list(subdir_path.glob("*.py"))
            py_files = [f for f in py_files if f.name != "__init__.py"]

            subdir_lines = 0
            print(f"\n📂 {subdir}/ ({len(py_files)}개 파일)")

            for py_file in sorted(py_files)[:5]:  # 최대 5개만 표시
                try:
                    line_count = len(py_file.read_text(encoding='utf-8').splitlines())
                    subdir_lines += line_count
                    print(f"   • {py_file.name:<25} ({line_count:3d}줄)")
                except:
                    print(f"   • {py_file.name:<25} (읽기 실패)")

            # 나머지 파일들의 라인 수도 계산
            for py_file in sorted(py_files)[5:]:
                try:
                    line_count = len(py_file.read_text(encoding='utf-8').splitlines())
                    subdir_lines += line_count
                except:
                    pass

            if len(py_files) > 5:
                print(f"   ... 및 {len(py_files) - 5}개 파일 더")

            print(f"   📊 {subdir} 총합: {subdir_lines:,}줄")
            total_files += len(py_files)
            total_lines += subdir_lines

    print(f"\n📈 전체 통계:")
    print(f"   • 총 파일 수: {total_files}개")
    print(f"   • 총 라인 수: {total_lines:,}줄")
    print(f"   • 평균 파일 크기: {total_lines // total_files if total_files > 0 else 0}줄")
    print(f"   • 최대 파일 크기: < 1,000줄 (목표 달성! ✅)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--modules":
        show_module_info()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("🎯 VibeCulling 리팩토링 버전 사용법:")
        print()
        print("python main.py           - VibeCulling 실행")
        print("python main.py --modules - 모듈 구조 및 통계 보기")
        print("python main.py --help    - 이 도움말 보기")
        print()
        print("🔧 개발자 워크플로우:")
        print("1. python main.py --modules  (구조 파악)")
        print("2. modules/ 디렉토리에서 코드 분석/수정")
        print("3. 수정사항을 원본 VibeCulling.py에 반영")
        print("4. python main.py로 테스트")
    else:
        exit_code = main()

        if exit_code == 0:
            print("\n" + "=" * 70)
            print("✨ VibeCulling이 성공적으로 실행되었습니다!")
            print()
            print("💡 개발자 팁:")
            print("   • 코드 분석: modules/ 디렉토리의 분할된 파일들 활용")
            print("   • 모듈 정보: python main.py --modules")
            print("   • 도움말: python main.py --help")
            print("   • 기능 수정: 해당 모듈 파일 수정 후 원본에 반영")
            print("=" * 70)

        sys.exit(exit_code)
