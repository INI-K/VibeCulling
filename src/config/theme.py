"""
테마 관리 모듈
다크/라이트 테마 설정 및 색상 관리
"""

import os
import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


class UIScaleManager:
    NORMAL_SETTINGS = {
        "font_size": 10,
        "zoom_grid_font_size": 10,
        "filename_font_size": 10,
        "control_panel_margins": 8,
        "radiobutton_padding": 4,
        "radiobutton_size": 12,
        "radiobutton_border": 1,
        "radiobutton_border_radius": 6,
        "checkbox_padding": 4,
    }
    COMPACT_SETTINGS = {
        "font_size": 9,
        "zoom_grid_font_size": 9,
        "filename_font_size": 9,
        "control_panel_margins": 6,
        "radiobutton_padding": 3,
        "radiobutton_size": 10,
        "radiobutton_border": 1,
        "radiobutton_border_radius": 5,
        "checkbox_padding": 3,
    }

    _current_settings = NORMAL_SETTINGS.copy()

    @classmethod
    def initialize(cls):
        """애플리케이션 시작 시 UI 스케일을 최종 결정합니다."""
        try:
            screen = QGuiApplication.primaryScreen()
            if not screen:
                cls._current_settings = cls.NORMAL_SETTINGS.copy()
                return

            geo = screen.geometry()
            width, height = geo.width(), geo.height()

            if height < 1201:
                base_settings = cls.COMPACT_SETTINGS.copy()
            else:
                base_settings = cls.NORMAL_SETTINGS.copy()
            
            # 폰트 크기 조정 로직 (해상도 및 DPI)
            if width >= 3840 and base_settings["font_size"] < 11:
                base_settings["font_size"] += 1; base_settings["zoom_grid_font_size"] += 1; base_settings["filename_font_size"] += 1

            dpi_scale = cls._get_system_dpi_scale()
            if dpi_scale >= 2.0 and base_settings["font_size"] > 9:
                logging.info(f"시스템 DPI 배율 {dpi_scale*100:.0f}% 감지. 폰트 크기 -1 적용.")
                base_settings["font_size"] -= 1; base_settings["zoom_grid_font_size"] -= 1; base_settings["filename_font_size"] -= 1
            elif dpi_scale == 1.0 and base_settings["font_size"] < 11:
                logging.info(f"시스템 DPI 배율 100% 감지. 폰트 크기 +1 적용.")
                base_settings["font_size"] += 2; base_settings["zoom_grid_font_size"] += 2; base_settings["filename_font_size"] += 2

            # 해상도 기반 너비 조정 (폰트 크기 조정 후)
            cls._update_settings_for_horizontal_resolution(base_settings, width, height)
            
            cls._current_settings = base_settings
            logging.info(f"UI 스케일 초기화 완료: 해상도={width}x{height}, 최종 폰트 크기={base_settings['font_size']}")

        except Exception as e:
            logging.error(f"UIScaleManager 초기화 중 오류: {e}. 기본 UI 스케일을 사용합니다.")
            cls._current_settings = cls.NORMAL_SETTINGS.copy()

    @classmethod
    def is_compact_mode(cls):
        return cls._current_settings["font_size"] < 10

    @classmethod
    def get(cls, key, default=None):
        return cls._current_settings.get(key, default)

    @classmethod
    def get_margins(cls):
        return cls._current_settings.get("control_panel_margins")

    @classmethod
    def _get_system_dpi_scale(cls):
        # DPI 스케일을 얻는 로직을 구현해야 합니다.
        # 현재는 임시로 1.0을 반환합니다.
        return 1.0

    @classmethod
    def _update_settings_for_horizontal_resolution(cls, base_settings, width, height):
        # 가로 해상도에 따른 설정을 업데이트합니다.
        # 현재는 임시로 아무런 처리도 하지 않습니다.
        pass


class ThemeManager:

    _UI_COLORS_DEFAULT = {
        "accent": "#848484",        # 강조색
        "accent_hover": "#555555",  # 강조색 호버 상태(밝음)
        "accent_pressed": "#222222",# 강조색 눌림 상태(어두움)
        "text": "#D8D8D8",          # 일반 텍스트 색상
        "text_disabled": "#595959", # 비활성화된 텍스트 색상
        "bg_primary": "#333333",    # 기본 배경색
        "bg_secondary": "#444444",  # 버튼 등 배경색
        "bg_hover": "#555555",      # 호버 시 배경색
        "bg_pressed": "#222222",    # 눌림 시 배경색
        "bg_disabled": "#222222",   # 비활성화 배경색
        "border": "#555555",        # 테두리 색상
    }
    _UI_COLORS_SONY = {
        "accent": "#FF6600",
        "accent_hover": "#FF6600",
        "accent_pressed": "#CC5200",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_NIKON = {
        "accent": "#FFE100",
        "accent_hover": "#FFE100",
        "accent_pressed": "#CCB800",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_CANON = {
        "accent": "#CC0000",
        "accent_hover": "#CC0000",
        "accent_pressed": "#A30000",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_FUJIFILM = {
        "accent": "#01916D",
        "accent_hover": "#01916D",
        "accent_pressed": "#016954",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_PANASONIC = {
        "accent": "#0041C0",
        "accent_hover": "#0041C0",
        "accent_pressed": "#002D87",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_LEICA = {
        "accent": "#E20612",
        "accent_hover": "#E20612",
        "accent_pressed": "#B00000",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_OLYMPUS = {
        "accent": "#08107B",
        "accent_hover": "#08107B",
        "accent_pressed": "#050A5B",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_SAMSUNG = {
        "accent": "#1428A0",
        "accent_hover": "#1428A0",
        "accent_pressed": "#101F7A",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_PENTAX = {
        "accent": "#01CA47",
        "accent_hover": "#01CA47",
        "accent_pressed": "#019437",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }
    _UI_COLORS_RICOH = {
        "accent": "#D61B3E",
        "accent_hover": "#D61B3E",
        "accent_pressed": "#B00030",
        "text": "#D8D8D8",
        "text_disabled": "#595959",
        "bg_primary": "#333333",
        "bg_secondary": "#444444",
        "bg_hover": "#555555",
        "bg_pressed": "#222222",
        "bg_disabled": "#222222",
        "border": "#555555",
    }   

    # 모든 테마 저장
    THEMES = {
        "default": _UI_COLORS_DEFAULT,
        "SONY": _UI_COLORS_SONY,
        "CANON": _UI_COLORS_CANON,
        "NIKON": _UI_COLORS_NIKON,
        "FUJIFILM": _UI_COLORS_FUJIFILM,
        "PANASONIC": _UI_COLORS_PANASONIC,
        "RICOH": _UI_COLORS_RICOH,
        "LEICA": _UI_COLORS_LEICA,
        "OLYMPUS": _UI_COLORS_OLYMPUS,
        "PENTAX": _UI_COLORS_PENTAX,
        "SAMSUNG": _UI_COLORS_SAMSUNG,
    }
    
    _current_theme = "default"  # 현재 테마
    _theme_change_callbacks = []  # 테마 변경 시 호출할 콜백 함수 목록
    
    @classmethod
    def generate_radio_button_style(cls):
        """현재 테마와 UI 스케일에 맞는 라디오 버튼 스타일시트를 생성합니다."""
        return f"""
            QRadioButton {{
                color: {cls.get_color('text')};
                padding: {UIScaleManager.get("radiobutton_padding")}px;
            }}
            QRadioButton::indicator {{
                width: {UIScaleManager.get("radiobutton_size")}px;
                height: {UIScaleManager.get("radiobutton_size")}px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {cls.get_color('accent')};
                border: {UIScaleManager.get("radiobutton_border")}px solid {cls.get_color('accent')};
                border-radius: {UIScaleManager.get("radiobutton_border_radius")}px;
            }}
            QRadioButton::indicator:unchecked {{
                background-color: {cls.get_color('bg_primary')};
                border: {UIScaleManager.get("radiobutton_border")}px solid {cls.get_color('border')};
                border-radius: {UIScaleManager.get("radiobutton_border_radius")}px;
            }}
            QRadioButton::indicator:unchecked:hover {{
                border: {UIScaleManager.get("radiobutton_border")}px solid {cls.get_color('text_disabled')};
            }}
        """

    @classmethod
    def generate_checkbox_style(cls):
        """현재 테마와 UI 스케일에 맞는 체크박스 스타일시트를 생성합니다."""
        return f"""
            QCheckBox {{
                color: {cls.get_color('text')};
                padding: {UIScaleManager.get("checkbox_padding")}px;
            }}
        """
