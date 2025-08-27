"""
UI 스케일 관리 모듈
해상도와 화면 비율에 따라 UI 크기를 동적으로 관리
"""

import os
import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication


class UIScaleManager:
    """해상도와 화면 비율에 따라 UI 크기를 동적으로 관리하는 클래스"""

    # min/max 너비 개념을 다시 사용합니다.
    NORMAL_SETTINGS = {
        "control_panel_margins": (8, 9, 8, 9),     # 컨트롤 패널 내부 여백 (좌, 상, 우, 하)
        "control_layout_spacing": 8,               # 컨트롤 레이아웃 위젯 간 기본 간격
        "button_padding": 7,                       # 버튼 내부 패딩
        "delete_button_width": 45,                 # 분류폴더 번호 및 삭제(X) 버튼 너비
        "JPG_RAW_spacing": 8,                      # JPG와 RAW 폴더 섹션 사이 간격
        "section_spacing": 20,                     # 구분선(HorizontalLine) 주변 간격
        "group_box_spacing": 15,                   # 라디오 버튼 등 그룹 내 간격
        "title_spacing": 10,                       # Zoom, Grid 등 섹션 제목 아래 간격
        "settings_button_size": 35,                # 설정(톱니바퀴) 버튼 크기
        "filename_label_padding": 40,              # 파일명 레이블 상하 패딩
        "info_label_padding": 5,                   # 파일 정보 레이블 좌측 패딩
        "font_size": 10,                           # 기본 폰트 크기
        "zoom_grid_font_size": 11,                 # Zoom, Grid 등 섹션 제목 폰트 크기
        "filename_font_size": 11,                  # 파일명 폰트 크기
        "folder_container_spacing": 6,             # 분류폴더 번호버튼 - 레이블 - X버튼 간격
        "folder_label_padding": 20,                # 폴더 경로 레이블 높이 계산용 패딩
        "sort_folder_label_padding": 25,           # 분류폴더 레이블 패딩
        "category_folder_vertical_spacing": 10,    # 분류 폴더 UI 사이 간격
        "info_container_width": 300,               # 파일 정보 컨테이너 너비
        "settings_label_width": 250,               # 설정 창 라벨 최소 너비
        "control_panel_min_width": 362,            # 컨트롤 패널 최소 너비
        "control_panel_max_width": 550,            # 컨트롤 패널 최대 너비 (범위로 설정)
        "combobox_padding": 5,                     # 콤보박스 내부 패딩
        "spinbox_padding": 3,                      # 스핀박스 내부 패딩
        "radiobutton_size": 13,                    # 라디오 버튼 인디케이터 크기
        "radiobutton_border": 2,                   # 라디오 버튼 테두리 두께
        "radiobutton_border_radius": 8,            # 라디오 버튼 둥근 모서리
        "radiobutton_padding": 0,                  # 라디오 버튼 전체 패딩
        "checkbox_size": 12,                       # 체크박스 인디케이터 크기
        "checkbox_border": 2,                      # 체크박스 테두리 두께
        "checkbox_border_radius": 2,               # 체크박스 둥근 모서리
        "checkbox_padding": 0,                     # 체크박스 전체 패딩
        "settings_popup_width": 1280,              # 설정 창 너비
        "settings_popup_height": 1120,             # 설정 창 높이
        "settings_layout_vspace": 18,              # 설정 창 항목 간 세로 간격
        "settings_group_title_spacing": 15,        # 설정 창 그룹 제목 아래 간격
        "infotext_licensebutton": 30,              # 정보 텍스트와 라이선스 버튼 사이 간격
        "donation_between_tworows": 25,            # 후원 QR 코드 행 사이 간격
        "bottom_space": 25,                        # (현재 미사용)
        "info_version_margin": 30,                 # 정보 텍스트: 버전 아래 여백
        "info_paragraph_margin": 30,               # 정보 텍스트: 문단 아래 여백
        "info_bottom_margin": 30,                  # 정보 텍스트: Copyright 아래 여백
        "info_donation_spacing": 35,               # 정보 섹션과 후원 섹션 사이 간격
        "thumbnail_image_size": 150,               # 썸네일 이미지 크기
        "thumbnail_item_height": 195,              # 썸네일 아이템 높이
        "thumbnail_item_spacing": 2,               # 썸네일 아이템 간 간격
        "thumbnail_text_height": 24,               # 썸네일 파일명 텍스트 영역 높이
        "thumbnail_padding": 6,                    # 썸네일 이미지와 파일명 사이 간격
        "thumbnail_border_width": 2,               # 썸네일 테두리 두께
        "thumbnail_panel_min_width": 197,          # 썸네일 패널 최소 너비
        "thumbnail_panel_max_width": 300,          # 썸네일 패널 최대 너비 (범위로 설정)
        "compare_filename_padding": 5,             # 비교 모드 파일명 패딩
        "shortcuts_popup_height": 1030,            # 단축키 팝업 높이
    }
    COMPACT_SETTINGS = {
        "control_panel_margins": (6, 6, 6, 6),     # 컨트롤 패널 내부 여백 (좌, 상, 우, 하)
        "control_layout_spacing": 6,               # 컨트롤 레이아웃 위젯 간 기본 간격
        "button_padding": 6,                       # 버튼 내부 패딩
        "delete_button_width": 35,                 # 분류폴더 번호 및 삭제(X) 버튼 너비
        "JPG_RAW_spacing": 6,                      # JPG와 RAW 폴더 섹션 사이 간격
        "section_spacing": 12,                     # 구분선(HorizontalLine) 주변 간격
        "group_box_spacing": 10,                   # 라디오 버튼 등 그룹 내 간격
        "title_spacing": 7,                        # Zoom, Grid 등 섹션 제목 아래 간격
        "settings_button_size": 25,                # 설정(톱니바퀴) 버튼 크기
        "filename_label_padding": 25,              # 파일명 레이블 상하 패딩
        "info_label_padding": 5,                   # 파일 정보 레이블 좌측 패딩
        "font_size": 9,                            # 기본 폰트 크기
        "zoom_grid_font_size": 10,                 # Zoom, Grid 등 섹션 제목 폰트 크기
        "filename_font_size": 10,                  # 파일명 폰트 크기
        "folder_container_spacing": 4,             # 분류폴더 번호버튼 - 레이블 - X버튼 간격
        "folder_label_padding": 10,                # 폴더 경로 레이블 높이 계산용 패딩
        "sort_folder_label_padding": 20,           # 분류폴더 레이블 패딩
        "category_folder_vertical_spacing": 6,     # 분류 폴더 UI 사이 간격
        "info_container_width": 200,               # 파일 정보 컨테이너 너비
        "settings_label_width": 180,               # 설정 창 라벨 최소 너비
        "control_panel_min_width": 290,            # 컨트롤 패널 최소 너비
        "control_panel_max_width": 450,            # 컨트롤 패널 최대 너비 (범위로 설정)
        "combobox_padding": 4,                     # 콤보박스 내부 패딩
        "spinbox_padding": 1,                      # 스핀박스 내부 패딩
        "radiobutton_size": 9,                     # 라디오 버튼 인디케이터 크기
        "radiobutton_border": 2,                   # 라디오 버튼 테두리 두께
        "radiobutton_border_radius": 6,            # 라디오 버튼 둥근 모서리
        "radiobutton_padding": 0,                  # 라디오 버튼 전체 패딩
        "checkbox_size": 8,                        # 체크박스 인디케이터 크기
        "checkbox_border": 2,                      # 체크박스 테두리 두께
        "checkbox_border_radius": 1,               # 체크박스 둥근 모서리
        "checkbox_padding": 0,                     # 체크박스 전체 패딩
        "settings_popup_width": 1000,              # 설정 창 너비
        "settings_popup_height": 870,              # 설정 창 높이
        "settings_layout_vspace": 12,              # 설정 창 항목 간 세로 간격
        "settings_group_title_spacing": 10,        # 설정 창 그룹 제목 아래 간격
        "infotext_licensebutton": 20,              # 정보 텍스트와 라이선스 버튼 사이 간격
        "donation_between_tworows": 17,            # 후원 QR 코드 행 사이 간격
        "bottom_space": 15,                        # (현재 미사용)
        "info_version_margin": 20,                 # 정보 텍스트: 버전 아래 여백
        "info_paragraph_margin": 20,               # 정보 텍스트: 문단 아래 여백
        "info_bottom_margin": 20,                  # 정보 텍스트: Copyright 아래 여백
        "info_donation_spacing": 25,               # 정보 섹션과 후원 섹션 사이 간격
        "thumbnail_image_size": 110,               # 썸네일 이미지 크기
        "thumbnail_item_height": 145,              # 썸네일 아이템 높이
        "thumbnail_item_spacing": 1,               # 썸네일 아이템 간 간격
        "thumbnail_text_height": 20,               # 썸네일 파일명 텍스트 영역 높이
        "thumbnail_padding": 5,                    # 썸네일 이미지와 파일명 사이 간격
        "thumbnail_border_width": 1,               # 썸네일 테두리 두께
        "thumbnail_panel_min_width": 145,          # 썸네일 패널 최소 너비
        "thumbnail_panel_max_width": 250,          # 썸네일 패널 최대 너비 (범위로 설정)
        "compare_filename_padding": 5,             # 비교 모드 파일명 패딩
        "shortcuts_popup_height": 920,            # 단축키 팝업 높이
    }

    _current_settings = NORMAL_SETTINGS

    @classmethod
    def _calculate_thumbnail_metrics(cls, image_size):
        """주어진 썸네일 이미지 크기를 기반으로 관련 UI 수치들을 계산합니다."""
        metrics = {}
        image_size = int(image_size)
        metrics["thumbnail_image_size"] = image_size
        
        panel_min_width = int(image_size * 1.31)
        metrics["thumbnail_panel_min_width"] = panel_min_width
        metrics["thumbnail_panel_max_width"] = int(panel_min_width * 1.5)
        
        text_height = max(20, int(24 * (image_size / 150.0)))
        metrics["thumbnail_text_height"] = text_height
        metrics["thumbnail_item_height"] = panel_min_width + text_height + 10

        scale_factor = image_size / 150.0
        metrics["thumbnail_padding"] = max(5, int(6 * scale_factor))
        metrics["thumbnail_item_spacing"] = max(1, int(2 * scale_factor))
        metrics["thumbnail_border_width"] = max(1, int(2 * scale_factor))
        
        return metrics

    @classmethod
    def _get_system_dpi_scale(cls):
        """Qt의 스케일링 비활성화와 무관하게 실제 시스템의 DPI 배율을 가져옵니다."""
        if sys.platform == "win32":
            try:
                # Windows API를 직접 호출하여 DPI를 가져옵니다.
                import ctypes
                user32 = ctypes.windll.user32
                # 화면 전체에 대한 Device Context를 가져옵니다.
                hdc = user32.GetDC(0)
                # LOGPIXELSX(88)는 수평 DPI, LOGPIXELSY(90)는 수직 DPI입니다.
                # 보통 두 값은 같으므로 하나만 사용합니다.
                current_dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
                user32.ReleaseDC(0, hdc)
                # Windows의 표준 DPI는 96입니다.
                scale = current_dpi / 96.0
                logging.info(f"Windows API로 감지된 DPI 배율: {scale:.2f} ({current_dpi} DPI)")
                return scale
            except Exception as e:
                logging.error(f"Windows DPI 배율 감지 실패: {e}. 기본값 1.0 사용.")
                return 1.0
        else:
            # Windows가 아닌 OS에서는 devicePixelRatio가 정상적으로 동작할 가능성이 높습니다.
            screen = QGuiApplication.primaryScreen()
            if screen:
                scale = screen.devicePixelRatio()
                logging.info(f"Qt API로 감지된 DPI 배율: {scale:.2f}")
                return scale
            return 1.0

    @classmethod
    def _update_settings_for_horizontal_resolution(cls, settings, width, height):
        aspect_ratio = width / height if height > 0 else 16/9
        if abs(aspect_ratio - 1.6) < 0.05:
            if width == 2560:
                settings["thumbnail_panel_min_width"], settings["control_panel_min_width"] = 197, 316
            elif width == 1920:
                settings["thumbnail_panel_min_width"], settings["control_panel_min_width"] = 145, 220
            return
        if width >= 3440:
            thumbnail_metrics = cls._calculate_thumbnail_metrics(width * 0.058)
            settings.update(thumbnail_metrics)
            settings["control_panel_min_width"] = 380

