# -*- coding: utf-8 -*-
"""
비디오 프레임 추출 옵션 모듈
- 비디오에서 프레임을 추출하는 옵션 UI 제공
- 오른쪽 패널에 표시
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, 
    QCheckBox, QLineEdit, QPushButton, QRadioButton, QButtonGroup, QApplication
)
from PySide6.QtCore import Qt, QBuffer, QIODevice, QRect, QThread, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from pathlib import Path
import subprocess
import tempfile
import os
import shutil
import sys
import urllib.request
import zipfile
import platform

# 전역 커스텀 UI 클래스 import
try:
    main_module = sys.modules.get('__main__')
    if main_module and hasattr(main_module, 'CustomSpinBox'):
        CustomSpinBox = main_module.CustomSpinBox
        CustomComboBox = main_module.CustomComboBox
    else:
        # fallback: 기본 클래스 사용
        CustomSpinBox = QSpinBox
        CustomComboBox = QComboBox
except:
    CustomSpinBox = QSpinBox
    CustomComboBox = QComboBox

# 세팅 모듈 스타일의 체크박스 클래스
class CustomCheckBox(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 12px;
                font-family: 'Segoe UI';
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 2px;
                border: 1px solid rgba(255, 255, 255, 0.8);
                background: rgba(17, 17, 27, 0.9);
            }
            QCheckBox::indicator:checked {
                background: rgba(17, 17, 27, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.8);
                image: none;
            }
            QCheckBox::indicator:hover {
                border: 1px solid rgba(255, 255, 255, 1.0);
            }
            QCheckBox:disabled {
                color: #6B7280;
            }
            QCheckBox::indicator:disabled {
                border: 1px solid rgba(75,85,99,0.2);
                background: rgba(26,27,38,0.4);
            }
        """)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.isChecked():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 비활성화 상태에 따른 색상 설정
            if self.isEnabled():
                check_color = QColor("#FFFFFF")  # 활성화: 흰색
            else:
                check_color = QColor("#6B7280")  # 비활성화: 회색
            
            # 체크 표시 그리기
            painter.setPen(QPen(check_color, 2))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            
            # 체크박스 영역 계산
            rect = self.rect()
            indicator_rect = QRect(1, (rect.height() - 14) // 2, 14, 14)
            
            # 체크 표시 (🗸) 그리기
            painter.drawText(indicator_rect, Qt.AlignCenter, "🗸")


class FFmpegWorker(QThread):
    """FFmpeg 실행을 위한 Worker 스레드"""
    progress_updated = Signal(int, str)  # 진행률, 메시지
    finished = Signal(list)  # 추출된 프레임 데이터
    error = Signal(str)  # 오류 메시지
    
    def __init__(self, cmd, expected_frames, temp_dir, format_ext):
        super().__init__()
        self.cmd = cmd
        self.expected_frames = expected_frames
        self.temp_dir = temp_dir
        self.format_ext = format_ext
        self._is_running = True
    
    def stop(self):
        """스레드 중지"""
        self._is_running = False
    
    def run(self):
        """FFmpeg 실행"""
        try:
            print(f"🔧 FFmpeg 명령 (Worker): {' '.join(self.cmd)}")
            
            # Popen으로 실행하여 실시간 출력 파싱
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1
            )
            
            # stderr에서 진행률 파싱
            stderr_lines = []
            frame_count = 0
            import time
            last_ui_update_time = 0
            
            # 실시간으로 stderr 읽기
            while self._is_running:
                line = process.stderr.readline()
                if not line:
                    # 프로세스가 종료되었는지 확인
                    if process.poll() is not None:
                        break
                    # 아직 실행 중이면 잠시 대기 후 계속
                    time.sleep(0.01)
                    continue
                
                stderr_lines.append(line)
                
                # frame= 패턴에서 프레임 번호 추출
                if "frame=" in line:
                    try:
                        # frame=12345 형식에서 숫자 추출
                        parts = line.split()
                        for part in parts:
                            if part.startswith("frame="):
                                frame_num = int(part.split("=")[1])
                                frame_count = max(frame_count, frame_num)
                                
                                # 진행률 계산 (0-100%)
                                if self.expected_frames > 0:
                                    ffmpeg_progress = min(100, int((frame_count / self.expected_frames) * 100))
                                else:
                                    # 예상 프레임 개수를 모르면 시간 기반 추정
                                    ffmpeg_progress = min(100, int((frame_count / 1000) * 100))
                                
                                # UI 업데이트 시그널 전송 (100ms 간격으로 제한 - 렉 방지)
                                current_time = time.time()
                                if (current_time - last_ui_update_time) >= 0.1:
                                    self.progress_updated.emit(ffmpeg_progress, "FFmpeg 실행 중...")
                                    last_ui_update_time = current_time
                    except:
                        pass
            
            # 프로세스 완료 대기
            process.wait()
            
            # 결과 확인
            if process.returncode != 0:
                error_msg = ''.join(stderr_lines)
                self.error.emit(f"FFmpeg 실행 실패 (코드: {process.returncode})\n{error_msg[:500]}")
                return
            
            # FFmpeg 실행 완료
            self.progress_updated.emit(100, "FFmpeg 실행 완료")
            
            # 추출된 프레임 파일 확인
            from pathlib import Path
            temp_dir_path = Path(self.temp_dir)
            png_files = sorted(temp_dir_path.glob("frame_*.png"))
            
            if not png_files:
                self.error.emit("프레임 추출 실패: 출력 파일이 생성되지 않았습니다")
                return
            
            # 프레임 파일 로드 시작
            self.progress_updated.emit(0, "프레임 파일 로드 중...")
            
            # 프레임 데이터 생성
            frames_data = []
            total_files = len(png_files)
            last_load_update_time = 0
            
            for i, png_file in enumerate(png_files):
                try:
                    from PySide6.QtGui import QImage
                    image = QImage(str(png_file))
                    if not image.isNull():
                        frames_data.append({
                            'index': i,
                            'timestamp': i,  # 임시값
                            'image': image
                        })
                    
                    # 로드 진행률 업데이트 (100ms 간격으로 제한)
                    if total_files > 0:
                        load_progress = int((i + 1) / total_files * 100)
                        current_time = time.time()
                        if (current_time - last_load_update_time) >= 0.1 or i == total_files - 1:
                            self.progress_updated.emit(load_progress, f"프레임 파일 로드 중... ({i+1}/{total_files})")
                            last_load_update_time = current_time
                            
                except Exception as e:
                    print(f"프레임 로드 오류 ({png_file}): {e}")
            
            # 로드 완료
            self.progress_updated.emit(100, "프레임 로드 완료")
            # 사용자가 완료 메시지를 볼 수 있도록 잠시 대기
            time.sleep(0.3)
            self.finished.emit(frames_data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(f"FFmpeg Worker 오류: {e}")


class FrameSaveWorker(QThread):
    """프레임 저장을 위한 Worker 스레드"""
    progress_updated = Signal(int, str)  # 진행률, 메시지
    finished = Signal(list)  # 저장된 파일 경로들
    error = Signal(str)  # 오류 메시지
    
    def __init__(self, frame_thumbnails, save_dir):
        super().__init__()
        self.frame_thumbnails = frame_thumbnails
        self.save_dir = save_dir
        self._is_running = True
    
    def stop(self):
        """스레드 중지"""
        self._is_running = False
    
    def run(self):
        """프레임 저장"""
        try:
            from pathlib import Path
            import time
            
            saved_paths = []
            total_frames = len(self.frame_thumbnails)
            
            for i, frame_thumb in enumerate(self.frame_thumbnails):
                if not self._is_running:
                    break
                
                try:
                    # 프레임 이미지 가져오기 (thumb_label의 pixmap에서)
                    if hasattr(frame_thumb, 'thumb_label'):
                        pixmap = frame_thumb.thumb_label.pixmap()
                        if pixmap and not pixmap.isNull():
                            # QPixmap을 QImage로 변환
                            frame_image = pixmap.toImage()
                            
                            # 타임스탬프 가져오기 (ms를 초로 변환)
                            timestamp_sec = frame_thumb.frame_time_ms / 1000.0 if hasattr(frame_thumb, 'frame_time_ms') else i
                            
                            # 파일명 생성
                            filename = f"frame_{time.strftime('%Y%m%d_%H%M%S')}_{i+1:04d}_{timestamp_sec:.3f}s.png"
                            save_path = Path(self.save_dir) / filename
                            
                            # 이미지 저장
                            if frame_image.save(str(save_path)):
                                saved_paths.append(save_path)
                        
                        # 진행률 업데이트
                        progress = int((i + 1) / total_frames * 100)
                        self.progress_updated.emit(progress, f"프레임 저장 중... ({i+1}/{total_frames})")
                except Exception as e:
                    print(f"프레임 {i} 저장 오류: {e}")
                    import traceback
                    traceback.print_exc()
            
            self.finished.emit(saved_paths)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(f"프레임 저장 Worker 오류: {e}")


class VideoFrameExtractionOptions(QFrame):
    """비디오 프레임 추출 옵션 카드"""
    
    def __init__(self, app_instance, parent=None):
        super().__init__(parent)
        self.app_instance = app_instance
        self.setObjectName("VideoFrameExtractionOptions")
        self.setStyleSheet("""
            QFrame#VideoFrameExtractionOptions {
                background: rgba(17,17,27,0.9);
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 6px;
                margin: 4px;
            }
        """)
        self.ffmpeg_path = None
        self.setup_ui()
        # 타임라인 연결은 지연 연결 (타임라인이 생성된 후)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self._connect_timeline)
    
    def _connect_timeline(self):
        """타임라인 선택 범위 변경 시 자동 업데이트 연결"""
        try:
            if hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
                if hasattr(self.app_instance.video_frame_module, 'timeline_card'):
                    timeline_card = self.app_instance.video_frame_module.timeline_card
                    if timeline_card and hasattr(timeline_card, 'timeline'):
                        timeline = timeline_card.timeline
                        if timeline:
                            # 기존 연결 해제 (중복 방지)
                            try:
                                timeline.selectionChanged.disconnect(self._on_timeline_selection_changed)
                            except:
                                pass
                            # 새 연결 (실시간 업데이트를 위해 직접 연결)
                            timeline.selectionChanged.connect(self._on_timeline_selection_changed)
                            print("✅ 프레임 추출 모듈이 타임라인과 연결되었습니다")
                            
                            # 초기 선택 범위가 있으면 적용
                            if hasattr(timeline, 'selection_start') and hasattr(timeline, 'selection_end'):
                                if timeline.selection_start < timeline.selection_end and timeline.duration > 0:
                                    vis_start_ms, vis_end_ms, vis_dur_ms = timeline.get_visible_time_range()
                                    if vis_dur_ms > 0:
                                        start_ms = int(vis_start_ms + timeline.selection_start * vis_dur_ms)
                                        end_ms = int(vis_start_ms + timeline.selection_end * vis_dur_ms)
                                        self._on_timeline_selection_changed(start_ms, end_ms)
        except Exception as e:
            print(f"⚠️ 타임라인 연결 실패: {e}")
    
    def _format_time_from_ms(self, ms):
        """밀리초를 HH:MM:SS.mmm 형식으로 변환"""
        total_seconds = ms / 1000.0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
    def _on_timeline_selection_changed(self, start_ms, end_ms):
        """타임라인 선택 범위가 변경되었을 때 호출"""
        start_time_str = self._format_time_from_ms(start_ms)
        end_time_str = self._format_time_from_ms(end_ms)
        
        # 시작/끝 시간 자동 업데이트
        if hasattr(self, 'start_edit') and self.start_edit:
            self.start_edit.setText(start_time_str)
        if hasattr(self, 'end_edit') and self.end_edit:
            self.end_edit.setText(end_time_str)
        
        print(f"🔄 프레임 추출 범위 자동 업데이트: {start_time_str} ~ {end_time_str}")
    
    def update_range_for_new_video(self, duration_ms):
        """새 비디오 로드 시 시작/끝 시간을 현재 타임라인의 가시 영역으로 갱신"""
        if duration_ms <= 0:
            return
        
        # 타임라인의 현재 가시 영역 가져오기
        vis_start_ms = 0
        vis_end_ms = duration_ms
        
        try:
            if hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
                if hasattr(self.app_instance.video_frame_module, 'timeline_card'):
                    timeline_card = self.app_instance.video_frame_module.timeline_card
                    if timeline_card and hasattr(timeline_card, 'timeline'):
                        timeline = timeline_card.timeline
                        if timeline:
                            vis_start_ms, vis_end_ms, vis_dur_ms = timeline.get_visible_time_range()
                            if vis_dur_ms > 0:
                                # 가시 영역의 시작/끝 시간 사용
                                pass
                            else:
                                # 가시 영역이 없으면 전체 범위
                                vis_start_ms = 0
                                vis_end_ms = duration_ms
        except Exception as e:
            print(f"⚠️ 타임라인 가시 영역 가져오기 실패: {e}")
            # 실패 시 전체 범위 사용
            vis_start_ms = 0
            vis_end_ms = duration_ms
        
        start_time_str = self._format_time_from_ms(vis_start_ms)
        end_time_str = self._format_time_from_ms(vis_end_ms)
        
        # 시작/끝 시간을 가시 영역으로 설정
        if hasattr(self, 'start_edit') and self.start_edit:
            self.start_edit.setText(start_time_str)
        if hasattr(self, 'end_edit') and self.end_edit:
            self.end_edit.setText(end_time_str)
        
        print(f"🔄 새 비디오 로드: 프레임 추출 범위를 가시 영역으로 설정 ({start_time_str} ~ {end_time_str})")
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 헤더
        header = QLabel("FRAME EXTRACTION")
        header.setStyleSheet("""
            QLabel {
                font-size: 11px; 
                font-weight: 700;
                color: #9CA3AF; 
                letter-spacing: 1px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(header)
        
        # 구분선 추가 함수 (advanced_search_module 스타일)
        def add_separator():
            separator = QFrame()
            separator.setFixedHeight(1)
            separator.setStyleSheet("""
                QFrame {
                    background-color: rgba(75,85,99,0.3);
                    border: none;
                    margin: 10px 20px;
                }
            """)
            layout.addWidget(separator)
        
        # Output 섹션
        output_label = QLabel("출력")
        output_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 600;
                color: #D1D5DB;
                margin-top: 0px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(output_label)
        
        # Format
        format_layout = QHBoxLayout()
        format_label = QLabel("포맷:")
        format_label.setStyleSheet("color: #9CA3AF; font-size: 11px; min-width: 70px;")
        self.format_combo = CustomComboBox()
        self.format_combo.addItems(["PNG", "JPG", "JPEG", "BMP", "TIFF", "WEBP"])
        # search_module의 검색 텍스트 박스와 동일한 높이 (padding으로 자동 계산)
        self.format_combo.setStyleSheet("""
            QComboBox {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
            }
            QComboBox:focus {
                border: 2px solid #3B82F6;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background: rgba(26,27,38,0.95);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
                selection-background-color: #3B82F6;
                selection-color: white;
            }
        """)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)
        
        # Quality
        quality_layout = QHBoxLayout()
        quality_label = QLabel("품질:")
        quality_label.setStyleSheet("color: #9CA3AF; font-size: 11px; min-width: 70px;")
        self.quality_spin = CustomSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        # search_module의 검색 텍스트 박스와 동일한 높이 (padding으로 자동 계산)
        self.quality_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
            }
            QSpinBox:focus {
                border: 2px solid #3B82F6;
            }
            QSpinBox::up-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::down-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::up-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
        """)
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_spin)
        layout.addLayout(quality_layout)
        
        # Scale
        scale_layout = QHBoxLayout()
        scale_label = QLabel("크기:")
        scale_label.setStyleSheet("color: #9CA3AF; font-size: 11px; min-width: 70px;")
        self.scale_spin = CustomSpinBox()
        self.scale_spin.setRange(1, 500)
        self.scale_spin.setValue(100)
        self.scale_spin.setSuffix("%")
        # search_module의 검색 텍스트 박스와 동일한 높이 (padding으로 자동 계산)
        self.scale_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
            }
            QSpinBox:focus {
                border: 2px solid #3B82F6;
            }
            QSpinBox::up-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::down-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::up-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
        """)
        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(self.scale_spin)
        layout.addLayout(scale_layout)
        
        # 구분선
        add_separator()
        
        # Extraction mode 섹션
        mode_label = QLabel("추출 모드")
        mode_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 600;
                color: #D1D5DB;
                margin-top: 12px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(mode_label)
        
        # 추출 모드 체크박스 (단일 선택 보장을 위한 로직 필요)
        mode_options_layout = QVBoxLayout()
        mode_options_layout.setSpacing(8)
        
        # 전체 프레임 추출
        self.all_frames_check = CustomCheckBox("전체 프레임 추출")
        self.all_frames_check.setChecked(False)
        self.all_frames_check.toggled.connect(lambda checked: self._on_mode_check_toggled("all_frames", checked))
        mode_options_layout.addWidget(self.all_frames_check)
        
        # 1초당 n프레임 추출
        fps_interval_layout = QVBoxLayout()
        fps_interval_layout.setSpacing(4)
        self.fps_interval_check = CustomCheckBox("1초당 n프레임 추출")
        self.fps_interval_check.setChecked(True)  # 기본 선택
        self.fps_interval_check.toggled.connect(lambda checked: self._on_mode_check_toggled("fps_interval", checked))
        fps_interval_layout.addWidget(self.fps_interval_check)
        
        # 1초당 n프레임 설정
        fps_setting_layout = QHBoxLayout()
        fps_setting_layout.setContentsMargins(20, 0, 0, 0)  # 들여쓰기
        fps_setting_label = QLabel("1초당")
        fps_setting_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        self.fps_interval_spin = CustomSpinBox()
        self.fps_interval_spin.setRange(1, 120)
        self.fps_interval_spin.setValue(1)
        # search_module의 검색 텍스트 박스와 동일한 높이 (padding으로 자동 계산)
        self.fps_interval_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
            }
            QSpinBox:focus {
                border: 2px solid #3B82F6;
            }
            QSpinBox::up-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::down-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::up-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
        """)
        fps_setting_label2 = QLabel("프레임")
        fps_setting_label2.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        fps_setting_layout.addWidget(fps_setting_label)
        fps_setting_layout.addWidget(self.fps_interval_spin)
        fps_setting_layout.addWidget(fps_setting_label2)
        fps_setting_layout.addStretch()
        fps_interval_layout.addLayout(fps_setting_layout)
        mode_options_layout.addLayout(fps_interval_layout)
        
        # n초당 1프레임 추출
        time_interval_layout = QVBoxLayout()
        time_interval_layout.setSpacing(4)
        self.time_interval_check = CustomCheckBox("n초당 1프레임 추출")
        self.time_interval_check.setChecked(False)
        self.time_interval_check.toggled.connect(lambda checked: self._on_mode_check_toggled("time_interval", checked))
        time_interval_layout.addWidget(self.time_interval_check)
        
        # n초당 1프레임 설정
        time_setting_layout = QHBoxLayout()
        time_setting_layout.setContentsMargins(20, 0, 0, 0)  # 들여쓰기
        time_setting_label = QLabel("매")
        time_setting_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        self.time_interval_spin = CustomSpinBox()
        self.time_interval_spin.setRange(1, 1000)
        self.time_interval_spin.setValue(1)
        # search_module의 검색 텍스트 박스와 동일한 높이 (padding으로 자동 계산)
        self.time_interval_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
            }
            QSpinBox:focus {
                border: 2px solid #3B82F6;
            }
            QSpinBox::up-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::down-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::up-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
        """)
        time_setting_label2 = QLabel("초당 1프레임")
        time_setting_label2.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        time_setting_layout.addWidget(time_setting_label)
        time_setting_layout.addWidget(self.time_interval_spin)
        time_setting_layout.addWidget(time_setting_label2)
        time_setting_layout.addStretch()
        time_interval_layout.addLayout(time_setting_layout)
        mode_options_layout.addLayout(time_interval_layout)
        
        # 키프레임만 추출
        self.keyframes_only_check = CustomCheckBox("키프레임만 추출")
        self.keyframes_only_check.setChecked(False)
        self.keyframes_only_check.toggled.connect(lambda checked: self._on_mode_check_toggled("keyframes_only", checked))
        mode_options_layout.addWidget(self.keyframes_only_check)
        
        layout.addLayout(mode_options_layout)
        
        # 구분선
        add_separator()
        
        # Range 섹션
        range_label = QLabel("범위")
        range_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 600;
                color: #D1D5DB;
                margin-top: 12px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(range_label)
        
        # Start
        start_layout = QHBoxLayout()
        start_label = QLabel("시작:")
        start_label.setStyleSheet("color: #9CA3AF; font-size: 11px; min-width: 70px;")
        self.start_edit = QLineEdit("")
        self.start_edit.setPlaceholderText("HH:MM:SS.mmm (타임라인에서 범위 지정 시 자동 입력)")
        # search_module의 검색 텍스트 박스와 동일한 높이 (padding으로 자동 계산)
        self.start_edit.setStyleSheet("""
            QLineEdit {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #3B82F6;
            }
        """)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_edit)
        layout.addLayout(start_layout)
        
        # End
        end_layout = QHBoxLayout()
        end_label = QLabel("끝:")
        end_label.setStyleSheet("color: #9CA3AF; font-size: 11px; min-width: 70px;")
        self.end_edit = QLineEdit("")
        self.end_edit.setPlaceholderText("HH:MM:SS.mmm (타임라인에서 범위 지정 시 자동 입력)")
        # search_module의 검색 텍스트 박스와 동일한 높이 (padding으로 자동 계산)
        self.end_edit.setStyleSheet("""
            QLineEdit {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #3B82F6;
            }
        """)
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_edit)
        layout.addLayout(end_layout)
        
        # 추가 옵션
        options_layout = QVBoxLayout()
        options_layout.setSpacing(8)
        
        self.deduplicate_check = CustomCheckBox("유사한 프레임 중복 제거")
        options_layout.addWidget(self.deduplicate_check)
        
        layout.addLayout(options_layout)
        
        # 추출 버튼
        extract_button = QPushButton("프레임 추출")
        extract_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(59,130,246,0.8), stop:1 rgba(37,99,235,0.9));
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 12px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(59,130,246,1.0), stop:1 rgba(37,99,235,1.0));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(37,99,235,0.9), stop:1 rgba(29,78,216,0.9));
            }
        """)
        extract_button.clicked.connect(self.on_extract_clicked)
        layout.addWidget(extract_button)
        
        # 추출한 프레임 이미지로 이동 버튼
        goto_frames_button = QPushButton("추출한 프레임 이미지로 이동")
        goto_frames_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(59,130,246,0.8), stop:1 rgba(37,99,235,0.9));
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 12px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(59,130,246,1.0), stop:1 rgba(37,99,235,1.0));
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(37,99,235,0.9), stop:1 rgba(29,78,216,0.9));
            }
        """)
        goto_frames_button.clicked.connect(self.on_goto_frames_clicked)
        layout.addWidget(goto_frames_button)
        
        layout.addStretch()
    
    def _on_mode_check_toggled(self, mode_name, checked):
        """추출 모드 체크박스 토글 시 단일 선택 보장"""
        if not checked:
            return
        
        # 다른 모든 체크박스 해제
        if mode_name != "all_frames":
            self.all_frames_check.blockSignals(True)
            self.all_frames_check.setChecked(False)
            self.all_frames_check.blockSignals(False)
        
        if mode_name != "fps_interval":
            self.fps_interval_check.blockSignals(True)
            self.fps_interval_check.setChecked(False)
            self.fps_interval_check.blockSignals(False)
        
        if mode_name != "time_interval":
            self.time_interval_check.blockSignals(True)
            self.time_interval_check.setChecked(False)
            self.time_interval_check.blockSignals(False)
        
        if mode_name != "keyframes_only":
            self.keyframes_only_check.blockSignals(True)
            self.keyframes_only_check.setChecked(False)
            self.keyframes_only_check.blockSignals(False)
    
    def _get_ffmpeg_path(self):
        """FFmpeg 실행 파일 경로 가져오기 (자동 다운로드 포함)"""
        # 1. 시스템 PATH에서 찾기
        ffmpeg_cmd = shutil.which("ffmpeg")
        if ffmpeg_cmd:
            return ffmpeg_cmd
        
        # 2. 플러그인 폴더에서 찾기
        if self.ffmpeg_path and Path(self.ffmpeg_path).exists():
            return self.ffmpeg_path
        
        # 현재 스크립트 위치 기준으로 plugins/ffmpeg 폴더 찾기
        current_dir = Path(__file__).parent.absolute()
        plugins_dir = current_dir / "plugins" / "ffmpeg"
        
        # Windows용 경로
        if platform.system() == "Windows":
            ffmpeg_exe = plugins_dir / "ffmpeg.exe"
        else:
            ffmpeg_exe = plugins_dir / "ffmpeg"
        
        if ffmpeg_exe.exists():
            self.ffmpeg_path = str(ffmpeg_exe)
            return self.ffmpeg_path
        
        # 3. 자동 다운로드 시도
        print("📥 FFmpeg를 자동으로 다운로드합니다...")
        if self._download_ffmpeg(plugins_dir):
            if ffmpeg_exe.exists():
                self.ffmpeg_path = str(ffmpeg_exe)
                return self.ffmpeg_path
        
        return None
    
    def _download_ffmpeg(self, target_dir):
        """FFmpeg를 자동으로 다운로드하고 설치"""
        try:
            system = platform.system()
            
            if system == "Windows":
                # Windows용 FFmpeg 다운로드 (GitHub releases)
                # 최신 버전의 Windows static build URL
                # 실제로는 최신 릴리즈를 확인해야 하지만, 안정적인 버전 사용
                download_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                
                # 다운로드 폴더 생성
                target_dir.mkdir(parents=True, exist_ok=True)
                zip_path = target_dir / "ffmpeg.zip"
                
                print(f"📥 FFmpeg 다운로드 중: {download_url}")
                
                # 다운로드
                def download_progress(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = min(100, (block_num * block_size * 100) // total_size)
                        if block_num % 10 == 0:  # 10블록마다 출력
                            print(f"다운로드 진행: {percent}%", end='\r')
                
                try:
                    urllib.request.urlretrieve(download_url, zip_path, download_progress)
                    print("\n✅ 다운로드 완료")
                except Exception as e:
                    print(f"\n❌ 다운로드 실패: {e}")
                    # 대체 URL 시도 (직접 빌드)
                    alt_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
                    try:
                        print(f"대체 URL로 시도: {alt_url}")
                        urllib.request.urlretrieve(alt_url, zip_path, download_progress)
                        print("\n✅ 다운로드 완료")
                    except Exception as e2:
                        print(f"\n❌ 대체 다운로드도 실패: {e2}")
                        return False
                
                # 압축 해제
                print("📦 압축 해제 중...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(target_dir)
                
                # zip 파일 삭제
                zip_path.unlink()
                
                # ffmpeg.exe 찾기 (하위 폴더에 있을 수 있음)
                for ffmpeg_file in target_dir.rglob("ffmpeg.exe"):
                    # bin 폴더에 있는 경우 그대로 사용
                    if "bin" in str(ffmpeg_file.parent):
                        # bin 폴더의 내용을 plugins/ffmpeg로 이동
                        bin_dir = ffmpeg_file.parent
                        for item in bin_dir.iterdir():
                            if item.is_file():
                                shutil.move(str(item), str(target_dir / item.name))
                        # bin 폴더 삭제 시도
                        try:
                            bin_dir.rmdir()
                        except:
                            pass
                    break
                
                # 상위 폴더들 정리
                for item in target_dir.iterdir():
                    if item.is_dir() and item.name not in ["bin"]:
                        # 하위에 ffmpeg.exe가 있으면 이동
                        for ffmpeg_file in item.rglob("ffmpeg.exe"):
                            bin_dir = ffmpeg_file.parent
                            for file_item in bin_dir.iterdir():
                                if file_item.is_file():
                                    shutil.move(str(file_item), str(target_dir / file_item.name))
                            break
                        try:
                            shutil.rmtree(item)
                        except:
                            pass
                
                print("✅ FFmpeg 설치 완료")
                return True
                
            else:
                print(f"❌ {system}용 자동 다운로드는 아직 지원되지 않습니다")
                print("시스템 패키지 매니저로 FFmpeg를 설치해주세요:")
                print("  macOS: brew install ffmpeg")
                print("  Linux: sudo apt-get install ffmpeg")
                return False
                
        except Exception as e:
            print(f"❌ FFmpeg 다운로드/설치 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_time_string(self, time_str):
        """시간 문자열 (HH:MM:SS.mmm)을 초로 변환"""
        try:
            parts = time_str.split(":")
            if len(parts) != 3:
                return 0
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split(".")
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            return total_seconds
        except:
            return 0
    
    def _extract_frames_with_ffmpeg(self, video_path, mode, start_time_sec, end_time_sec, scale_percent, format_ext, timeline_card=None):
        """FFmpeg를 사용하여 프레임 추출"""
        try:
            # FFmpeg 실행 파일 확인 (자동 다운로드 포함)
            ffmpeg_cmd = self._get_ffmpeg_path()
            if not ffmpeg_cmd:
                print("❌ FFmpeg를 찾을 수 없고 자동 다운로드도 실패했습니다")
                print("수동으로 FFmpeg를 설치하거나 plugins/ffmpeg 폴더에 ffmpeg.exe를 배치해주세요")
                return []
            
            # 현재 비디오 경로 가져오기
            if not video_path or not Path(video_path).exists():
                print("❌ 비디오 파일이 존재하지 않습니다")
                return []
            
            mode_type, mode_value = mode
            frames_data = []
            
            # 예상 프레임 개수 계산 (진행률 계산용)
            expected_frames = 0
            duration_sec = end_time_sec - start_time_sec if end_time_sec > start_time_sec else 0
            if duration_sec > 0:
                if mode_type == "all_frames":
                    # 전체 프레임: 비디오 FPS 필요 (나중에 계산)
                    pass
                elif mode_type == "fps_interval":
                    # 1초당 n프레임
                    expected_frames = int(duration_sec * mode_value)
                elif mode_type == "time_interval":
                    # n초당 1프레임
                    expected_frames = int(duration_sec / mode_value) if mode_value > 0 else 0
                elif mode_type == "keyframes_only":
                    # 키프레임: 대략 1초당 1개
                    expected_frames = int(duration_sec)
            
            # 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp()
            try:
                # FFmpeg 명령 구성
                output_pattern = os.path.join(temp_dir, "frame_%06d.png")
                cmd = [ffmpeg_cmd, "-i", str(video_path), "-y"]  # -y: 덮어쓰기
                
                # 시간 범위 설정
                if start_time_sec > 0:
                    cmd.extend(["-ss", str(start_time_sec)])
                if end_time_sec > 0:
                    duration = end_time_sec - start_time_sec
                    if duration > 0:
                        cmd.extend(["-t", str(duration)])
                
                # 필터 설정
                filter_parts = []
                
                if mode_type == "all_frames":
                    # 전체 프레임 추출
                    filter_parts.append("select='not(mod(n,1))'")
                elif mode_type == "fps_interval":
                    # 1초당 n프레임 추출
                    fps_value = mode_value
                    filter_parts.append(f"fps={fps_value}")
                elif mode_type == "time_interval":
                    # n초당 1프레임 추출
                    time_interval = mode_value
                    fps_value = 1.0 / time_interval
                    filter_parts.append(f"fps={fps_value}")
                elif mode_type == "keyframes_only":
                    # 키프레임만 추출
                    filter_parts.append("select='eq(pict_type,I)'")
                
                # 스케일 적용
                if scale_percent != 100:
                    scale_factor = scale_percent / 100.0
                    filter_parts.append(f"scale=iw*{scale_factor}:ih*{scale_factor}")
                
                if filter_parts:
                    cmd.extend(["-vf", ",".join(filter_parts)])
                
                # 출력 설정
                cmd.extend(["-vsync", "0", output_pattern])
                
                print(f"🔧 FFmpeg 명령: {' '.join(cmd)}")
                
                # FFmpeg Worker 스레드로 실행 (UI 멈춤 방지)
                # Worker 결과를 저장할 변수
                worker_result = {'frames_data': None, 'error': None, 'finished': False}
                
                # Worker 생성
                worker = FFmpegWorker(cmd, expected_frames, temp_dir, format_ext)
                
                # 진행률 업데이트 시그널 연결
                def on_ffmpeg_progress(progress, message):
                    if timeline_card:
                        timeline_card.update_extraction_progress(progress, message)
                
                worker.progress_updated.connect(on_ffmpeg_progress)
                
                # 완료 시그널 연결
                def on_ffmpeg_finished(frames_data):
                    worker_result['frames_data'] = frames_data
                    worker_result['finished'] = True
                
                worker.finished.connect(on_ffmpeg_finished)
                
                # 오류 시그널 연결
                def on_ffmpeg_error(error_msg):
                    worker_result['error'] = error_msg
                    worker_result['finished'] = True
                    print(f"❌ FFmpeg Worker 오류: {error_msg}")
                
                worker.error.connect(on_ffmpeg_error)
                
                # 진행바 초기화
                if timeline_card:
                    timeline_card.update_extraction_progress(0, "FFmpeg 실행 중...")
                
                # Worker 시작
                worker.start()
                
                # Worker 완료 대기 (UI는 멈추지 않음)
                while not worker_result['finished']:
                    QApplication.processEvents()
                    import time
                    time.sleep(0.01)
                
                # Worker 종료 대기
                worker.wait()
                
                # 오류 확인
                if worker_result['error']:
                    print(f"❌ FFmpeg 실행 실패: {worker_result['error']}")
                    if timeline_card:
                        timeline_card.update_extraction_progress(0, "FFmpeg 실행 실패")
                    return []
                
                # 프레임 데이터 가져오기 (Worker에서 이미 QImage로 변환됨)
                raw_frames_data = worker_result['frames_data'] or []
                
                if not raw_frames_data:
                    print(f"⚠️ 추출된 프레임이 없습니다.")
                    if timeline_card:
                        timeline_card.hide_extraction_progress()
                    return []
                
                # 비디오 FPS 가져오기 (시간 계산용)
                fps = 30.0  # 기본값
                try:
                    probe_cmd = [ffmpeg_cmd, "-i", str(video_path), "-hide_banner"]
                    probe_result = subprocess.run(
                        probe_cmd,
                        capture_output=True,
                        encoding='utf-8',
                        errors='ignore',
                        timeout=10
                    )
                    # FPS 추출 (간단한 파싱)
                    stderr_text = probe_result.stderr if probe_result.stderr else ""
                    for line in stderr_text.split("\n"):
                        if "fps" in line.lower() and "fps" in line:
                            try:
                                parts = line.split()
                                for i, part in enumerate(parts):
                                    if "fps" in part.lower():
                                        fps_str = parts[i-1] if i > 0 else "30"
                                        fps = float(fps_str)
                                        break
                            except:
                                pass
                except:
                    pass
                
                # 프레임 데이터를 (QPixmap, time_ms) 튜플로 변환
                frames_data = []
                if timeline_card:
                    timeline_card.update_extraction_progress(0, "프레임 처리 중...")
                    QApplication.processEvents()
                
                total_frames = len(raw_frames_data)
                for idx, frame_dict in enumerate(raw_frames_data):
                    frame_number = frame_dict['index']
                    qimage = frame_dict['image']
                    
                    # 진행바 업데이트
                    if timeline_card and total_frames > 0:
                        convert_progress = int((idx / total_frames) * 100)
                        timeline_card.update_extraction_progress(convert_progress, "프레임 처리 중...")
                        # 주기적으로 UI 업데이트
                        if idx % 10 == 0 or idx == total_frames - 1:
                            QApplication.processEvents()
                    
                    # 프레임 시간 계산
                    if mode_type == "fps_interval":
                        time_sec = start_time_sec + (frame_number / mode_value)
                    elif mode_type == "time_interval":
                        time_sec = start_time_sec + (frame_number * mode_value)
                    elif mode_type == "all_frames":
                        time_sec = start_time_sec + (frame_number / fps) if fps > 0 else start_time_sec
                    elif mode_type == "keyframes_only":
                        time_sec = start_time_sec + frame_number
                    else:
                        time_sec = start_time_sec + (frame_number / fps) if fps > 0 else start_time_sec
                    
                    time_ms = int(time_sec * 1000)
                    
                    # QImage를 QPixmap으로 변환
                    pixmap = QPixmap.fromImage(qimage)
                    if not pixmap.isNull():
                        frames_data.append((pixmap, time_ms))
                    frame_number += 1
                
                # 프레임 로드 완료 - 다음 작업으로 전환 (중복 제거가 필요한 경우)
                
                print(f"✅ FFmpeg로 {len(frames_data)}개 프레임 추출 완료")
                
            finally:
                # 임시 디렉토리 정리
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            
            return frames_data
            
        except subprocess.TimeoutExpired:
            print("❌ FFmpeg 실행 시간 초과")
            if timeline_card:
                timeline_card.hide_extraction_progress()
            return []
        except Exception as e:
            print(f"❌ 프레임 추출 오류: {e}")
            import traceback
            traceback.print_exc()
            if timeline_card:
                timeline_card.hide_extraction_progress()
            return []
    
    def on_goto_frames_clicked(self):
        """추출한 프레임 이미지로 이동 버튼 클릭 시 호출"""
        # 타임라인 카드 가져오기 (진행률 바 표시용)
        timeline_card = None
        try:
            if hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
                if hasattr(self.app_instance.video_frame_module, 'timeline_card'):
                    timeline_card = self.app_instance.video_frame_module.timeline_card
        except Exception:
            pass
        
        # Worker 스레드를 사용하여 프레임 저장 (UI 멈춤 방지)
        self._save_frames_with_worker(timeline_card)
    
    def _save_frames_with_worker(self, timeline_card=None):
        """Worker 스레드를 사용하여 프레임 저장 (UI 멈춤 방지)"""
        try:
            if not hasattr(self.app_instance, 'video_frame_module') or not self.app_instance.video_frame_module:
                print("⚠️ 비디오 프레임 모듈이 없습니다.")
                return
            
            if not hasattr(self.app_instance.video_frame_module, 'frame_container_card'):
                print("⚠️ 프레임 컨테이너가 없습니다.")
                return
            
            frame_container = self.app_instance.video_frame_module.frame_container_card
            if not frame_container or not frame_container.frame_thumbnails:
                print("⚠️ 프레임 컨테이너에 프레임이 없습니다. 먼저 프레임을 추출해주세요.")
                return
            
            # plugins/ffmpeg/images 폴더 생성
            ffmpeg_path = self._get_ffmpeg_path()
            if not ffmpeg_path:
                print("❌ FFmpeg 경로를 찾을 수 없습니다")
                return
            
            plugins_dir = Path(ffmpeg_path).parent
            images_dir = plugins_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # 진행률 바 표시 시작
            if timeline_card:
                timeline_card.update_extraction_progress(0, "프레임 저장 준비 중...")
                QApplication.processEvents()
            
            # Worker 스레드 생성 및 시작
            self._frame_save_worker = FrameSaveWorker(
                frame_container.frame_thumbnails,
                str(images_dir)
            )
            
            # 시그널 연결
            self._frame_save_worker.progress_updated.connect(
                lambda progress, msg: self._on_save_progress(timeline_card, progress, msg)
            )
            self._frame_save_worker.finished.connect(
                lambda saved_paths: self._on_save_finished(timeline_card, saved_paths)
            )
            self._frame_save_worker.error.connect(
                lambda error: self._on_save_error(timeline_card, error)
            )
            
            # 스레드 시작
            self._frame_save_worker.start()
            print("프레임 저장 Worker 스레드 시작")
            
        except Exception as e:
            print(f"프레임 저장 Worker 시작 오류: {e}")
            import traceback
            traceback.print_exc()
            if timeline_card:
                timeline_card.hide_extraction_progress()
    
    def _on_save_progress(self, timeline_card, progress, message):
        """프레임 저장 진행률 업데이트"""
        if timeline_card:
            timeline_card.update_extraction_progress(progress, message)
    
    def _on_save_finished(self, timeline_card, saved_paths):
        """프레임 저장 완료"""
        print(f"✅ 프레임 저장 완료: {len(saved_paths)}개")
        
        if saved_paths:
            # 서치 필터 그리드에 이미지 추가
            self._add_images_to_grid(saved_paths, timeline_card)
        
        # 진행률 바 숨김
        if timeline_card:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, timeline_card.hide_extraction_progress)
        
        # 프레임 컨테이너로 포커스 이동 및 스크롤
        self._scroll_to_frame_container()
    
    def _on_save_error(self, timeline_card, error):
        """프레임 저장 오류"""
        print(f"❌ 프레임 저장 오류: {error}")
        if timeline_card:
            timeline_card.hide_extraction_progress()
    
    def _save_frames_to_images(self, timeline_card=None):
        """프레임 컨테이너의 프레임들을 이미지 파일로 저장"""
        saved_paths = []
        try:
            if not hasattr(self.app_instance, 'video_frame_module') or not self.app_instance.video_frame_module:
                print("⚠️ 비디오 프레임 모듈이 없습니다.")
                return saved_paths
            
            if not hasattr(self.app_instance.video_frame_module, 'frame_container_card'):
                print("⚠️ 프레임 컨테이너가 없습니다.")
                return saved_paths
            
            frame_container = self.app_instance.video_frame_module.frame_container_card
            if not frame_container or not frame_container.frame_thumbnails:
                print("⚠️ 프레임 컨테이너에 프레임이 없습니다. 먼저 프레임을 추출해주세요.")
                return saved_paths
            
            # 진행률 바 표시 시작
            if timeline_card:
                timeline_card.update_extraction_progress(0, "프레임 이미지 저장 중...")
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()  # UI 즉시 업데이트
            
            # plugins/ffmpeg/images 폴더 생성
            ffmpeg_path = self._get_ffmpeg_path()
            if not ffmpeg_path:
                print("❌ FFmpeg 경로를 찾을 수 없습니다.")
                return saved_paths
            
            # FFmpeg 경로를 기반으로 plugins/ffmpeg 폴더 찾기
            ffmpeg_path_obj = Path(ffmpeg_path)
            if ffmpeg_path_obj.is_file():
                # 실행 파일인 경우: plugins/ffmpeg/ffmpeg.exe -> plugins/ffmpeg
                ffmpeg_dir = ffmpeg_path_obj.parent
            else:
                # 디렉토리인 경우
                ffmpeg_dir = ffmpeg_path_obj
            
            # plugins/ffmpeg/images 폴더 생성
            images_dir = ffmpeg_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 이미지 저장 폴더: {images_dir}")
            
            # 각 프레임을 이미지 파일로 저장
            from datetime import datetime
            from PySide6.QtWidgets import QApplication
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 저장할 프레임 개수 계산 (유효한 프레임만)
            valid_thumbnails = []
            for thumbnail in frame_container.frame_thumbnails:
                if hasattr(thumbnail, 'thumb_label') and thumbnail.thumb_label.pixmap():
                    pixmap = thumbnail.thumb_label.pixmap()
                    if not pixmap.isNull():
                        valid_thumbnails.append(thumbnail)
            
            total_frames = len(valid_thumbnails)
            
            # 배치 처리로 성능 개선 (한 번에 더 많이 처리)
            batch_size = 50  # 한 번에 50개씩 처리
            for batch_start in range(0, total_frames, batch_size):
                batch_end = min(batch_start + batch_size, total_frames)
                batch_thumbnails = valid_thumbnails[batch_start:batch_end]
                
                # 배치 내에서 프레임 저장
                for idx_in_batch, thumbnail in enumerate(batch_thumbnails):
                    idx = batch_start + idx_in_batch
                    pixmap = thumbnail.thumb_label.pixmap()
                    
                    # 파일명 생성: frame_YYYYMMDD_HHMMSS_001.png 형식
                    frame_time_ms = getattr(thumbnail, 'frame_time_ms', idx * 1000)
                    frame_time_sec = frame_time_ms / 1000.0
                    filename = f"frame_{timestamp}_{idx+1:04d}_{frame_time_sec:.3f}s.png"
                    filepath = images_dir / filename
                    
                    # 이미지 저장 (Path 객체를 문자열로 변환)
                    filepath_str = str(filepath)
                    if pixmap.save(filepath_str, "PNG"):
                        saved_paths.append(filepath)
                    else:
                        print(f"  ❌ 프레임 저장 실패: {filename}")
                
                # 배치 완료 후 진행률 업데이트 (UI 업데이트 빈도 줄이기)
                if timeline_card and total_frames > 0:
                    save_progress = int((batch_end / total_frames) * 100)
                    timeline_card.update_extraction_progress(save_progress, "프레임 이미지 저장 중...")
                    QApplication.processEvents()  # 배치 단위로만 UI 업데이트
                
                # 로그 출력 빈도 줄이기
                if batch_end % 100 == 0 or batch_end == total_frames:
                    print(f"  💾 {batch_end}/{total_frames}개 프레임 저장 완료")
            
            # 저장 완료 - 다음 작업으로 전환
            if timeline_card:
                timeline_card.update_extraction_progress(0, "서치 필터 그리드에 추가 중...")
                QApplication.processEvents()  # UI 즉시 업데이트
            
            print(f"✅ 총 {len(saved_paths)}개 프레임 이미지 저장 완료")
            return saved_paths
            
        except Exception as e:
            print(f"❌ 프레임 이미지 저장 실패: {e}")
            import traceback
            traceback.print_exc()
            return saved_paths
    
    def _add_images_to_grid(self, image_paths, timeline_card=None):
        """저장된 이미지 경로들을 서치 필터 그리드에 추가"""
        try:
            if not image_paths:
                return
            
            from PySide6.QtWidgets import QApplication
            
            # image_files 초기화 확인
            if not hasattr(self.app_instance, 'image_files'):
                self.app_instance.image_files = []
            if not hasattr(self.app_instance, 'original_image_files'):
                self.app_instance.original_image_files = []
            
            # 중복 제거하면서 추가
            existing_paths = {str(path) for path in self.app_instance.image_files}
            new_images = []
            
            for image_path in image_paths:
                image_path_str = str(image_path)
                if image_path_str not in existing_paths:
                    new_images.append(image_path)
            
            total_new = len(new_images)
            
            if total_new > 0:
                # 진행률 바 업데이트: 이미지 추가 중
                if timeline_card:
                    timeline_card.update_extraction_progress(0, "서치 필터 그리드에 추가 중...")
                    QApplication.processEvents()
                
                # 이미지 파일 목록에 추가
                for idx, image_path in enumerate(new_images):
                    self.app_instance.image_files.append(image_path)
                    self.app_instance.original_image_files.append(image_path)
                    
                    # 진행률 바 업데이트
                    if timeline_card and total_new > 0:
                        add_progress = int((idx / total_new) * 100)
                        timeline_card.update_extraction_progress(add_progress, "서치 필터 그리드에 추가 중...")
                        if idx % 10 == 0 or idx == total_new - 1:
                            QApplication.processEvents()
                
                # 이미지 썸네일 새로고침
                if timeline_card:
                    timeline_card.update_extraction_progress(90, "썸네일 새로고침 중...")
                    QApplication.processEvents()
                
                # 검색 결과 초기화 (새로 추가된 이미지가 필터링되지 않도록)
                if hasattr(self.app_instance, 'search_results'):
                    self.app_instance.search_results = None
                if hasattr(self.app_instance, 'advanced_search_results'):
                    self.app_instance.advanced_search_results = None
                
                from search_filter_grid_image_module import refresh_image_thumbnails_immediate
                refresh_image_thumbnails_immediate(self.app_instance)
                
                # 이미지 카운터 업데이트
                from search_module import update_image_counter
                update_image_counter(self.app_instance, len(self.app_instance.image_files), len(self.app_instance.image_files))
                
                if timeline_card:
                    timeline_card.update_extraction_progress(100, "완료")
                    QApplication.processEvents()
                
                print(f"✅ 서치 필터 그리드에 {total_new}개 이미지 추가 완료")
            else:
                if timeline_card:
                    timeline_card.update_extraction_progress(100, "완료")
                    QApplication.processEvents()
                print("ℹ️ 추가할 새 이미지가 없습니다 (모두 이미 존재함)")
                
        except Exception as e:
            print(f"❌ 서치 필터 그리드에 이미지 추가 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_extracted_images_folder(self):
        """plugins/ffmpeg/images 폴더의 모든 이미지 파일 삭제"""
        try:
            ffmpeg_path = self._get_ffmpeg_path()
            if not ffmpeg_path:
                return
            
            # FFmpeg 경로를 기반으로 plugins/ffmpeg 폴더 찾기
            ffmpeg_path_obj = Path(ffmpeg_path)
            if ffmpeg_path_obj.is_file():
                # 실행 파일인 경우: plugins/ffmpeg/ffmpeg.exe -> plugins/ffmpeg
                ffmpeg_dir = ffmpeg_path_obj.parent
            else:
                # 디렉토리인 경우
                ffmpeg_dir = ffmpeg_path_obj
            
            # plugins/ffmpeg/images 폴더 경로
            images_dir = ffmpeg_dir / "images"
            
            if images_dir.exists() and images_dir.is_dir():
                # 폴더 내 모든 파일 삭제
                deleted_count = 0
                for file_path in images_dir.iterdir():
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            print(f"⚠️ 이미지 파일 삭제 실패: {file_path.name} - {e}")
                
                if deleted_count > 0:
                    print(f"🧹 {deleted_count}개 추출 이미지 파일 삭제 완료: {images_dir}")
        except Exception as e:
            print(f"⚠️ 추출 이미지 폴더 정리 실패: {e}")
    
    def _scroll_to_frame_container(self):
        """프레임 컨테이너로 스크롤 및 포커스 이동"""
        try:
            if hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
                if hasattr(self.app_instance.video_frame_module, 'frame_container_card'):
                    frame_container = self.app_instance.video_frame_module.frame_container_card
                    if frame_container:
                        # 프레임 컨테이너가 있는지 확인
                        if frame_container.frame_thumbnails:
                            # 프레임 컨테이너로 포커스 이동
                            frame_container.setFocus()
                            # 스크롤 영역이 있으면 맨 위로 스크롤
                            if hasattr(frame_container, 'scroll') and frame_container.scroll:
                                frame_container.scroll.verticalScrollBar().setValue(0)
                            print(f"✅ 프레임 컨테이너로 이동: {len(frame_container.frame_thumbnails)}개 프레임")
                        else:
                            print("⚠️ 프레임 컨테이너에 프레임이 없습니다. 먼저 프레임을 추출해주세요.")
        except Exception as e:
            print(f"❌ 프레임 컨테이너로 이동 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def _deduplicate_frames(self, frames_data, threshold=0.95):
        """유사한 프레임 중복 제거 (간단한 해시 기반)"""
        if not frames_data:
            return frames_data
        
        import hashlib
        
        seen_hashes = set()
        unique_frames = []
        
        for pixmap, time_ms in frames_data:
            # 프레임을 작은 썸네일로 변환하여 해시 계산
            thumb = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image = thumb.toImage()
            
            # QImage를 바이트로 변환
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            image.save(buffer, "PNG")
            image_bytes = buffer.data()
            
            frame_hash = hashlib.md5(image_bytes).hexdigest()
            
            if frame_hash not in seen_hashes:
                seen_hashes.add(frame_hash)
                unique_frames.append((pixmap, time_ms))
        
        return unique_frames
    
    def on_extract_clicked(self):
        """프레임 추출 버튼 클릭 시 호출"""
        print("프레임 추출 시작")
        
        # 진행바 표시
        timeline_card = None
        if hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
            if hasattr(self.app_instance.video_frame_module, 'timeline_card'):
                timeline_card = self.app_instance.video_frame_module.timeline_card
                if timeline_card:
                    timeline_card.show_extraction_progress("FFmpeg 실행 중...")
                    # UI 즉시 업데이트
                    QApplication.processEvents()
        
        # 현재 비디오 경로 가져오기
        video_path = None
        if hasattr(self.app_instance, 'current_video') and self.app_instance.current_video:
            video_path = self.app_instance.current_video
        elif hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
            if hasattr(self.app_instance.video_frame_module, 'video_preview_card'):
                if hasattr(self.app_instance.video_frame_module.video_preview_card, 'current_video_path'):
                    video_path = self.app_instance.video_frame_module.video_preview_card.current_video_path
        
        if not video_path or not Path(video_path).exists():
            print("❌ 비디오 파일이 선택되지 않았거나 존재하지 않습니다.")
            if timeline_card:
                timeline_card.hide_extraction_progress()
            return
        
        # 옵션 가져오기
        format_ext = self.format_combo.currentText().lower()
        quality = self.quality_spin.value()
        scale = self.scale_spin.value()
        
        # 추출 모드 확인 (단일 선택)
        mode = None
        if self.all_frames_check.isChecked():
            mode = ("all_frames", None)
        elif self.fps_interval_check.isChecked():
            # 1초당 n프레임 추출
            fps_value = self.fps_interval_spin.value()
            mode = ("fps_interval", fps_value)
        elif self.time_interval_check.isChecked():
            # n초당 1프레임 추출
            time_value = self.time_interval_spin.value()
            mode = ("time_interval", time_value)
        elif self.keyframes_only_check.isChecked():
            mode = ("keyframes_only", None)
        else:
            print("❌ 추출 모드를 선택해주세요.")
            return
        
        start_time = self.start_edit.text()
        end_time = self.end_edit.text()
        deduplicate = self.deduplicate_check.isChecked()
        
        # 시간 문자열을 초로 변환
        start_time_sec = self._parse_time_string(start_time)
        end_time_sec = self._parse_time_string(end_time)
        
        print(f"Format: {format_ext}, Quality: {quality}, Scale: {scale}%")
        print(f"Mode: {mode}")
        print(f"Range: {start_time} ({start_time_sec}s) - {end_time} ({end_time_sec}s)")
        print(f"🔍 중복제거 체크박스 상태: {deduplicate} (체크됨: {self.deduplicate_check.isChecked()})")
        print(f"Video: {video_path}")
        
        # FFmpeg로 프레임 추출 (진행바 전달)
        frames_data = self._extract_frames_with_ffmpeg(
            video_path, mode, start_time_sec, end_time_sec, scale, format_ext, timeline_card
        )
        
        # 중복 제거
        if deduplicate and frames_data:
            print(f"🔄 중복 제거 시작: 총 {len(frames_data)}개 프레임")
            # 중복 제거 작업 시작 - 진행바 초기화
            if timeline_card:
                timeline_card.update_extraction_progress(0, "중복 제거 중...")
                QApplication.processEvents()  # UI 즉시 업데이트
            
            original_count = len(frames_data)
            unique_frames = []
            seen_hashes = set()
            import hashlib
            
            for idx, (pixmap, time_ms) in enumerate(frames_data):
                # 진행바 업데이트: 중복 제거 중 (0-100%)
                if timeline_card and original_count > 0:
                    dedup_progress = int((idx / original_count) * 100)
                    timeline_card.update_extraction_progress(dedup_progress, "중복 제거 중...")
                    # 주기적으로 UI 업데이트 (너무 자주 호출하지 않도록)
                    if idx % 10 == 0 or idx == original_count - 1:
                        QApplication.processEvents()
                
                # 프레임을 작은 썸네일로 변환하여 해시 계산
                thumb = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image = thumb.toImage()
                
                # QImage를 바이트로 변환
                buffer = QBuffer()
                buffer.open(QIODevice.WriteOnly)
                image.save(buffer, "PNG")
                image_bytes = buffer.data()
                
                frame_hash = hashlib.md5(image_bytes).hexdigest()
                
                if frame_hash not in seen_hashes:
                    seen_hashes.add(frame_hash)
                    unique_frames.append((pixmap, time_ms))
                else:
                    print(f"  ⚠️ 중복 프레임 발견: {time_ms}ms (해시: {frame_hash[:8]}...)")
            
            frames_data = unique_frames
            removed_count = original_count - len(frames_data)
            print(f"✅ 중복 제거 완료: {original_count}개 → {len(frames_data)}개 (제거됨: {removed_count}개)")
            
            # 중복 제거 완료 - 다음 작업으로 전환
            if timeline_card:
                timeline_card.update_extraction_progress(0, "프레임 컨테이너에 추가 중...")
                QApplication.processEvents()  # UI 즉시 업데이트
        elif deduplicate and not frames_data:
            print(f"⚠️ 중복 제거 체크됨 but 프레임 데이터 없음 (frames_data: {frames_data})")
        elif not deduplicate:
            print(f"ℹ️ 중복 제거 비활성화됨 (체크박스 해제)")
        
        # 프레임 컨테이너에 전달
        if hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
            if hasattr(self.app_instance.video_frame_module, 'frame_container_card'):
                frame_container = self.app_instance.video_frame_module.frame_container_card
                if frame_container:
                    # 프레임 컨테이너 추가 작업 시작 (중복 제거가 없었으면 여기서 시작)
                    if timeline_card and not deduplicate:
                        timeline_card.update_extraction_progress(0, "프레임 컨테이너에 추가 중...")
                        QApplication.processEvents()  # UI 즉시 업데이트
                    
                    # 기존 프레임 제거
                    frame_container.clear_frames()
                    
                    # 새 프레임 추가 (페이지네이션 적용)
                    if frames_data:
                        total_frames = len(frames_data)
                        
                        # 진행바 업데이트: 프레임 데이터 저장 중
                        if timeline_card:
                            timeline_card.update_extraction_progress(50, "프레임 데이터 저장 중...")
                            QApplication.processEvents()
                        
                        # all_frames_data에 모든 프레임 저장 (페이지네이션용)
                        frame_container.all_frames_data = frames_data.copy()
                        
                        # 프레임 캐시에도 저장
                        for pixmap, time_ms in frames_data:
                            frame_container.frame_cache[time_ms] = pixmap
                        
                        # 첫 페이지로 초기화
                        frame_container.frame_current_page = 1
                        
                        # 진행바 업데이트: 프레임 표시 중
                        if timeline_card:
                            timeline_card.update_extraction_progress(80, "프레임 표시 중...")
                            QApplication.processEvents()
                        
                        # 현재 페이지의 프레임만 표시 (페이지네이션 적용)
                        frame_container.refresh_frame_thumbnails()
                        
                        # 프레임 추가 후 스크롤바 생겼는지 확인하고 썸네일 크기 재조정
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(100, frame_container._adjust_thumbnails_for_scrollbar)
                    
                    print(f"✅ 프레임 컨테이너에 {len(frames_data)}개 프레임 추가 완료")
                    
                    # 프레임 컨테이너로 자동 스크롤 (선택사항)
                    # self._scroll_to_frame_container()
                    
                    # 진행바 업데이트: 완료 (100%) 후 숨김
                    if timeline_card:
                        timeline_card.update_extraction_progress(100, "프레임 컨테이너에 추가 중...")
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(1000, timeline_card.hide_extraction_progress)


def create_video_frame_extraction_options(app_instance):
    """비디오 프레임 추출 옵션 위젯 생성"""
    return VideoFrameExtractionOptions(app_instance)

