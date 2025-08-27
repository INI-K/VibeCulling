"""
카메라 유틸리티 모듈
카메라 제조사 및 모델명 포맷팅 함수들
"""

# 필요한 import 구문을 추가합니다.
import re


def format_camera_name(make, model):
    make_str = (make or "").strip()
    model_str = (model or "").strip()
    # 1. OLYMPUS IMAGING CORP. → OLYMPUS로 치환
    if make_str.upper() == "OLYMPUS IMAGING CORP.":
        make_str = "OLYMPUS"
    # 2. RICOH가 make에 있으면 make 생략
    if "RICOH" in make_str.upper():
        make_str = ""
    if make_str.upper().find("NIKON") != -1 and model_str.upper().startswith("NIKON"):
        return model_str
    if make_str.upper().find("CANON") != -1 and model_str.upper().startswith("CANON"):
        return model_str
    return f"{make_str} {model_str}".strip()

