"""
UI 스케일 관리 모듈
해상도와 화면 비율에 따라 UI 크기를 동적으로 관리
"""

import os
import json
import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont, QFontMetrics, QGuiApplication
from PySide6.QtWidgets import QApplication
import sys

class UIScaleManager:
    """해상도와 화면 비율에 따라 UI 크기를 동적으로 관리하는 클래스"""

    NORMAL_SETTINGS = {
        "font_size": 10,
        "zoom_grid_font_size": 11,
        "filename_font_size": 11,
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
        "font_size": 9,
        "zoom_grid_font_size": 10,
        "filename_font_size": 10,
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

    _current_settings = NORMAL_SETTINGS.copy()

    @classmethod
    def initialize(cls):
        """애플리케이션 시작 시 UI 스케일을 최종 결정합니다."""
        try:
            screen = QGuiApplication.primaryScreen()
            if not screen:
                cls._current_settings = cls.NORMAL_SETTINGS.copy()
                logging.warning("스크린 정보를 가져올 수 없습니다. 기본 UI 스케일을 사용합니다.")
                return

            geo = screen.geometry()
            width, height = geo.width(), geo.height()

            # 기본 설정 선택
            if height < 1201:
                base_settings = cls.COMPACT_SETTINGS.copy()
                logging.info(f"낮은 해상도 감지 ({width}x{height}). 컴팩트 UI 스케일을 사용합니다.")
            else:
                base_settings = cls.NORMAL_SETTINGS.copy()
                logging.info(f"일반 해상도 감지 ({width}x{height}). 기본 UI 스케일을 사용합니다.")

            # 폰트 크기 조정 로직 (해상도 및 DPI)
            if width >= 3840 and base_settings["font_size"] < 11:
                base_settings["font_size"] += 1
                base_settings["zoom_grid_font_size"] += 1
                base_settings["filename_font_size"] += 1
                logging.info("4K 해상도 감지. 폰트 크기 +1 적용.")

            dpi_scale = cls._get_system_dpi_scale()
            if dpi_scale >= 2.0 and base_settings["font_size"] > 9:
                logging.info(f"시스템 DPI 배율 {dpi_scale * 100:.0f}% 감지. 폰트 크기 -1 적용.")
                base_settings["font_size"] -= 1
                base_settings["zoom_grid_font_size"] -= 1
                base_settings["filename_font_size"] -= 1
            elif dpi_scale == 1.0 and base_settings["font_size"] < 11:
                logging.info(f"시스템 DPI 배율 100% 감지. 폰트 크기 +1 적용.")
                base_settings["font_size"] += 1
                base_settings["zoom_grid_font_size"] += 1
                base_settings["filename_font_size"] += 1

            # 해상도 기반 너비 조정 (폰트 크기 조정 후)
            cls._update_settings_for_horizontal_resolution(base_settings, width, height)

            cls._current_settings = base_settings
            logging.info(f"UI 스케일 초기화 완료: 해상도={width}x{height}, "
                         f"최종 폰트 크기={base_settings['font_size']}")

        except Exception as e:
            logging.error(f"UIScaleManager 초기화 중 오류: {e}. 기본 UI 스케일을 사용합니다.")
            cls._current_settings = cls.NORMAL_SETTINGS.copy()

    @classmethod
    def is_compact_mode(cls):
        """현재 컴팩트 모드 여부를 반환합니다."""
        return cls._current_settings["font_size"] < 10

    @classmethod
    def get(cls, key, default=None):
        """설정값을 가져옵니다."""
        return cls._current_settings.get(key, default)

    @classmethod
    def get_margins(cls):
        """컨트롤 패널 마진을 반환합니다."""
        return cls._current_settings.get("control_panel_margins")

    @classmethod
    def get_font_size(cls):
        """기본 폰트 크기를 반환합니다."""
        return cls._current_settings.get("font_size")

    @classmethod
    def get_zoom_grid_font_size(cls):
        """줌 그리드 폰트 크기를 반환합니다."""
        return cls._current_settings.get("zoom_grid_font_size")

    @classmethod
    def get_filename_font_size(cls):
        """파일명 폰트 크기를 반환합니다."""
        return cls._current_settings.get("filename_font_size")

    @classmethod
    def _get_system_dpi_scale(cls):
        """시스템 DPI 스케일을 가져옵니다."""
        try:
            screen = QGuiApplication.primaryScreen()
            if screen:
                # 물리적 DPI와 논리적 DPI 비교하여 스케일 계산
                logical_dpi = screen.logicalDotsPerInch()
                physical_dpi = screen.physicalDotsPerInch()
                if physical_dpi > 0:
                    scale = logical_dpi / 96.0  # 96 DPI를 기준으로 스케일 계산
                    return max(1.0, scale)
            return 1.0
        except Exception as e:
            logging.warning(f"DPI 스케일 계산 실패: {e}")
            return 1.0

    @classmethod
    def _update_settings_for_horizontal_resolution(cls, base_settings, width, height):
        """가로 해상도에 따른 설정을 업데이트합니다."""
        try:
            # 매우 넓은 화면 (울트라와이드 등)에 대한 추가 조정
            if width >= 2560 and height < width * 0.6:  # 21:9 이상 비율
                # 울트라와이드 모니터 감지
                base_settings["control_panel_margins"] = (base_settings["control_panel_margins"][0] + 2,
                                                          base_settings["control_panel_margins"][1] + 2,
                                                          base_settings["control_panel_margins"][2] + 2,
                                                          base_settings["control_panel_margins"][3] + 2)
                logging.info("울트라와이드 화면 감지. 마진 증가.")

            # 매우 작은 화면에 대한 조정
            elif width < 1366 or height < 768:
                # 작은 화면에서는 모든 요소를 더 작게
                for key in base_settings:
                    if key.endswith("_size") and isinstance(base_settings[key], int):
                        base_settings[key] = max(8, base_settings[key] - 1)
                    elif key.endswith("_padding") and isinstance(base_settings[key], int):
                        base_settings[key] = max(2, base_settings[key] - 1)
                logging.info("작은 화면 감지. UI 요소 크기 감소.")

        except Exception as e:
            logging.warning(f"해상도 기반 설정 조정 실패: {e}")

    @classmethod
    def get_current_settings(cls):
        """현재 모든 설정을 반환합니다."""
        return cls._current_settings.copy()

    @classmethod
    def update_setting(cls, key, value):
        """특정 설정값을 업데이트합니다."""
        if key in cls._current_settings:
            cls._current_settings[key] = value
            logging.info(f"UI 스케일 설정 업데이트: {key}={value}")
            return True
        else:
            logging.warning(f"알 수 없는 UI 스케일 설정: {key}")
            return False

    @classmethod
    def reset_to_default(cls):
        """설정을 기본값으로 재설정합니다."""
        cls._current_settings = cls.NORMAL_SETTINGS.copy()
        logging.info("UI 스케일이 기본값으로 재설정되었습니다.")

    @classmethod
    def log_current_settings(cls):
        """현재 설정을 로그로 출력합니다."""
        logging.info("=== UI 스케일 설정 ===")
        for key, value in cls._current_settings.items():
            logging.info(f"{key}: {value}")
        logging.info("====================")
