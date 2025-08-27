"""
리소스 매니저 모듈
메모리 사용량 모니터링 및 리소스 관리
"""

import gc
import time
import threading
import logging
from PySide6.QtCore import QObject, Signal
import psutil


class ResourceManager:
    """스레드 풀과 프로세스 풀을 통합 관리하는 싱글톤 클래스"""
    _instance = None
    
    @classmethod
    def instance(cls):
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = ResourceManager()
        return cls._instance
    
    def __init__(self):
        """리소스 매니저 초기화"""
        if ResourceManager._instance is not None:
            raise RuntimeError("ResourceManager는 싱글톤입니다. instance() 메서드를 사용하세요.")

        # HardwareProfileManager에서 직접 파라미터 가져오기
        HardwareProfileManager.initialize() # 앱의 이 시점에서 초기화
        max_imaging_threads = HardwareProfileManager.get("max_imaging_threads")
        raw_processes = HardwareProfileManager.get("max_raw_processes")

        # 통합 이미징 스레드 풀
        self.imaging_thread_pool = PriorityThreadPoolExecutor(
            max_workers=max_imaging_threads,
            thread_name_prefix="Imaging"
        )
        # RAW 디코더 프로세스 풀
        self.raw_decoder_pool = RawDecoderPool(num_processes=raw_processes)
        
        self.active_tasks = set()
        self.pending_tasks = {}
        self._running = True
        logging.info(f"ResourceManager 초기화 ({HardwareProfileManager.get_current_profile_name()}): 이미징 스레드 {max_imaging_threads}개, RAW 디코더 프로세스 {raw_processes}개")
        
        # 작업 모니터링 타이머 (이 부분은 유지)
        self.monitor_timer = QTimer()
        self.monitor_timer.setInterval(5000)
        self.monitor_timer.timeout.connect(self.monitor_resources)
        self.monitor_timer.start()

    def monitor_resources(self):
        """시스템 리소스 사용량 모니터링 및 필요시 조치"""
        if not self._running:
            return
            
        try:
            # 현재 메모리 사용량 확인
            memory_percent = psutil.virtual_memory().percent
            
            # 메모리 사용량이 95%를 초과할 경우만 긴급 정리 (기존 90%에서 상향)
            if memory_percent > 95:
                print(f"심각한 메모리 부족 감지 ({memory_percent}%): 긴급 조치 수행")
                # 우선순위 낮은 작업 취소
                self.cancel_low_priority_tasks()
                
                # 가비지 컬렉션 명시적 호출
                gc.collect()
        except:
            pass  # psutil 사용 불가 등의 예외 상황 무시

    def cancel_low_priority_tasks(self):
        """우선순위가 낮은 작업 취소"""
        # low 우선순위 작업 전체 취소
        if 'low' in self.pending_tasks:
            for task in list(self.pending_tasks['low']):
                task.cancel()
            self.pending_tasks['low'] = []
            
        # 필요시 medium 우선순위 작업 일부 취소 (최대 절반)
        if 'medium' in self.pending_tasks and len(self.pending_tasks['medium']) > 4:
            # 절반만 유지
            keep = len(self.pending_tasks['medium']) // 2
            to_cancel = self.pending_tasks['medium'][keep:]
            self.pending_tasks['medium'] = self.pending_tasks['medium'][:keep]
            
            for task in to_cancel:
                task.cancel()

    
    def submit_imaging_task_with_priority(self, priority, fn, *args, **kwargs):
        """이미지 처리 작업을 우선순위와 함께 제출"""
        if not self._running:
            return None
            
        # 우선순위 스레드 풀에 작업 제출
        if isinstance(self.imaging_thread_pool, PriorityThreadPoolExecutor):
            
            future = self.imaging_thread_pool.submit_with_priority(priority, fn, *args, **kwargs)
            if future: # 반환된 future가 유효한지 확인 (선택적이지만 안전함)
                self.active_tasks.add(future)
                future.add_done_callback(lambda f: self.active_tasks.discard(f))
            return future

        else:
            # 우선순위 지원하지 않으면 일반 제출
            return self.submit_imaging_task(fn, *args, **kwargs)


    def submit_imaging_task(self, fn, *args, **kwargs):
        """이미지 처리 작업 제출 (일반)"""
        if not self._running:
            return None
            
        future = self.imaging_thread_pool.submit(fn, *args, **kwargs)
        self.active_tasks.add(future)
        future.add_done_callback(lambda f: self.active_tasks.discard(f))
        return future
    
    def submit_raw_decoding(self, file_path, callback):
        """RAW 디코딩 작업 제출"""
        if not self._running:
            return None
        return self.raw_decoder_pool.decode_raw(file_path, callback)
    
    def process_raw_results(self, max_results=5):
        """RAW 디코딩 결과 처리"""
        if not self._running:
            return 0
        return self.raw_decoder_pool.process_results(max_results)
    
    def cancel_all_tasks(self):
        """모든 활성 작업 취소"""
        logging.info("ResourceManager: 모든 작업 취소 중...")
        
        # 1. 활성 스레드 풀 작업 취소
        # PriorityThreadPoolExecutor의 경우, 내부 큐를 직접 비워야 합니다.
        if isinstance(self.imaging_thread_pool, PriorityThreadPoolExecutor):
            for q in self.imaging_thread_pool.task_queues.values():
                while not q.empty():
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break
            logging.info("PriorityThreadPoolExecutor의 작업 큐를 비웠습니다.")

        for future in list(self.active_tasks):
            future.cancel()
        self.active_tasks.clear()
        
        # 2. RAW 디코더 풀 작업 취소 (input_queue 비우기 추가)
        if hasattr(self, 'raw_decoder_pool') and self.raw_decoder_pool:
            try:
                # 입력 큐를 비워 더 이상 작업이 할당되지 않도록 합니다.
                while not self.raw_decoder_pool.input_queue.empty():
                    try:
                        self.raw_decoder_pool.input_queue.get_nowait()
                    except queue.Empty:
                        break
                
                # 출력 큐에 남아있는 결과도 비웁니다.
                while not self.raw_decoder_pool.output_queue.empty():
                    try:
                        self.raw_decoder_pool.output_queue.get_nowait()
                    except queue.Empty:
                        break
                        
                # 콜백을 기다리는 작업 추적 정보도 모두 비웁니다.
                self.raw_decoder_pool.tasks.clear()
                logging.info("RAW 디코더 작업 큐 및 작업 추적 정보 초기화됨")
            except Exception as e:
                logging.error(f"RAW 디코더 풀 작업 취소 중 오류: {e}")
        
        logging.info("ResourceManager: 모든 작업 취소 완료")

    
    def shutdown(self):
        """모든 리소스 종료"""
        if not self._running:
            return
            
        print("ResourceManager: 리소스 종료 중...")
        self._running = False # 종료 플래그 설정
        
        # 활성 작업 취소 (기존 로직 유지)
        self.cancel_all_tasks() 
        
        # 스레드 풀 종료
        logging.info("ResourceManager: 이미징 스레드 풀 종료 시도 (wait=True)...")
        self.imaging_thread_pool.shutdown(wait=True, cancel_futures=True)
        logging.info("ResourceManager: 이미징 스레드 풀 종료 완료.")
        
        # RAW 디코더 풀 종료 (기존 로직 유지)
        self.raw_decoder_pool.shutdown()
        
        print("ResourceManager: 리소스 종료 완료")

