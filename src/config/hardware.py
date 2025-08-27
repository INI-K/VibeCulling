"""
하드웨어 프로파일 관리 모듈
시스템 메모리 사용량 및 하드웨어 성능에 따른 최적화 설정
"""

import logging
import sys
import psutil
from PySide6.QtCore import QObject, Signal
from pathlib import Path


class ThemeManager:
    """현재 테마를 관리하고 테마 변경 시 관련된 모든 ui 요소에 변경 사항을 반영하는 클래스."""

    THEMES = {
        "light": {
            "bg_primary": "#F0F0F0",
            "bg_secondary": "#FFFFFF",
            "text": "#000000",
            "text_disabled": "#AAAAAA",
            "accent": "#03A9F4",
            "accent_hover": "#0277BD",
            "accent_pressed": "#01579B",
            "border": "#DDDDDD",
        },
        "dark": {
            "bg_primary": "#2F2F2F",
            "bg_secondary": "#3F3F3F",
            "text": "#FFFFFF",
            "text_disabled": "#AAAAAA",
            "accent": "#03A9F4",
            "accent_hover": "#0277BD",
            "accent_pressed": "#01579B",
            "border": "#555555",
        }
    }

    _current_theme = "light"
    _theme_change_callbacks = []

    @classmethod
    def generate_checkbox_style(cls):
        """현재 테마에 맞는 체크박스 스타일시트를 생성합니다."""
        return f"""
            QCheckBox:disabled {{
                color: {cls.get_color('text_disabled')};
            }}
            QCheckBox::indicator {{
                width: {UIScaleManager.get("checkbox_size")}px;
                height: {UIScaleManager.get("checkbox_size")}px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {cls.get_color('accent')};
                border: {UIScaleManager.get("checkbox_border")}px solid {cls.get_color('accent')};
                border-radius: {UIScaleManager.get("checkbox_border_radius")}px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {cls.get_color('bg_primary')};
                border: {UIScaleManager.get("checkbox_border")}px solid {cls.get_color('border')};
                border-radius: {UIScaleManager.get("checkbox_border_radius")}px;
            }}
            QCheckBox::indicator:unchecked:hover {{
                border: {UIScaleManager.get("checkbox_border")}px solid {cls.get_color('text_disabled')};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                border: {UIScaleManager.get("checkbox_border")}px solid {cls.get_color('text_disabled')};
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
                padding: {UIScaleManager.get("button_padding")}px;
                border-radius: 1px;
                min-height: {UIScaleManager.get("button_min_height")}px;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('accent_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('accent_pressed')};
            }}
            QPushButton:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                color: {cls.get_color('text_disabled')};
                opacity: 0.7;
            }}
        """

    @classmethod
    def generate_dynamic_height_button_style(cls):
        """수직 패딩이 없고 수평 패딩만 있는 버튼 스타일을 생성합니다."""
        horizontal_padding = UIScaleManager.get("button_padding")
        return f"""
            QPushButton {{
                background-color: {cls.get_color('bg_secondary')};
                color: {cls.get_color('text')};
                border: none;
                /* 수직 패딩은 0, 수평 패딩은 유지 */
                padding: 0px {horizontal_padding}px;
                border-radius: 1px;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('accent_hover')};
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('accent_pressed')};
            }}
            QPushButton:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                color: {cls.get_color('text_disabled')};
                opacity: 0.7;
            }}
        """

    @classmethod
    def generate_action_button_style(cls):
        """현재 테마에 맞는 액션 버튼(X, ✓) 스타일시트를 생성합니다."""
        return f"""
            QPushButton {{
                background-color: {cls.get_color('bg_secondary')};
                color: {cls.get_color('text')};
                border: none;
                padding: 4px;
                border-radius: 1px;
                min-height: {UIScaleManager.get("button_min_height")}px;
            }}
            QPushButton:hover {{
                background-color: {cls.get_color('accent_hover')};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {cls.get_color('accent_pressed')};
                color: white;
            }}
            QPushButton:disabled {{
                background-color: {cls.get_color('bg_disabled')};
                color: {cls.get_color('text_disabled')};
            }}
        """

    @classmethod
    def get_color(cls, color_key):
        """현재 테마에서 색상 코드 가져오기"""
        return cls.THEMES[cls._current_theme][color_key]
    
    @classmethod
    def set_theme(cls, theme_name):
        """테마 변경하고 모든 콜백 함수 호출"""
        if theme_name in cls.THEMES:
            cls._current_theme = theme_name
            # 모든 콜백 함수 호출
            for callback in cls._theme_change_callbacks:
                callback()
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

class HardwareProfileManager:
    """시스템 하드웨어 및 예상 사용 시나리오를 기반으로 성능 프로필을 결정하고 관련 파라미터를 제공하는 클래스."""
    
    _profile = "balanced"
    _system_memory_gb = 8
    _cpu_cores = 4

    PROFILES = {
        "conservative": {
            "name": "저사양 (8GB RAM)",
            "max_imaging_threads": 2, "max_raw_processes": 1, "cache_size_images": 30,
            "preload_range_adjacent": (5, 2), "preload_range_priority": 2, "preload_grid_bg_limit_factor": 0.3,
            "memory_thresholds": {"danger": 88, "warning": 82, "caution": 75},
            "cache_clear_ratios": {"danger": 0.5, "warning": 0.3, "caution": 0.15},
            "idle_preload_enabled": False,
