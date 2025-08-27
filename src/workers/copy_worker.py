"""
복사 워커 모듈  
선택된 파일들을 다른 폴더로 복사하는 백그라운드 작업자
"""

import os
import shutil
import queue
import threading
import logging
from PySide6.QtCore import QObject, Signal


class CopyWorker(QObject):
    """백그라운드 스레드에서 파일 복사를 순차적으로 처리하는 워커"""
    copyFinished = Signal(str)
    copyFailed = Signal(str) # <-- 실패 신호 추가

    def __init__(self, copy_queue, parent_app):
        super().__init__()
        self.copy_queue = copy_queue
        self.parent_app = parent_app
        self._is_running = True

    def stop(self):
        self._is_running = False

    def _copy_single_file(self, source_path, target_folder):
        """파일을 대상 폴더로 복사하고, 이름 충돌 시 새 이름을 부여합니다."""
        if not source_path or not target_folder:
            return None, "Source or target is missing." # 오류 메시지 반환
        target_dir = Path(target_folder)
        target_path = target_dir / source_path.name

        if target_path.exists():
            counter = 1
            while True:
                new_name = f"{source_path.stem}_{counter}{source_path.suffix}"
                new_target_path = target_dir / new_name
                if not new_target_path.exists():
                    target_path = new_target_path
                    break
                counter += 1
        
        try:
            shutil.copy2(str(source_path), str(target_path))
            logging.info(f"파일 복사: {source_path} -> {target_path}")
            return target_path, None # 성공 시 (경로, None) 반환
        except Exception as e:
            error_message = f"{source_path.name}: {str(e)}"
            logging.error(f"파일 복사 실패: {error_message}")
            return None, error_message # 실패 시 (None, 오류 메시지) 반환

    @Slot()
    def process_queue(self):
        """큐에 작업이 들어올 때까지 대기하고, 작업을 순차적으로 처리합니다."""
        while self._is_running:
            try:
                task = self.copy_queue.get()

                if task is None or not self._is_running:
                    break

                files_to_copy, target_folder, raw_files_dict, copy_raw_flag = task
                
                copied_count = 0
                failed_files = []
                for jpg_path in files_to_copy:
                    _, error = self._copy_single_file(jpg_path, target_folder)
                    if error:
                        failed_files.append(error)
                    else:
                        copied_count += 1
                        if copy_raw_flag:
                            raw_path = raw_files_dict.get(jpg_path.stem)
                            if raw_path:
                                _, raw_error = self._copy_single_file(raw_path, target_folder)
                                if raw_error:
                                    failed_files.append(raw_error)

                if failed_files:
                    fail_msg_key = "다음 파일 복사에 실패했습니다:\n\n"
                    self.copyFailed.emit(LanguageManager.translate(fail_msg_key) + "\n".join(failed_files))

                if copied_count > 0:
                    if len(files_to_copy) == 1:
                        filename = files_to_copy[0].name
                        msg_key = "{filename} 복사 완료"
                        message = LanguageManager.translate(msg_key).format(filename=filename)
                    else:
                        msg_key = "이미지 {count}개 복사 완료"
                        message = LanguageManager.translate(msg_key).format(count=copied_count)
                    
                    self.copyFinished.emit(message)

            except Exception as e:
                logging.error(f"CopyWorker 처리 중 오류: {e}")



