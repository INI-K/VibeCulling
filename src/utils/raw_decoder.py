"""
RAW 디코더 유틸리티 모듈
RAW 이미지 파일 디코딩을 위한 멀티프로세싱 풀
"""

import multiprocessing
import queue
import logging
from multiprocessing import Process, Queue
import rawpy
from PIL import Image
import numpy as np
import os
from multiprocessing import cpu_count


def decode_raw_in_process(input_queue, output_queue):
    """별도 프로세스에서 RAW 파일을 디코딩하는 워커 함수"""
    import rawpy
    from PIL import Image
    import numpy as np
    import logging

    while True:
        try:
            # 작업 큐에서 항목 가져오기
            item = input_queue.get()
            if item is None:
                # 종료 신호
                break

            file_path, task_id = item

            try:
                # RAW 파일 열기 및 디코딩
                with rawpy.imread(file_path) as raw:
                    # 기본 설정으로 RGB 배열 생성
                    rgb = raw.postprocess(
                        use_camera_wb=True,
                        half_size=False,
                        no_auto_bright=False,
                        output_bps=8
                    )

                # NumPy 배열을 PIL Image로 변환
                height, width = rgb.shape[:2]
                pil_image = Image.fromarray(rgb, 'RGB')

                # 성공 결과
                result = {
                    'task_id': task_id,
                    'success': True,
                    'image': pil_image,
                    'width': width,
                    'height': height,
                    'error': None
                }

            except Exception as e:
                # 디코딩 실패
                result = {
                    'task_id': task_id,
                    'success': False,
                    'image': None,
                    'width': 0,
                    'height': 0,
                    'error': str(e)
                }
                logging.error(f"RAW 디코딩 실패 ({file_path}): {e}")

            # 결과를 출력 큐에 전송
            output_queue.put(result)

        except Exception as e:
            logging.error(f"RAW 디코더 프로세스 오류: {e}")
            # 프로세스 오류 발생시에도 결과를 전송하여 무한 대기 방지
            try:
                error_result = {
                    'task_id': task_id if 'task_id' in locals() else -1,
                    'success': False,
                    'image': None,
                    'width': 0,
                    'height': 0,
                    'error': f"프로세스 오류: {str(e)}"
                }
                output_queue.put(error_result)
            except:
                pass


class RawDecoderPool:
    """RAW 디코더 프로세스 풀"""
    def __init__(self, num_processes=None):
        if num_processes is None:
        # 코어 수에 비례하되 상한선 설정
            available_cores = cpu_count()
            num_processes = min(2, max(1, available_cores // 4))
            # 8코어: 2개, 16코어: 4개, 32코어: 8개로 제한
            
        logging.info(f"RawDecoderPool 초기화: {num_processes}개 프로세스")
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.processes = []
        
        # 디코더 프로세스 시작
        for i in range(num_processes):
            p = Process(
                target=decode_raw_in_process, 
                args=(self.input_queue, self.output_queue),
                daemon=True  # 메인 프로세스가 종료하면 함께 종료
            )
            p.start()
            logging.info(f"RAW 디코더 프로세스 #{i+1} 시작됨 (PID: {p.pid})")
            self.processes.append(p)
        
        self.next_task_id = 0
        self.tasks = {}  # task_id -> callback
        self._running = True
    
    def decode_raw(self, file_path, callback):
        """RAW 디코딩 요청 (비동기)"""
        if not self._running:
            print("RawDecoderPool이 이미 종료됨")
            return None
        
        task_id = self.next_task_id
        self.next_task_id += 1
        self.tasks[task_id] = callback
        
        print(f"RAW 디코딩 요청: {os.path.basename(file_path)} (task_id: {task_id})")
        self.input_queue.put((file_path, task_id))
        return task_id
    
    def process_results(self, max_results=5):
        """완료된 결과 처리 (메인 스레드에서 주기적으로 호출)"""
        if not self._running:
            return 0
            
        processed = 0
        while processed < max_results:
            try:
                # non-blocking 확인
                if self.output_queue.empty():
                    break
                    
                result = self.output_queue.get_nowait()
                task_id = result['task_id']
                
                if task_id in self.tasks:
                    callback = self.tasks.pop(task_id)
                    # 성공 여부와 관계없이 콜백 호출
                    callback(result)
                else:
                    logging.warning(f"경고: task_id {task_id}에 대한 콜백을 찾을 수 없음")
                
                processed += 1
                
            except Exception as e:
                logging.error(f"결과 처리 중 오류: {e}")
                break
                
        return processed
    
    def shutdown(self):
        """프로세스 풀 종료"""
        if not self._running:
            print("RawDecoderPool이 이미 종료됨")
            return
            
        print("RawDecoderPool 종료 중...")
        self._running = False
        
        # 모든 프로세스에 종료 신호 전송
        for _ in range(len(self.processes)):
            try:
                self.input_queue.put(None, timeout=0.1) # 타임아웃 추가
            except queue.Full:
                pass # 큐가 꽉 차서 넣을 수 없어도 계속 진행
        
        # 프로세스 종료 대기
        for i, p in enumerate(self.processes):
            p.join(0.5)  # 각 프로세스별로 최대 0.5초 대기
            if p.is_alive():
                logging.info(f"프로세스 #{i+1} (PID: {p.pid})이 응답하지 않아 강제 종료")
                p.terminate()
                p.join(0.1) # 강제 종료 후 정리 시간
                
        self.processes.clear()
        self.tasks.clear()
        
        # 큐 닫기 (자원 누수 방지)
        self.input_queue.close()
        self.output_queue.close()
        
        logging.info("RawDecoderPool 종료 완료")

