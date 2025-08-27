"""
로컬라이제이션 관리 모듈
언어 설정 및 날짜 형식 관리
"""

import os
import json
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal
import psutil
import logging


class PerformanceManager:
    """성능 프로필을 관리하는 클래스"""

    # 성능 프로필 정보
    PROFILES = {
        "conservative": {
            "name": "최소 (4GB RAM)",
            "max_imaging_threads": 1, "max_raw_processes": lambda cores: min(1, max(1, cores // 4)),
            "cache_size_images": 30,
            "preload_range_adjacent": (4, 2), "preload_range_priority": 2, "preload_grid_bg_limit_factor": 0.3,
            "memory_thresholds": {"danger": 90, "warning": 85, "caution": 80},
            "cache_clear_ratios": {"danger": 0.6, "warning": 0.4, "caution": 0.2},
            "idle_preload_enabled": False, "idle_interval_ms": 3000,
        },
        "balanced": {
            "name": "표준 (16GB RAM)",
            "max_imaging_threads": 3, "max_raw_processes": lambda cores: min(2, max(1, cores // 4)), "cache_size_images": 60,
            "preload_range_adjacent": (8, 3), "preload_range_priority": 3, "preload_grid_bg_limit_factor": 0.5,
            "memory_thresholds": {"danger": 92, "warning": 88, "caution": 80},
            "cache_clear_ratios": {"danger": 0.5, "warning": 0.3, "caution": 0.15},
            "idle_preload_enabled": True, "idle_interval_ms": 2200,
        },
        "enhanced": {
            "name": "상급 (24GB RAM)",
            "max_imaging_threads": 4, "max_raw_processes": lambda cores: min(2, max(1, cores // 4)), "cache_size_images": 80,
            "preload_range_adjacent": (10, 4), "preload_range_priority": 4, "preload_grid_bg_limit_factor": 0.6,
            "memory_thresholds": {"danger": 94, "warning": 90, "caution": 85},
            "cache_clear_ratios": {"danger": 0.5, "warning": 0.3, "caution": 0.15},
            "idle_preload_enabled": True, "idle_interval_ms": 1800,
        },
        "aggressive": {
            "name": "고성능 (32GB RAM)",
            "max_imaging_threads": 4, "max_raw_processes": lambda cores: min(3, max(2, cores // 3)), "cache_size_images": 120,
            "preload_range_adjacent": (12, 5), "preload_range_priority": 5, "preload_grid_bg_limit_factor": 0.75,
            "memory_thresholds": {"danger": 95, "warning": 92, "caution": 88},
            "cache_clear_ratios": {"danger": 0.4, "warning": 0.25, "caution": 0.1},
            "idle_preload_enabled": True, "idle_interval_ms": 1500,
        },
        "extreme": {
            "name": "초고성능 (64GB RAM)",
            "max_imaging_threads": 4, "max_raw_processes": lambda cores: min(4, max(2, cores // 3)), "cache_size_images": 150,
            "preload_range_adjacent": (18, 6), "preload_range_priority": 6, "preload_grid_bg_limit_factor": 0.8,
            "memory_thresholds": {"danger": 96, "warning": 94, "caution": 90},
            "cache_clear_ratios": {"danger": 0.4, "warning": 0.2, "caution": 0.1},
            "idle_preload_enabled": True, "idle_interval_ms": 1200,
        },
        "dominator": {
            "name": "워크스테이션 (96GB+ RAM)",
            "max_imaging_threads": 5, "max_raw_processes": lambda cores: min(8, max(4, cores // 3)), "cache_size_images": 200,
            "preload_range_adjacent": (20, 8), "preload_range_priority": 7, "preload_grid_bg_limit_factor": 0.9,
            "memory_thresholds": {"danger": 97, "warning": 95, "caution": 92},
            "cache_clear_ratios": {"danger": 0.3, "warning": 0.15, "caution": 0.05},
            "idle_preload_enabled": True, "idle_interval_ms": 800,
        }
    }

    @classmethod
    def initialize(cls):
        try:
            cls._system_memory_gb = psutil.virtual_memory().total / (1024 ** 3)
            physical_cores = psutil.cpu_count(logical=False)
            logical_cores = psutil.cpu_count(logical=True)
            cls._cpu_cores = physical_cores if physical_cores is not None and physical_cores > 0 else logical_cores
        except Exception:
            cls._profile = "conservative"
            logging.warning("시스템 사양 확인 실패. 보수적인 성능 프로필을 사용합니다.")
            return
        
        if cls._system_memory_gb >= 90:
            cls._profile = "dominator"
        elif cls._system_memory_gb >= 45:
            cls._profile = "extreme"
        elif cls._system_memory_gb >= 30:
            cls._profile = "aggressive"
        elif cls._system_memory_gb >= 22:
            cls._profile = "enhanced"
        elif cls._system_memory_gb >= 12:
            cls._profile = "balanced"
        else:
            cls._profile = "conservative"
        
        logging.info(f"시스템 사양: {cls._system_memory_gb:.1f}GB RAM, {cls._cpu_cores} Cores. 성능 프로필 '{cls.PROFILES[cls._profile]['name']}' 활성화.")

    @classmethod
    def get(cls, key):
        param = cls.PROFILES[cls._profile].get(key)
        if callable(param):
            return param(cls._cpu_cores)
        return param

    @classmethod
    def get_current_profile_name(cls):
        return cls.PROFILES[cls._profile]["name"]

    @classmethod
    def get_current_profile_key(cls):
        return cls._profile

    @classmethod
    def set_profile_manually(cls, profile_key):
        if profile_key in cls.PROFILES:
            cls._profile = profile_key
            logging.info(f"사용자가 성능 프로필을 수동으로 '{cls.PROFILES[profile_key]['name']}'(으)로 변경했습니다.")
            return True
        return False

class LanguageManager:
    """언어 설정 및 번역을 관리하는 클래스"""
    
    # 사용 가능한 언어
    LANGUAGES = {
        "en": "English",
        "ko": "한국어"
    }
    
    # 번역 데이터
    _translations = {
        "en": {},  # 영어 번역 데이터는 아래에서 초기화
        "ko": {}   # 한국어는 기본값이므로 필요 없음
    }
    
    _current_language = "en"  # 기본 언어
    _language_change_callbacks = []  # 언어 변경 시 호출할 콜백 함수 목록
    
    @classmethod
    def initialize_translations(cls, translations_data):
        """번역 데이터 초기화"""
        # 영어는 key-value 반대로 저장 (한국어->영어 매핑)
        for ko_text, en_text in translations_data.items():
            cls._translations["en"][ko_text] = en_text
    
    @classmethod
    def translate(cls, text_id):
        """텍스트 ID에 해당하는 번역 반환"""
        if cls._current_language == "ko":
            return text_id  # 한국어는 원래 ID 그대로 사용
        
        translations = cls._translations.get(cls._current_language, {})
        return translations.get(text_id, text_id)  # 번역 없으면 원본 반환
    
    @classmethod
    def set_language(cls, language_code):
        """언어 설정 변경"""
        if language_code in cls.LANGUAGES:
            cls._current_language = language_code
            # 언어 변경 시 콜백 함수 호출
            for callback in cls._language_change_callbacks:
                callback()
            return True
        return False
    
    @classmethod
    def register_language_change_callback(cls, callback):
        """언어 변경 시 호출될 콜백 함수 등록"""
        if callable(callback) and callback not in cls._language_change_callbacks:
            cls._language_change_callbacks.append(callback)
    
    @classmethod
    def get_current_language(cls):
        """현재 언어 코드 반환"""
        return cls._current_language
    
    @classmethod
    def get_available_languages(cls):
        """사용 가능한 언어 목록 반환"""
        return list(cls.LANGUAGES.keys())
    
    @classmethod
    def get_language_name(cls, language_code):
        """언어 코드에 해당하는 언어 이름 반환"""
        return cls.LANGUAGES.get(language_code, language_code)

class DateFormatManager:
    """날짜 형식 설정을 관리하는 클래스"""
    
    # 날짜 형식 정보
    DATE_FORMATS = {
        "yyyy-mm-dd": "YYYY-MM-DD",
        "mm/dd/yyyy": "MM/DD/YYYY",
        "dd/mm/yyyy": "DD/MM/YYYY"
    }
    
    # 형식별 실제 변환 패턴
    _format_patterns = {
        "yyyy-mm-dd": "%Y-%m-%d",
        "mm/dd/yyyy": "%m/%d/%Y",
        "dd/mm/yyyy": "%d/%m/%Y"
    }
    
    _current_format = "yyyy-mm-dd"  # 기본 형식
    _format_change_callbacks = []  # 형식 변경 시 호출할 콜백 함수
    
    @classmethod
    def format_date(cls, date_str):
        """날짜 문자열을 현재 설정된 형식으로 변환"""
        if not date_str:
            return "▪ -"
        
        # 기존 형식(YYYY:MM:DD HH:MM:SS)에서 datetime 객체로 변환
        try:
            # EXIF 날짜 형식 파싱 (콜론 포함)
            if ":" in date_str:
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            else:
                # 콜론 없는 형식 시도 (다른 포맷의 가능성)
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            
            # 현재 설정된 형식으로 변환하여 반환
            pattern = cls._format_patterns.get(cls._current_format, "%Y-%m-%d")
            # 시간 정보 추가
            return f"▪ {dt.strftime(pattern)} {dt.strftime('%H:%M:%S')}"
        except (ValueError, TypeError) as e:
            # 다른 형식 시도 (날짜만 있는 경우)
            try:
                if ":" in date_str:
                    dt = datetime.strptime(date_str.split()[0], "%Y:%m:%d")
                else:
                    dt = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                pattern = cls._format_patterns.get(cls._current_format, "%Y-%m-%d")
                return f"▪ {dt.strftime(pattern)}"
            except (ValueError, TypeError):
                # 형식이 맞지 않으면 원본 반환
                return f"▪ {date_str}"
    
    @classmethod
    def set_date_format(cls, format_code):
        """날짜 형식 설정 변경"""
        if format_code in cls.DATE_FORMATS:
            cls._current_format = format_code
            # 형식 변경 시 콜백 함수 호출
            for callback in cls._format_change_callbacks:
                callback()
            return True
        return False
    
    @classmethod
    def register_format_change_callback(cls, callback):
        """날짜 형식 변경 시 호출될 콜백 함수 등록"""
        if callable(callback) and callback not in cls._format_change_callbacks:
            cls._format_change_callbacks.append(callback)
    
    @classmethod
    def get_current_format(cls):
        """현재 날짜 형식 코드 반환"""
        return cls._current_format
    
    @classmethod
    def get_available_formats(cls):
        """사용 가능한 날짜 형식 목록 반환"""
        return list(cls.DATE_FORMATS.keys())
    
    @classmethod
    def get_format_display_name(cls, format_code):
        """날짜 형식 코드에 해당하는 표시 이름 반환"""
        return cls.DATE_FORMATS.get(format_code, format_code)

