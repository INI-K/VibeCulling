"""
EXIF 워커 모듈
이미지 메타데이터(EXIF) 정보 추출을 위한 백그라운드 작업자
"""

import os
import subprocess
import json
import threading
import logging
from PySide6.QtCore import QObject, Signal
from datetime import datetime
from PIL import Image
import rawpy
import piexif
from pathlib import Path
import sys


class ExifWorker(QObject):
    """백그라운드 스레드에서 EXIF 데이터를 처리하는 워커 클래스"""
    # 시그널 정의
    finished = Signal(dict, str)  # (EXIF 결과 딕셔너리, 이미지 경로)
    error = Signal(str, str)      # (오류 메시지, 이미지 경로)
    request_process = Signal(str)
    
    def __init__(self, raw_extensions, exiftool_path, exiftool_available):
        super().__init__()
        self.raw_extensions = raw_extensions
        self.exiftool_path = exiftool_path
        self.exiftool_available = exiftool_available
        self._running = True  # 작업 중단 플래그

        # 자신의 시그널을 슬롯에 연결
        self.request_process.connect(self.process_image)
    
    def stop(self):
        """워커의 실행을 중지"""
        self._running = False
    
    def get_exif_with_exiftool(self, image_path):
        """ExifTool을 사용하여 이미지 메타데이터 추출"""
        if not self.exiftool_available or not self._running:
            return {}
            
        try:
            # 중요: -g1 옵션 제거하고 일반 태그로 변경
            cmd = [self.exiftool_path, "-json", "-a", "-u", str(image_path)]
            # Windows에서 콘솔창 숨기기 위한 플래그 추가
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", 
                                    errors="replace", check=False, creationflags=creationflags)
            
            if process.returncode == 0 and process.stdout:
                try:
                    exif_data = json.loads(process.stdout)
                    # ExifTool은 결과를 항상 리스트로 반환
                    if exif_data and isinstance(exif_data, list):
                        return exif_data[0]
                    return {}
                except json.JSONDecodeError:
                    return {}
            else:
                return {}
        except Exception:
            return {}

    def process_image(self, image_path):
        """백그라운드에서 이미지의 EXIF 데이터 처리"""
        try:
            if not self._running:
                return
                
            file_path_obj = Path(image_path)
            suffix = file_path_obj.suffix.lower()
            is_raw = file_path_obj.suffix.lower() in self.raw_extensions
            is_heic = file_path_obj.suffix.lower() in {'.heic', '.heif'} 

            skip_piexif_formats = {'.heic', '.heif', '.png', '.webp', '.bmp'} # piexif 시도를 건너뛸 포맷 목록
            
            # 결과를 저장할 딕셔너리 초기화
            result = {
                "exif_resolution": None,
                "exif_make": "",
                "exif_model": "",
                "exif_datetime": None,
                "exif_focal_mm": None,
                "exif_focal_35mm": None,
                "exif_exposure_time": None,
                "exif_fnumber": None,
                "exif_iso": None,
                "exif_orientation": None,
                "image_path": image_path
            }
            
            # PHASE 0: RAW 파일인 경우 rawpy로 정보 추출
            if is_raw and self._running:
                try:
                    with rawpy.imread(image_path) as raw:
                        result["exif_resolution"] = (raw.sizes.raw_width, raw.sizes.raw_height)
                        if hasattr(raw, 'camera_manufacturer'):
                            result["exif_make"] = raw.camera_manufacturer.strip() if raw.camera_manufacturer else ""
                        if hasattr(raw, 'model'):
                            result["exif_model"] = raw.model.strip() if raw.model else ""
                        if hasattr(raw, 'timestamp') and raw.timestamp:
                            dt_obj = datetime.fromtimestamp(raw.timestamp)
                            result["exif_datetime"] = dt_obj.strftime('%Y:%m:%d %H:%M:%S')
                except Exception:
                    pass

            # PHASE 1: Piexif로 EXIF 정보 추출 시도
            piexif_success = False
            if self._running and suffix not in skip_piexif_formats: # HEIC 파일이면 piexif 시도 건너뛰기
                try:
                    # JPG 이미지 크기 (RAW는 위에서 추출)
                    if not is_raw and not result["exif_resolution"]:
                        try:
                            with Image.open(image_path) as img:
                                result["exif_resolution"] = img.size
                        except Exception:
                            pass
                    
                    exif_dict = piexif.load(image_path)
                    ifd0 = exif_dict.get("0th", {})
                    exif_ifd = exif_dict.get("Exif", {})

                    # Orientation
                    if piexif.ImageIFD.Orientation in ifd0:
                        try:
                            result["exif_orientation"] = int(ifd0.get(piexif.ImageIFD.Orientation))
                        except (ValueError, TypeError):
                            pass

                    # 카메라 정보
                    if not result["exif_make"] and piexif.ImageIFD.Make in ifd0:
                        result["exif_make"] = ifd0.get(piexif.ImageIFD.Make, b'').decode('utf-8', errors='ignore').strip()
                    if not result["exif_model"] and piexif.ImageIFD.Model in ifd0:
                        result["exif_model"] = ifd0.get(piexif.ImageIFD.Model, b'').decode('utf-8', errors='ignore').strip()

                    # 날짜 정보
                    if not result["exif_datetime"]:
                        if piexif.ExifIFD.DateTimeOriginal in exif_ifd:
                            result["exif_datetime"] = exif_ifd.get(piexif.ExifIFD.DateTimeOriginal, b'').decode('utf-8', errors='ignore')
                        elif piexif.ImageIFD.DateTime in ifd0:
                            result["exif_datetime"] = ifd0.get(piexif.ImageIFD.DateTime, b'').decode('utf-8', errors='ignore')

                    # 초점 거리
                    if result["exif_focal_mm"] is None and piexif.ExifIFD.FocalLength in exif_ifd:
                        val = exif_ifd.get(piexif.ExifIFD.FocalLength)
                        if isinstance(val, tuple) and len(val) == 2 and val[1] != 0:
                            result["exif_focal_mm"] = val[0] / val[1]
                    if result["exif_focal_35mm"] is None and piexif.ExifIFD.FocalLengthIn35mmFilm in exif_ifd:
                        result["exif_focal_35mm"] = exif_ifd.get(piexif.ExifIFD.FocalLengthIn35mmFilm)

                    # 노출 시간
                    if result["exif_exposure_time"] is None and piexif.ExifIFD.ExposureTime in exif_ifd:
                        val = exif_ifd.get(piexif.ExifIFD.ExposureTime)
                        if isinstance(val, tuple) and len(val) == 2 and val[1] != 0:
                            result["exif_exposure_time"] = val[0] / val[1]
                    
                    # 조리개값
                    if result["exif_fnumber"] is None and piexif.ExifIFD.FNumber in exif_ifd:
                        val = exif_ifd.get(piexif.ExifIFD.FNumber)
                        if isinstance(val, tuple) and len(val) == 2 and val[1] != 0:
                            result["exif_fnumber"] = val[0] / val[1]
                    
                    # ISO
                    if result["exif_iso"] is None and piexif.ExifIFD.ISOSpeedRatings in exif_ifd:
                        result["exif_iso"] = exif_ifd.get(piexif.ExifIFD.ISOSpeedRatings)

                    # 필수 정보 확인
                    required_info_count = sum([
                        result["exif_resolution"] is not None,
                        bool(result["exif_make"] or result["exif_model"]),
                        result["exif_datetime"] is not None
                    ])
                    piexif_success = required_info_count >= 2
                except Exception:
                    piexif_success = False

            # PHASE 2: ExifTool 필요 여부 확인 및 실행
            if not self._running:
                return
                
            needs_exiftool = False
            if self.exiftool_available:
                if is_heic: # HEIC 파일은 항상 ExifTool 필요
                    needs_exiftool = True
                elif is_raw and result["exif_orientation"] is None:
                    needs_exiftool = True
                elif not result["exif_resolution"]:
                    needs_exiftool = True
                elif not piexif_success:
                    needs_exiftool = True

            if needs_exiftool and self._running:
                exif_data_tool = self.get_exif_with_exiftool(image_path)
                if exif_data_tool:
                    # 해상도 정보
                    if not result["exif_resolution"]:
                        width = exif_data_tool.get("ImageWidth") or exif_data_tool.get("ExifImageWidth")
                        height = exif_data_tool.get("ImageHeight") or exif_data_tool.get("ExifImageHeight")
                        if width and height:
                            try:
                                result["exif_resolution"] = (int(width), int(height))
                            except (ValueError, TypeError):
                                pass
                    
                    # Orientation
                    if result["exif_orientation"] is None:
                        orientation_val = exif_data_tool.get("Orientation")
                        if orientation_val:
                            try:
                                result["exif_orientation"] = int(orientation_val)
                            except (ValueError, TypeError):
                                pass
                    
                    # 카메라 정보
                    if not (result["exif_make"] or result["exif_model"]):
                        result["exif_make"] = exif_data_tool.get("Make", "")
                        result["exif_model"] = exif_data_tool.get("Model", "")
                    
                    # 날짜 정보
                    if not result["exif_datetime"]:
                        date_str = (exif_data_tool.get("DateTimeOriginal") or
                                exif_data_tool.get("CreateDate") or
                                exif_data_tool.get("FileModifyDate"))
                        if date_str:
                            result["exif_datetime"] = date_str
                    
                    # 초점 거리
                    if result["exif_focal_mm"] is None:
                        focal_val = exif_data_tool.get("FocalLength")
                        if focal_val:
                            try:
                                result["exif_focal_mm"] = float(str(focal_val).lower().replace(" mm", ""))
                            except (ValueError, TypeError):
                                result["exif_focal_mm"] = str(focal_val)
                    
                    if result["exif_focal_35mm"] is None:
                        focal_35_val = exif_data_tool.get("FocalLengthIn35mmFormat")
                        if focal_35_val:
                            try:
                                result["exif_focal_35mm"] = float(str(focal_35_val).lower().replace(" mm", ""))
                            except (ValueError, TypeError):
                                result["exif_focal_35mm"] = str(focal_35_val)

                    # 노출 시간
                    if result["exif_exposure_time"] is None:
                        exposure_val = exif_data_tool.get("ExposureTime")
                        if exposure_val:
                            try:
                                result["exif_exposure_time"] = float(exposure_val)
                            except (ValueError, TypeError):
                                result["exif_exposure_time"] = str(exposure_val)
                    
                    # 조리개값
                    if result["exif_fnumber"] is None:
                        fnumber_val = exif_data_tool.get("FNumber")
                        if fnumber_val:
                            try:
                                result["exif_fnumber"] = float(fnumber_val)
                            except (ValueError, TypeError):
                                result["exif_fnumber"] = str(fnumber_val)
                    
                    # ISO
                    if result["exif_iso"] is None:
                        iso_val = exif_data_tool.get("ISO")
                        if iso_val:
                            try:
                                result["exif_iso"] = int(iso_val)
                            except (ValueError, TypeError):
                                result["exif_iso"] = str(iso_val)

            # 작업 완료, 결과 전송
            if self._running:
                self.finished.emit(result, image_path)
            
        except Exception as e:
            # 오류 발생, 오류 메시지 전송
            if self._running:
                self.error.emit(str(e), image_path)

