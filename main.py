#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VibeCulling - 사진 컬링 애플리케이션
메인 실행 파일
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 로깅 설정 초기화
from src import setup_logger

logger = setup_logger()

# 메인 애플리케이션 실행
if __name__ == "__main__":
    from src.controllers import main

    main()
