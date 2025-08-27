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
from .ui_scale import UIScaleManager


class ThemeManager:
    """현재 테마를 관리하고 테마 변경 시 관련된 모든 ui 요소에 변경 사항을 반영하는 클래스."""

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
            QCheckBox::indicator {{
                width: {UIScaleManager.get("checkbox_size", 12)}px;
                height: {UIScaleManager.get("checkbox_size", 12)}px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {cls.get_color('accent')};
                border: 1px solid {cls.get_color('accent')};
                border-radius: 2px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {cls.get_color('bg_primary')};
                border: 1px solid {cls.get_color('border')};
                border-radius: 2px;
            }}
            QCheckBox::indicator:unchecked:hover {{
                border: 1px solid {cls.get_color('text_disabled')};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                border: 1px solid {cls.get_color('text_disabled')};
            }}
        """

    @classmethod
    def generate_main_button_style(cls):
        """현재 테마에 맞는 기본 버튼 스타일시트를 생성합니다."""
        return f"""
            QPushButton {{
                background-color: {cls.get_color('bg_secondary')};
                color: {cls.get_color('text')};
                border: none;
                padding: 6px;
                border-radius: 1px;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('bg_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('bg_pressed')};
            }}
            QPushButton:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                color: {cls.get_color('text_disabled')};
            }}
        """

    @classmethod
    def get_color(cls, color_key):
        """현재 테마에서 색상 코드 가져오기"""
        return cls.THEMES[cls._current_theme].get(color_key, "#FFFFFF")

    @classmethod
    def set_theme(cls, theme_name):
        """테마 변경하고 모든 콜백 함수 호출"""
        if theme_name in cls.THEMES:
            cls._current_theme = theme_name
            # 모든 콜백 함수 호출
            for callback in cls._theme_change_callbacks:
                try:
                    callback()
                except Exception as e:
                    logging.warning(f"테마 변경 콜백 실행 중 오류: {e}")
            return True
        return False

    @classmethod
    def register_theme_change_callback(cls, callback):
        """테마 변경 시 호출될 콜백 함수 등록"""
        if callable(callback) and callback not in cls._theme_change_callbacks:
            cls._theme_change_callbacks.append(callback)

    @classmethod
    def get_current_theme_name(cls):
        """현재 테마 이름 반환"""
        return cls._current_theme

    @classmethod
    def get_available_themes(cls):
        """사용 가능한 모든 테마 이름 목록 반환"""
        return list(cls.THEMES.keys())

    @classmethod
    def initialize(cls, theme_name="default"):
        """테마 매니저 초기화"""
        if theme_name in cls.THEMES:
            cls._current_theme = theme_name
        else:
            cls._current_theme = "default"
        logging.info(f"테마 매니저 초기화 완료: {cls._current_theme}")
