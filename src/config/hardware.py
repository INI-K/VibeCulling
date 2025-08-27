"""
하드웨어 프로파일 관리 모듈
시스템 메모리 사용량 및 하드웨어 성능에 따른 최적화 설정
"""

import logging
import sys
import psutil
from PySide6.QtCore import QObject, Signal
from pathlib import Path


class HardwareProfileManager:
    """시스템 하드웨어 및 예상 사용 시나리오를 기반으로 성능 프로필을 결정하고 관련 파라미터를 제공하는 클래스."""

    _profile = "balanced"
    _system_memory_gb = 8
    _cpu_cores = 4

    PROFILES = {
        "conservative": {
            "name": "저사양 (8GB RAM)",
            "max_imaging_threads": 2,
            "max_raw_processes": 1,
            "cache_size_images": 30,
            "preload_range_adjacent": (5, 2),
            "preload_range_priority": 2,
            "preload_grid_bg_limit_factor": 0.3,
            "memory_thresholds": {"danger": 88, "warning": 82, "caution": 75},
            "cache_clear_ratios": {"danger": 0.5, "warning": 0.3, "caution": 0.15},
            "idle_preload_enabled": False,
            "idle_interval_ms": 3000,
        },
        "balanced": {
            "name": "일반 (16GB RAM)",
            "max_imaging_threads": 4,
            "max_raw_processes": 2,
            "cache_size_images": 60,
            "preload_range_adjacent": (8, 4),
            "preload_range_priority": 4,
            "preload_grid_bg_limit_factor": 0.5,
            "memory_thresholds": {"danger": 90, "warning": 85, "caution": 80},
            "cache_clear_ratios": {"danger": 0.6, "warning": 0.4, "caution": 0.2},
            "idle_preload_enabled": True,
            "idle_interval_ms": 2000,
        },
        "performance": {
            "name": "고성능 (32GB+ RAM)",
            "max_imaging_threads": 8,
            "max_raw_processes": 4,
            "cache_size_images": 120,
            "preload_range_adjacent": (12, 6),
            "preload_range_priority": 8,
            "preload_grid_bg_limit_factor": 0.7,
            "memory_thresholds": {"danger": 92, "warning": 88, "caution": 85},
            "cache_clear_ratios": {"danger": 0.7, "warning": 0.5, "caution": 0.3},
            "idle_preload_enabled": True,
            "idle_interval_ms": 1500,
        }
    }

    @classmethod
    def initialize(cls):
        """시스템 정보를 수집하고 적절한 프로필을 자동으로 설정합니다."""
        try:
            # 시스템 메모리 정보
            memory = psutil.virtual_memory()
            cls._system_memory_gb = round(memory.total / (1024 ** 3))

            # CPU 코어 수
            cls._cpu_cores = psutil.cpu_count(logical=False) or 4

            # 메모리 기준으로 프로필 자동 선택
            if cls._system_memory_gb <= 8:
                cls._profile = "conservative"
            elif cls._system_memory_gb <= 24:
                cls._profile = "balanced"
            else:
                cls._profile = "performance"

            logging.info(f"하드웨어 프로필 초기화 완료: {cls._profile} "
                         f"(메모리: {cls._system_memory_gb}GB, CPU: {cls._cpu_cores}코어)")

        except Exception as e:
            logging.warning(f"하드웨어 프로필 초기화 실패: {e}, 기본값 사용")
            cls._profile = "balanced"
            cls._system_memory_gb = 16
            cls._cpu_cores = 4

    @classmethod
    def set_profile(cls, profile_name):
        """프로필을 수동으로 설정합니다."""
        if profile_name in cls.PROFILES:
            cls._profile = profile_name
            logging.info(f"하드웨어 프로필 변경: {profile_name}")
            return True
        else:
            logging.warning(f"알 수 없는 프로필: {profile_name}")
            return False

    @classmethod
    def get_current_profile(cls):
        """현재 프로필 이름을 반환합니다."""
        return cls._profile

    @classmethod
    def get_profile_info(cls, profile_name=None):
        """프로필 정보를 반환합니다."""
        target_profile = profile_name or cls._profile
        return cls.PROFILES.get(target_profile, cls.PROFILES["balanced"])

    @classmethod
    def get(cls, key, profile_name=None):
        """특정 설정값을 가져옵니다."""
        profile_info = cls.get_profile_info(profile_name)
        return profile_info.get(key)

    @classmethod
    def get_max_imaging_threads(cls):
        """최대 이미징 스레드 수를 반환합니다."""
        return cls.get("max_imaging_threads")

    @classmethod
    def get_max_raw_processes(cls):
        """최대 RAW 프로세스 수를 반환합니다."""
        return cls.get("max_raw_processes")

    @classmethod
    def get_cache_size_images(cls):
        """이미지 캐시 크기를 반환합니다."""
        return cls.get("cache_size_images")

    @classmethod
    def get_preload_range_adjacent(cls):
        """인접 이미지 사전로드 범위를 반환합니다."""
        return cls.get("preload_range_adjacent")

    @classmethod
    def get_preload_range_priority(cls):
        """우선순위 사전로드 범위를 반환합니다."""
        return cls.get("preload_range_priority")

    @classmethod
    def get_preload_grid_bg_limit_factor(cls):
        """그리드 배경 로드 제한 계수를 반환합니다."""
        return cls.get("preload_grid_bg_limit_factor")

    @classmethod
    def get_memory_thresholds(cls):
        """메모리 임계값들을 반환합니다."""
        return cls.get("memory_thresholds")

    @classmethod
    def get_cache_clear_ratios(cls):
        """캐시 클리어 비율들을 반환합니다."""
        return cls.get("cache_clear_ratios")

    @classmethod
    def is_idle_preload_enabled(cls):
        """유휴 시간 사전로드 활성화 여부를 반환합니다."""
        return cls.get("idle_preload_enabled")

    @classmethod
    def get_idle_interval_ms(cls):
        """유휴 시간 간격(밀리초)을 반환합니다."""
        return cls.get("idle_interval_ms")

    @classmethod
    def get_system_info(cls):
        """시스템 정보를 반환합니다."""
        return {
            "memory_gb": cls._system_memory_gb,
            "cpu_cores": cls._cpu_cores,
            "current_profile": cls._profile,
            "profile_name": cls.get("name")
        }

    @classmethod
    def get_all_profiles(cls):
        """모든 프로필 정보를 반환합니다."""
        return cls.PROFILES

    @classmethod
    def log_current_settings(cls):
        """현재 설정을 로그로 출력합니다."""
        profile_info = cls.get_profile_info()
        system_info = cls.get_system_info()

        logging.info("=== 하드웨어 프로필 설정 ===")
        logging.info(f"시스템: {system_info['memory_gb']}GB RAM, {system_info['cpu_cores']}코어")
        logging.info(f"프로필: {system_info['current_profile']} ({system_info['profile_name']})")
        logging.info(f"이미징 스레드: {profile_info['max_imaging_threads']}")
        logging.info(f"RAW 프로세스: {profile_info['max_raw_processes']}")
        logging.info(f"이미지 캐시: {profile_info['cache_size_images']}")
        logging.info(f"사전로드 범위: {profile_info['preload_range_adjacent']}")
        logging.info(f"유휴 사전로드: {profile_info['idle_preload_enabled']}")
        logging.info("==========================")
