"""
유틸리티 모듈
"""

from .threading import PriorityThreadPoolExecutor
from .raw_decoder import RawDecoderPool, decode_raw_in_process
from .camera import format_camera_name
from .app_data import get_app_data_dir


# 플랫폼별 기능
def apply_dark_title_bar(widget):
    """다크 타이틀 바 적용 (macOS/Windows 호환)"""
    import logging
    try:
        if hasattr(widget, 'winId'):
            # 플랫폼별 다크 타이틀 바 구현
            pass
    except Exception as e:
        logging.warning(f"다크 타이틀 바 적용 실패: {e}")


__all__ = [
    'PriorityThreadPoolExecutor',
    'RawDecoderPool',
    'decode_raw_in_process',
    'format_camera_name',
    'get_app_data_dir',
    'apply_dark_title_bar'
]
