"""
Video Frame Container Module - 동영상 프레임 컨테이너 모듈
- 비디오 프리뷰 오른쪽에 프레임들을 그리드 형태로 표시
- 태그 트리처럼 별도 모듈로 구성
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget, QGridLayout, QSizePolicy, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
from pathlib import Path
import cv2


class FrameThumbnail(QFrame):
    """프레임 썸네일 위젯 (서치 필터 그리드와 동일한 디자인)"""
    
    def __init__(self, frame_pixmap, frame_time_ms, available_width=None, parent=None):
        super().__init__(parent)
        self.frame_time_ms = frame_time_ms
        self.is_current = False  # 현재 선택된 프레임인지
        self.is_multi = False  # 다중 선택된 프레임인지
        
        self.setObjectName("FrameThumb")
        # 상대 사이즈: 가용 너비 기준으로 계산 (2열 배열)
        margin = 2
        # 가용 너비가 없으면 부모 위젯의 너비를 기준으로 계산
        if available_width is None:
            if parent:
                available_width = parent.width() if parent.width() > 0 else 300
            else:
                available_width = 300  # 기본값
        
        # 2열 배열: (가용 너비 - 좌우 여백 - 열 간격) / 2
        spacing = 4  # 그리드 spacing
        grid_margins = 4 * 2  # 좌우 여백
        item_width = (available_width - grid_margins - spacing) // 2
        item_width = max(item_width, 50)  # 최소 50px
        
        # 원본 비율 유지하며 높이 계산
        if frame_pixmap.width() > 0:
            aspect_ratio = frame_pixmap.height() / frame_pixmap.width()
            calculated_height = int(item_width * aspect_ratio)
        else:
            calculated_height = 80  # 기본값
        
        self.setFixedSize(item_width + margin, calculated_height + margin)
        
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)  # 이미지와 테두리 사이 여백
        layout.setSpacing(0)
        
        # 썸네일 라벨 (원본 해상도 pixmap 저장, 위젯 크기에 맞춰 표시)
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setScaledContents(True)  # 위젯 크기에 맞춰 스케일링 (원본 해상도는 유지)
        self.thumb_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
        """)
        # 원본 해상도 pixmap 저장 (해상도 다운그레이드 안 함)
        self.thumb_label.setPixmap(frame_pixmap)
        layout.addWidget(self.thumb_label)
        
        # 초기 스타일 설정
        self.update_selection()
        
        # 툴팁 비활성화 (오버레이 방지)
        self.setToolTip("")
    
    def update_selection(self):
        """선택 상태에 따라 테두리 스타일 업데이트 (서치 필터 그리드와 동일)"""
        if self.is_current:
            self.setStyleSheet("""
                QFrame#FrameThumb {
                    background: transparent;
                    border: 2px solid #3B82F6;
                    border-radius: 4px;
                }
                QFrame#FrameThumb:hover {
                    border: 2px solid #3B82F6;
                }
            """)
        elif self.is_multi:
            self.setStyleSheet("""
                QFrame#FrameThumb {
                    background: transparent;
                    border: 2px solid #10B981;
                    border-radius: 4px;
                }
                QFrame#FrameThumb:hover {
                    border: 2px solid #10B981;
                }
            """)
        else:
            # 기본 상태: 투명 테두리, 호버 시 파란색
            self.setStyleSheet("""
                QFrame#FrameThumb {
                    background: transparent;
                    border: 2px solid transparent;
                    border-radius: 4px;
                }
                QFrame#FrameThumb:hover {
                    border: 2px solid #3B82F6;
                    border-radius: 4px;
                }
            """)


class VideoFrameContainerCard(QFrame):
    """비디오 프레임 컨테이너 카드"""
    
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.current_video_path = None
        self.frame_thumbnails = []  # 현재 표시된 프레임 썸네일들
        self.frame_cache = {}  # 프레임 캐시 {time_ms: QPixmap}
        self.all_frames_data = []  # 모든 프레임 데이터 (페이지네이션용) [(pixmap, time_ms), ...]
        self.frame_current_page = 1  # 현재 페이지
        self.frame_items_per_page = 50  # 페이지당 프레임 개수
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        self.setObjectName("VideoFrameContainerCard")
        self.setStyleSheet("""
            QFrame#VideoFrameContainerCard {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 6px;
                margin: 4px;
            }
        """)
        
        # 태그 트리와 동일한 고정 너비 설정
        self.setFixedWidth(300)
        
        # 메인 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        
        # 헤더 라벨 (프레임 개수 표시용)
        self.header_label = QLabel("FRAME CONTAINER")
        self.header_label.setTextFormat(Qt.RichText)  # HTML 형식 지원
        self.header_label.setStyleSheet("""
            QLabel {
                font-size: 11px; 
                font-weight: 700;
                color: #9CA3AF; 
                letter-spacing: 1px;
                margin-bottom: 8px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.header_label)
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # viewport에 오른쪽 여백 추가하여 스크롤바를 오른쪽으로 밀기
        scroll.setViewportMargins(0, 0, 2, 0)  # 오른쪽 여백 2px
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background: rgba(26,27,38,0.8);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(75,85,99,0.6);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(75,85,99,0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 프레임 그리드 컨테이너
        self.frame_container = QWidget()
        # setWidgetResizable(True)를 사용하면 자동으로 스크롤바 공간이 확보되므로
        # 최대 너비 제한이 필요 없음 (서치 필터 그리드와 동일)
        self.frame_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 최소 높이만 사용
        self.frame_grid = QGridLayout(self.frame_container)
        self.frame_grid.setSpacing(4)
        # 오른쪽 스크롤바에서 프레임이 잘리지 않도록 오른쪽 여백 추가
        self.frame_grid.setContentsMargins(4, 4, 4, 4)
        # 상단 정렬 설정 (위아래 여백 없이 상단부터 배치)
        self.frame_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        scroll.setWidget(self.frame_container)
        layout.addWidget(scroll)
        self.scroll = scroll  # 스크롤바 너비 계산용 참조 저장
        
        # 페이지네이션 UI 추가
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 8, 0, 0)
        pagination_layout.setSpacing(4)
        
        # 이전 페이지 버튼
        self.frame_prev_page_btn = QPushButton("❮")
        self.frame_prev_page_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(75,85,99,0.3);
                color: #F0F2F5;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: rgba(75,85,99,0.5);
            }
            QPushButton:disabled {
                background: transparent;
                border-color: rgba(75,85,99,0.3);
                color: #F0F2F5;
            }
        """)
        self.frame_prev_page_btn.clicked.connect(lambda: self.change_frame_page(-1))
        
        # 페이지 정보 라벨
        self.frame_page_label = QLabel("0 / 0")
        self.frame_page_label.setStyleSheet("""
            color: #9CA3AF;
            font-size: 11px;
            padding: 4px 8px;
        """)
        self.frame_page_label.setAlignment(Qt.AlignCenter)
        self.frame_page_label.setMinimumWidth(60)
        
        # 다음 페이지 버튼
        self.frame_next_page_btn = QPushButton("❯")
        self.frame_next_page_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(75,85,99,0.3);
                color: #F0F2F5;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: rgba(75,85,99,0.5);
            }
            QPushButton:disabled {
                background: transparent;
                border-color: rgba(75,85,99,0.3);
                color: #F0F2F5;
            }
        """)
        self.frame_next_page_btn.clicked.connect(lambda: self.change_frame_page(1))
        
        # 페이지네이션을 중앙 정렬
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.frame_prev_page_btn)
        pagination_layout.addWidget(self.frame_page_label)
        pagination_layout.addWidget(self.frame_next_page_btn)
        pagination_layout.addStretch()
        
        layout.addLayout(pagination_layout)
    
    def load_video_frames(self, video_path, frame_interval_seconds=1.0):
        """비디오에서 프레임 추출 및 표시 (페이지네이션 적용)"""
        if not video_path or not Path(video_path).exists():
            self.clear_frames()
            return
        
        self.current_video_path = video_path
        
        try:
            # OpenCV로 비디오 열기
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                print(f"❌ 비디오 파일을 열 수 없습니다: {video_path}")
                self.clear_frames()
                return
            
            # 비디오 정보 가져오기
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_ms = int((total_frames / fps) * 1000) if fps > 0 else 0
            
            # 프레임 간격을 밀리초로 변환 (기본값: 1초마다)
            frame_interval_ms = int(frame_interval_seconds * 1000)
            
            # 기존 프레임들 제거
            self.clear_frames()
            
            # 프레임 추출 (간격마다 추출, 모든 프레임을 all_frames_data에 저장)
            self.all_frames_data = []
            current_time_ms = 0
            
            while current_time_ms < duration_ms:
                frame_number = int((current_time_ms / 1000.0) * fps) if fps > 0 else 0
                
                # 비디오에서 프레임 읽기
                cap.set(cv2.CAP_PROP_POS_FRAMES, min(frame_number, total_frames - 1))
                ret, frame = cap.read()
                
                if ret:
                    # BGR을 RGB로 변환
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image)
                    
                    # 캐시에 저장
                    self.frame_cache[current_time_ms] = pixmap
                    self.all_frames_data.append((pixmap, current_time_ms))
                else:
                    # 실패 시 플레이스홀더
                    thumb = QPixmap(120, 80)
                    from PySide6.QtGui import QColor
                    thumb.fill(QColor(60, 60, 60))
                    self.all_frames_data.append((thumb, current_time_ms))
                
                # 다음 프레임 시간으로 이동
                current_time_ms += frame_interval_ms
            
            cap.release()
            
            # 첫 페이지로 초기화
            self.frame_current_page = 1
            
            # 현재 페이지의 프레임만 표시
            self.refresh_frame_thumbnails()
            
            print(f"✅ 프레임 컨테이너: {len(self.all_frames_data)}개 프레임 추출 완료 (페이지네이션 적용)")
            
        except ImportError:
            print("⚠️ OpenCV가 설치되지 않았습니다")
            self.clear_frames()
        except Exception as e:
            print(f"❌ 프레임 추출 오류: {e}")
            import traceback
            traceback.print_exc()
            self.clear_frames()
    
    def refresh_frame_thumbnails(self):
        """현재 페이지의 프레임만 표시"""
        # 기존 썸네일들 제거
        for thumbnail in self.frame_thumbnails:
            self.frame_grid.removeWidget(thumbnail)
            thumbnail.deleteLater()
        self.frame_thumbnails.clear()
        
        if not self.all_frames_data:
            self.update_frame_pagination_ui()
            self.update_header_count()
            return
        
        # 현재 페이지에 해당하는 프레임만 추출
        items_per_page = self.frame_items_per_page
        current_page = self.frame_current_page
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        
        current_page_frames = self.all_frames_data[start_idx:end_idx]
        
        if current_page_frames:
            # 초기 가용 너비 계산 (컨테이너 너비 기준)
            container_width = self.frame_container.width()
            if container_width <= 0:
                container_width = 300  # 기본값
            
            for idx, (pixmap, time_ms) in enumerate(current_page_frames):
                row = idx // 2
                col = idx % 2
                
                # 원본 해상도 그대로 사용, 상대 사이즈로 썸네일 생성
                thumbnail = FrameThumbnail(pixmap, time_ms, available_width=container_width)
                
                # 클릭 이벤트 연결 (비디오 재생 위치 이동)
                def make_click_handler(t):
                    def handler(event):
                        self.on_frame_clicked(t)
                    return handler
                thumbnail.mousePressEvent = make_click_handler(time_ms)
                
                self.frame_grid.addWidget(thumbnail, row, col)
                self.frame_thumbnails.append(thumbnail)
            
            # 프레임 추가 후 스크롤바 생겼는지 확인하고 썸네일 크기 재조정
            QTimer.singleShot(100, self._adjust_thumbnails_for_scrollbar)
        
        # 페이지네이션 UI 업데이트
        self.update_frame_pagination_ui()
        
        # 헤더에 프레임 개수 업데이트
        self.update_header_count()
    
    def change_frame_page(self, direction):
        """프레임 페이지 변경 (direction: -1 이전, 1 다음)"""
        if not self.all_frames_data:
            return
        
        total_items = len(self.all_frames_data)
        if total_items == 0:
            return
        
        items_per_page = self.frame_items_per_page
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        # 현재 페이지 업데이트
        current_page = self.frame_current_page
        new_page = current_page + direction
        
        # 페이지 범위 제한
        if new_page < 1 or new_page > total_pages:
            return
        
        self.frame_current_page = new_page
        
        # 스크롤 위치 초기화
        if hasattr(self, 'scroll') and self.scroll:
            self.scroll.verticalScrollBar().setValue(0)
        
        # 썸네일 재생성
        self.refresh_frame_thumbnails()
        
        print(f"프레임 페이지 변경: {new_page} / {total_pages}")
    
    def update_frame_pagination_ui(self):
        """프레임 페이지네이션 UI 업데이트"""
        if not hasattr(self, 'frame_page_label'):
            return
        
        total_items = len(self.all_frames_data)
        if total_items == 0:
            self.frame_page_label.setText("0 / 0")
            self.frame_prev_page_btn.setEnabled(False)
            self.frame_next_page_btn.setEnabled(False)
            return
        
        items_per_page = self.frame_items_per_page
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        current_page = self.frame_current_page
        
        # 페이지 범위 조정
        if current_page > total_pages:
            self.frame_current_page = total_pages
            current_page = total_pages
        
        self.frame_page_label.setText(f"{current_page} / {total_pages}")
        self.frame_prev_page_btn.setEnabled(current_page > 1)
        self.frame_next_page_btn.setEnabled(current_page < total_pages)
    
    def _adjust_thumbnails_for_scrollbar(self):
        """스크롤바가 생겼을 때 썸네일 크기 재조정"""
        if not self.frame_thumbnails:
            return
        
        # 스크롤바 너비 감안한 실제 가용 너비 계산
        if hasattr(self, 'scroll') and self.scroll:
            # viewport 너비 사용 (스크롤바 제외된 실제 가용 너비)
            available_width = self.scroll.viewport().width()
        else:
            # 폴백: 컨테이너 너비에서 스크롤바 너비(약 8px) 빼기
            container_width = self.frame_container.width()
            available_width = container_width - 10 if container_width > 0 else 290
        
        if available_width <= 0:
            available_width = 290  # 기본값
        
        # 모든 썸네일 크기 재조정
        for thumbnail in self.frame_thumbnails:
            if hasattr(thumbnail, 'thumb_label') and thumbnail.thumb_label.pixmap():
                pixmap = thumbnail.thumb_label.pixmap()
                if not pixmap.isNull():
                    # 새로운 크기 계산
                    margin = 2
                    spacing = 4
                    grid_margins = 4 * 2
                    item_width = (available_width - grid_margins - spacing) // 2
                    item_width = max(item_width, 50)
                    
                    # 원본 비율 유지하며 높이 계산
                    if pixmap.width() > 0:
                        aspect_ratio = pixmap.height() / pixmap.width()
                        calculated_height = int(item_width * aspect_ratio)
                    else:
                        calculated_height = 80
                    
                    # 크기 재설정
                    thumbnail.setFixedSize(item_width + margin, calculated_height + margin)
    
    def on_frame_clicked(self, time_ms):
        """프레임 클릭 시 비디오 재생 위치 이동 및 선택 상태 업데이트"""
        # 모든 프레임의 선택 상태 초기화
        for thumbnail in self.frame_thumbnails:
            thumbnail.is_current = False
            thumbnail.update_selection()
        
        # 클릭된 프레임 찾아서 선택 상태 설정
        for thumbnail in self.frame_thumbnails:
            if thumbnail.frame_time_ms == time_ms:
                thumbnail.is_current = True
                thumbnail.update_selection()
                break
        
        # 비디오 재생 위치 이동
        if hasattr(self.app_instance, 'video_frame_module'):
            if self.app_instance.video_frame_module and self.app_instance.video_frame_module.video_preview_card:
                media_player = self.app_instance.video_frame_module.video_preview_card.media_player
                if media_player:
                    media_player.setPosition(time_ms)
                    print(f"▶️ 프레임 클릭: {time_ms}ms로 이동")
    
    def clear_frames(self):
        """프레임들 제거"""
        # 기존 썸네일들 제거
        for thumbnail in self.frame_thumbnails:
            self.frame_grid.removeWidget(thumbnail)
            thumbnail.deleteLater()
        self.frame_thumbnails.clear()
        self.frame_cache.clear()
        self.all_frames_data.clear()
        self.frame_current_page = 1
        # 페이지네이션 UI 업데이트
        if hasattr(self, 'frame_page_label'):
            self.update_frame_pagination_ui()
        # 헤더에 프레임 개수 업데이트
        self.update_header_count()
    
    def update_current_position(self, position_ms):
        """현재 재생 위치에 해당하는 프레임 강조"""
        # 프레임 강조 기능 (선택사항)
        pass
    
    def update_header_count(self):
        """헤더에 현재 프레임 개수 표시 (태그 스타일시트 모듈과 동일한 형식)"""
        total_frame_count = len(self.all_frames_data)
        current_page_frame_count = len(self.frame_thumbnails)
        if hasattr(self, 'header_label'):
            # 전체 프레임 개수 표시
            frame_text = "frame" if total_frame_count == 1 else "frames"
            self.header_label.setText(f"FRAME CONTAINER <span style='font-size: 9px; color: #6B7280;'>({total_frame_count} {frame_text})</span>")


def create_video_frame_container_card(app_instance):
    """비디오 프레임 컨테이너 카드 생성"""
    return VideoFrameContainerCard(app_instance)

