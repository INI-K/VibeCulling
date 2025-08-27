"""
폴더 로더 워커 모듈
폴더에서 이미지 파일들을 로드하는 백그라운드 작업자
"""

import os
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot
import logging
from pathlib import Path
from typing import List


class FolderLoaderWorker(QObject):
    """백그라운드 스레드에서 폴더 스캔, 파일 매칭, 정렬 작업을 수행하는 워커"""
    startProcessing = Signal(str, str, str, list, list)
    
    finished = Signal(list, dict, str, str, str)
    progress = Signal(str)
    error = Signal(str, str)

    def __init__(self, raw_extensions, get_datetime_func):
        super().__init__()
        self.raw_extensions = raw_extensions
        self.get_datetime_from_file_fast = get_datetime_func
        self._is_running = True
        
        self.startProcessing.connect(self.process_folders)


    def stop(self):
        self._is_running = False

    @Slot(str, str, str, list, list)
    def process_folders(self, jpg_folder_path, raw_folder_path, mode, raw_file_list_from_main, supported_extensions):
        """메인 처리 함수 (mode에 따라 분기)"""
        self._is_running = True
        try:
            image_files = []
            raw_files = {}

            if mode == 'raw_only':
                self.progress.emit(LanguageManager.translate("RAW 파일 정렬 중..."))
                image_files = sorted(raw_file_list_from_main, key=self.get_datetime_from_file_fast)
            
            else: # 'jpg_with_raw' or 'jpg_only'
                self.progress.emit(LanguageManager.translate("이미지 파일 스캔 중..."))
                target_path = Path(jpg_folder_path)
                temp_image_files = []
                for file_path in target_path.iterdir():
                    if not self._is_running: return
                    if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                        temp_image_files.append(file_path)
                
                if not temp_image_files:
                    self.error.emit(LanguageManager.translate("선택한 폴더에 지원하는 이미지 파일이 없습니다."), LanguageManager.translate("경고"))
                    return

                self.progress.emit(LanguageManager.translate("파일 정렬 중..."))
                image_files = sorted(temp_image_files, key=self.get_datetime_from_file_fast)

                if mode == 'jpg_with_raw' and raw_folder_path:
                    self.progress.emit(LanguageManager.translate("RAW 파일 매칭 중..."))
                    jpg_filenames = {f.stem: f for f in image_files}
                    for file_path in Path(raw_folder_path).iterdir():
                        if not self._is_running: return
                        if file_path.is_file() and file_path.suffix.lower() in self.raw_extensions:
                            if file_path.stem in jpg_filenames:
                                raw_files[file_path.stem] = file_path
            
            if not self._is_running: return
            self.finished.emit(image_files, raw_files, jpg_folder_path, raw_folder_path, mode)

        except Exception as e:
            logging.error(f"백그라운드 폴더 로딩 중 오류: {e}")
            self.error.emit(str(e), LanguageManager.translate("오류"))

