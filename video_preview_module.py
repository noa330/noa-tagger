"""
Video Preview Module - 동영상 프리뷰 모듈
- 비디오 모드일 때 중앙 패널들을 숨기고 비디오 프리뷰를 표시
- center_panel_overlay_plugin을 사용하여 오버레이 시스템 구현
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QPushButton, QHBoxLayout, QSizePolicy, QSlider, QScrollArea, QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, QUrl, QTimer, QEvent, QRect, QPoint, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QImage
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from pathlib import Path
from video_timeline_module import VideoTimelineCard


class VideoPreviewCard(QFrame):
    """비디오 프리뷰용 카드 - 실제 비디오 플레이어 포함"""
    
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.media_player = None
        self.audio_output = None
        self.video_widget = None
        self.video_container = None
        self.controls_widget = None
        self.current_video_path = None
        self.is_slider_dragging = False
        self.is_playhead_dragging = False  # 헤드 드래그 중 플래그
        self.timeline_card = None  # 외부 타임라인 카드 참조
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        self.setObjectName("VideoPreviewCard")
        self.setStyleSheet("""
            QFrame#VideoPreviewCard {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 6px;
                margin: 4px;
            }
        """)
        
        # 🔧 최대/최소 좌우 길이 설정 (더 넓게)
        self.setMinimumWidth(400)  # 최소 너비 400px
        self.setMaximumWidth(2000)  # 최대 너비 2000px
        
        # 메인 레이아웃 - SectionCard와 통일
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        
        # 헤더 라벨 ("VIDEO PREVIEW") - SectionCard 스타일과 통일
        header_label = QLabel("VIDEO PREVIEW")
        header_label.setStyleSheet("""
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
        layout.addWidget(header_label)
        
        # 비디오 컨테이너와 네비게이션 버튼 레이아웃
        video_nav_layout = QHBoxLayout()
        video_nav_layout.setSpacing(8)
        
        # Previous button (left side)
        self.btn_prev_video = QPushButton("〈")
        self.btn_prev_video.setMinimumSize(50, 40)
        self.btn_prev_video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_prev_video.setToolTip("Previous video")
        self.btn_prev_video.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #CFD8DC;
                border: none;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FFFFFF;
                font-size: 28px;
            }
            QPushButton:pressed {
                color: #9CA3AF;
                font-size: 24px;
            }
        """)
        self.btn_prev_video.clicked.connect(self.previous_video)
        
        # Next button (right side)
        self.btn_next_video = QPushButton("〉")
        self.btn_next_video.setMinimumSize(50, 40)
        self.btn_next_video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_next_video.setToolTip("Next video")
        self.btn_next_video.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #CFD8DC;
                border: none;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FFFFFF;
                font-size: 28px;
            }
            QPushButton:pressed {
                color: #9CA3AF;
                font-size: 24px;
            }
        """)
        self.btn_next_video.clicked.connect(self.next_video)
        
        # 비디오 컨테이너 (비디오 위젯을 담는 컨테이너)
        self.video_container = QWidget()
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 최소 크기 제한 제거 (이미지 프리뷰처럼 자유롭게 축소/확대 가능하도록)
        self.video_container.setMinimumSize(1, 1)
        self.video_container.setStyleSheet("""
            QWidget {
                background: rgba(26,27,38,0.8);
                border: 2px dashed rgba(75,85,99,0.3);
                border-radius: 12px;
            }
        """)
        # 컨테이너 리사이즈 이벤트 감지 (자동 스케일링용)
        self.video_container.installEventFilter(self)
        
        # 초기 텍스트 플레이스홀더 라벨 (비디오가 없을 때 표시)
        self.placeholder_label = QLabel("Select a video to preview", self.video_container)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #9CA3AF;
                font-size: 14px;
                border: none;
            }
        """)
        
        # QGraphicsView와 QGraphicsScene을 사용하여 투명 배경 비디오 재생
        self.video_graphics_view = QGraphicsView(self.video_container)
        # QGraphicsView의 프레임과 테두리 완전히 제거 (컨테이너 테두리만 보이도록)
        self.video_graphics_view.setFrameShape(QFrame.NoFrame)
        self.video_graphics_view.setStyleSheet("""
            QGraphicsView {
                background: transparent;
                border: none;
                outline: none;
            }
        """)
        self.video_graphics_view.setRenderHint(QPainter.Antialiasing)
        self.video_graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.video_graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Graphics Scene 생성 (투명 배경)
        self.video_scene = QGraphicsScene()
        self.video_scene.setBackgroundBrush(Qt.transparent)  # 배경 투명 설정
        self.video_graphics_view.setScene(self.video_scene)
        
        # QGraphicsVideoItem 생성 (투명 배경 지원)
        self.video_item = QGraphicsVideoItem()
        self.video_item.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video_scene.addItem(self.video_item)
        
        # 기존 QVideoWidget 호환성을 위한 참조 (나중에 제거 가능)
        self.video_widget = None
        self.video_graphics_view.hide()  # 초기에는 숨김
        
        # Media Player 및 Audio Output 설정
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0)
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_item)
        
        # 에러 및 상태 변화 신호 연결
        self.media_player.errorOccurred.connect(self.on_error)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        
        # 네비게이션 레이아웃에 추가
        video_nav_layout.addWidget(self.btn_prev_video)
        video_nav_layout.addWidget(self.video_container, 1)  # stretch factor 1
        video_nav_layout.addWidget(self.btn_next_video)
        
        # 메인 레이아웃에 비디오 네비게이션 레이아웃 추가
        layout.addLayout(video_nav_layout, 1)
        
        # 컨트롤 바 생성 (비디오 아래에 배치)
        self.create_controls()
        
        # 컨트롤 바를 레이아웃에 추가
        layout.addWidget(self.controls_widget, 0)

        # 이벤트 필터 설치 (리사이즈 감지용)
        self.video_container.installEventFilter(self)
    
    def attach_timeline_card(self, timeline_card):
        """외부 비디오 타임라인 카드를 연결"""
        # 기존 연결 해제
        if self.timeline_card:
            try:
                self.timeline_card.selectionChanged.disconnect(self.on_frame_selection_changed)
            except Exception:
                pass
            try:
                self.timeline_card.needMoreFrames.disconnect(self.generate_frames)
            except Exception:
                pass
            try:
                self.timeline_card.positionChanged.disconnect(self.on_playhead_position_changed)
            except Exception:
                pass
            try:
                self.timeline_card.playheadDragStarted.disconnect(self.on_playhead_drag_started)
            except Exception:
                pass
            try:
                self.timeline_card.playheadDragEnded.disconnect(self.on_playhead_drag_ended)
            except Exception:
                pass
        
        self.timeline_card = timeline_card
        
        if self.timeline_card:
            self.timeline_card.selectionChanged.connect(self.on_frame_selection_changed)
            self.timeline_card.needMoreFrames.connect(self.generate_frames)
            self.timeline_card.positionChanged.connect(self.on_playhead_position_changed)
            self.timeline_card.playheadDragStarted.connect(self.on_playhead_drag_started)
            self.timeline_card.playheadDragEnded.connect(self.on_playhead_drag_ended)

    def create_controls(self):
        """비디오 아래에 배치되는 컨트롤 바 생성"""
        # 컨트롤 바 위젯 (비디오 아래에 배치)
        self.controls_widget = QWidget()
        self.controls_widget.setObjectName("ControlsWidget")
        self.controls_widget.setStyleSheet("""
            QWidget#ControlsWidget {
                background: qlineargradient(to top,
                    stop:0 rgba(0, 0, 0, 0.85), 
                    stop:1 rgba(0, 0, 0, 0.95));
                border: none;
                border-radius: 0px 0px 12px 12px;
                padding: 12px;
            }
        """)
        
        # 한 줄 컨트롤 레이아웃 (버튼 + 슬라이더 + 시간)
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(12, 8, 12, 12)
        controls_layout.setSpacing(8)
        
        # 재생/일시정지 버튼 (흰색) - 두 개의 막대를 절대 위치로 배치
        self.play_pause_btn = QPushButton()
        self.play_pause_btn.setFixedSize(32, 32)
        self.play_pause_btn.setCursor(Qt.PointingHandCursor)
        
        # 두 개의 막대 라벨 (절대 위치로 배치)
        self.pause_bar1 = QLabel("❚", self.play_pause_btn)
        self.pause_bar1.setAlignment(Qt.AlignCenter)
        self.pause_bar1.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                border: none;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        # 첫 번째 막대: 약간 왼쪽
        self.pause_bar1.setGeometry(7, 7, 8, 18)
        
        self.pause_bar2 = QLabel("❚", self.play_pause_btn)
        self.pause_bar2.setAlignment(Qt.AlignCenter)
        self.pause_bar2.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                border: none;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        # 두 번째 막대: 첫 번째 막대 옆 (약간의 간격)
        self.pause_bar2.setGeometry(17, 7, 8, 18)
        
        # 재생 삼각형 라벨
        self.play_triangle = QLabel("▶", self.play_pause_btn)
        self.play_triangle.setAlignment(Qt.AlignCenter)
        self.play_triangle.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                border: none;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.play_triangle.setGeometry(0, 0, 32, 32)
        self.play_triangle.hide()
        
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        
        # 기본 상태는 재생 버튼
        self.pause_bar1.hide()
        self.pause_bar2.hide()
        self.play_triangle.show()
        
        # 정지 버튼 (흰색)
        self.stop_btn = QPushButton("■")
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        self.stop_btn.clicked.connect(self.stop_video)
        
        # 진행 바 (슬라이더) - 중앙에 크게 배치
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 0.3);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #3B82F6;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #2563EB;
                width: 14px;
                height: 14px;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #3B82F6;
                border-radius: 2px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.valueChanged.connect(self.on_slider_value_changed)
        
        # 시간 표시 라벨
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)
        
        # 한 줄로 배치: 재생버튼 - 정지버튼 - 슬라이더(확장) - 시간
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.progress_slider, 1)  # stretch factor 1로 확장
        controls_layout.addWidget(self.time_label)
    
    def update_video_widget_size(self):
        """비디오 위젯 크기 업데이트 (이미지 프리뷰처럼 비율 유지하며 자동 스케일링)"""
        if not self.video_container or not self.video_graphics_view or not self.video_item:
            return
        
        container_rect = self.video_container.rect()
        
        if container_rect.width() > 0 and container_rect.height() > 0:
            # 테두리와 동영상 사이 여백 제거
            margin = 0
            available_width = container_rect.width()
            available_height = container_rect.height()
            
            # GraphicsView 크기 설정
            self.video_graphics_view.setGeometry(margin, margin, available_width, available_height)
            
            # 비디오 아이템 크기를 GraphicsView 크기에 맞춤
            self.video_item.setSize(QSize(available_width, available_height))
            
            # Scene의 크기도 설정
            self.video_scene.setSceneRect(0, 0, available_width, available_height)
            
            # GraphicsView가 최상위에 오도록
            self.video_graphics_view.raise_()
            # 플레이스홀더 라벨도 동일한 여백 적용
            if hasattr(self, 'placeholder_label'):
                self.placeholder_label.setGeometry(0, 0, available_width, available_height)
                self.placeholder_label.lower()
    
    def eventFilter(self, obj, event):
        """이벤트 필터로 리사이즈 처리"""
        if obj == self.video_container:
            if event.type() == QEvent.Resize:
                # 즉시 리사이즈 (이미지 프리뷰처럼 자동 스케일링)
                self.update_video_widget_size()
        return super().eventFilter(obj, event)
    
    def update_position(self, position):
        """재생 위치 업데이트"""
        # 헤드 드래그 중이면 업데이트 건너뛰기 (무한 루프 방지)
        if self.is_playhead_dragging:
            return
        
        # 재생이 끝났는지 확인 (position이 duration에 도달했거나 초과)
        duration = self.media_player.duration()
        if duration > 0 and position >= duration:
            # 0초로 되돌리고 정지
            self.media_player.setPosition(0)
            self.media_player.pause()
            # UI 업데이트
            self.pause_bar1.hide()
            self.pause_bar2.hide()
            self.play_triangle.show()
            # 슬라이더와 시간 라벨도 0초로 업데이트
            if not self.is_slider_dragging:
                self.progress_slider.setValue(0)
            current_time = self.format_time(0)
            total_time = self.format_time(duration)
            self.time_label.setText(f"{current_time} / {total_time}")
            # 타임라인도 0초로 업데이트
            if self.timeline_card:
                self.timeline_card.set_current_position(0)
            return
        
        if not self.is_slider_dragging:
            self.progress_slider.setValue(position)
        
        # 시간 표시 업데이트
        current_time = self.format_time(position)
        total_time = self.format_time(self.media_player.duration())
        self.time_label.setText(f"{current_time} / {total_time}")
        
        # 프레임 타임라인 재생 위치 업데이트
        if self.timeline_card:
            self.timeline_card.set_current_position(position)
    
    def update_duration(self, duration):
        """비디오 길이 업데이트"""
        self.progress_slider.setRange(0, duration)
        # 타임라인에도 duration 설정 (현재 재생 위치 기준으로 선택 범위 설정)
        if duration > 0 and self.timeline_card:
            current_position = self.media_player.position()
            self.timeline_card.set_duration(duration, current_position)
            
            # 프레임 추출 모듈의 시작/끝 시간을 새 비디오의 전체 범위로 갱신
            if hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
                if hasattr(self.app_instance.video_frame_module, 'frame_extraction_options'):
                    frame_extraction = self.app_instance.video_frame_module.frame_extraction_options
                    if frame_extraction:
                        frame_extraction.update_range_for_new_video(duration)
    
    def format_time(self, milliseconds):
        """밀리초를 MM:SS 형식으로 변환"""
        total_seconds = milliseconds // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def on_slider_pressed(self):
        """슬라이더 드래그 시작"""
        self.is_slider_dragging = True
    
    def on_slider_released(self):
        """슬라이더 드래그 종료 - 위치 이동"""
        self.is_slider_dragging = False
        self.media_player.setPosition(self.progress_slider.value())
    
    def on_slider_value_changed(self, value):
        """슬라이더 값 변경 (드래그 중)"""
        if self.is_slider_dragging:
            current_time = self.format_time(value)
            total_time = self.format_time(self.media_player.duration())
            self.time_label.setText(f"{current_time} / {total_time}")
    
    def load_video(self, video_path):
        """비디오 로드 및 재생"""
        try:
            import os
            # 파일 경로 확인
            if not os.path.exists(video_path):
                error_msg = f"파일을 찾을 수 없습니다: {video_path}"
                print(f"❌ {error_msg}")
                # 플레이스홀더 라벨 표시
                if hasattr(self, 'placeholder_label'):
                    self.placeholder_label.setText("File not found")
                    self.placeholder_label.show()
                self.video_graphics_view.hide()
                return
            
            print(f"🔄 비디오 로드 시작: {video_path}")
            self.current_video_path = video_path
            
            # 🔧 새 비디오 로드 시 타임라인 프레임 캐시 초기화
            if self.timeline_card:
                self.timeline_card.clear_cache()
            
            # 🔧 새 비디오 로드 시 프레임 컨테이너 완전히 비우기 (캐시 포함)
            if hasattr(self.app_instance, 'video_frame_module') and self.app_instance.video_frame_module:
                if hasattr(self.app_instance.video_frame_module, 'frame_container_card'):
                    frame_container = self.app_instance.video_frame_module.frame_container_card
                    if frame_container:
                        frame_container.clear_frames()
                        frame_container.current_video_path = None  # 현재 비디오 경로도 초기화
            
            # 절대 경로로 변환
            abs_path = os.path.abspath(video_path)
            video_url = QUrl.fromLocalFile(abs_path)
            
            print(f"🔄 비디오 URL 설정: {video_url.toString()}")
            self.media_player.setSource(video_url)
            
            # 플레이스홀더 라벨 숨기기 및 비디오 위젯 표시
            if hasattr(self, 'placeholder_label'):
                self.placeholder_label.hide()
            
            # 비디오 위젯 크기 즉시 업데이트 (타이밍 문제 해결)
            self.update_video_widget_size()
            
            # 비디오 GraphicsView 표시 및 최상위로
            self.video_graphics_view.show()
            self.video_graphics_view.raise_()
            
            # 재생 버튼 상태 업데이트 (일시정지)
            self.pause_bar1.show()
            self.pause_bar2.show()
            self.play_triangle.hide()
            
            # 비디오 위젯 크기 다시 업데이트 (레이아웃 완료 후)
            QTimer.singleShot(50, self.update_video_widget_size)
            QTimer.singleShot(200, self.update_video_widget_size)
            
            # 자동 재생 시작
            print(f"🔄 비디오 재생 시작")
            self.media_player.play()
            
            # 초기 프레임 로드 (필요한 것만)
            QTimer.singleShot(500, self.initial_frame_load)
            
            # 프레임 컨테이너는 프레임 추출 버튼을 눌렀을 때만 채워짐 (자동 로드 제거)
            
            print(f"✅ 비디오 로드됨: {video_path}")
        except Exception as e:
            error_msg = f"Error loading video: {str(e)}"
            print(f"❌ 비디오 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            # 예외 발생 시 플레이스홀더 라벨 표시
            if hasattr(self, 'placeholder_label'):
                self.placeholder_label.setText("Error loading video")
                self.placeholder_label.show()
            if hasattr(self, 'video_graphics_view'):
                self.video_graphics_view.hide()
    
    def on_error(self, error, error_string):
        """MediaPlayer 에러 처리"""
        print(f"❌ MediaPlayer 에러: {error} - {error_string}")
        self.pause_bar1.hide()
        self.pause_bar2.hide()
        self.play_triangle.show()
        # 에러 발생 시 플레이스홀더 라벨 표시
        if hasattr(self, 'placeholder_label'):
            self.placeholder_label.setText(f"Error loading video: {error_string}")
            self.placeholder_label.show()
        self.video_widget.hide()
    
    def on_media_status_changed(self, status):
        """미디어 상태 변화 처리"""
        pass
    
    def on_playback_state_changed(self, state):
        """재생 상태 변화 처리"""
        from PySide6.QtMultimedia import QMediaPlayer
        state_names = {
            QMediaPlayer.PlaybackState.StoppedState: "Stopped",
            QMediaPlayer.PlaybackState.PlayingState: "Playing",
            QMediaPlayer.PlaybackState.PausedState: "Paused",
        }
        print(f"▶️ 재생 상태 변화: {state_names.get(state, 'Unknown')}")
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.pause_bar1.show()
            self.pause_bar2.show()
            self.play_triangle.hide()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.pause_bar1.hide()
            self.pause_bar2.hide()
            self.play_triangle.show()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.pause_bar1.hide()
            self.pause_bar2.hide()
            self.play_triangle.show()
    
    def toggle_play_pause(self):
        """재생/일시정지 토글"""
        from PySide6.QtMultimedia import QMediaPlayer
        current_state = self.media_player.playbackState()
        
        if current_state == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.pause_bar1.hide()
            self.pause_bar2.hide()
            self.play_triangle.show()
        else:
            self.media_player.play()
            self.pause_bar1.show()
            self.pause_bar2.show()
            self.play_triangle.hide()
    
    def stop_video(self):
        """비디오 정지"""
        self.media_player.stop()
        self.pause_bar1.hide()
        self.pause_bar2.hide()
        self.play_triangle.show()
    
    def previous_video(self):
        """이전 비디오로 이동"""
        # 필터링된 비디오 목록 사용 (video_list가 있으면 사용, 없으면 video_files 사용)
        video_list = None
        if hasattr(self.app_instance, 'video_list') and self.app_instance.video_list:
            video_list = self.app_instance.video_list
        elif hasattr(self.app_instance, 'video_files') and self.app_instance.video_files:
            video_list = [str(v) for v in self.app_instance.video_files]
        
        if not video_list:
            return
        
        # 현재 비디오 인덱스 찾기
        current_index = -1
        if self.current_video_path:
            current_path_str = str(self.current_video_path)
            for i, video_path in enumerate(video_list):
                if str(video_path) == current_path_str:
                    current_index = i
                    break
        
        # 이전 비디오 인덱스 계산
        if current_index > 0:
            new_index = current_index - 1
        else:
            new_index = len(video_list) - 1  # 첫 번째에서 마지막으로
        
        # 비디오 로드
        load_video_from_module(self.app_instance, video_list[new_index])
    
    def next_video(self):
        """다음 비디오로 이동"""
        # 필터링된 비디오 목록 사용 (video_list가 있으면 사용, 없으면 video_files 사용)
        video_list = None
        if hasattr(self.app_instance, 'video_list') and self.app_instance.video_list:
            video_list = self.app_instance.video_list
        elif hasattr(self.app_instance, 'video_files') and self.app_instance.video_files:
            video_list = [str(v) for v in self.app_instance.video_files]
        
        if not video_list:
            return
        
        # 현재 비디오 인덱스 찾기
        current_index = -1
        if self.current_video_path:
            current_path_str = str(self.current_video_path)
            for i, video_path in enumerate(video_list):
                if str(video_path) == current_path_str:
                    current_index = i
                    break
        
        # 다음 비디오 인덱스 계산
        if current_index < len(video_list) - 1:
            new_index = current_index + 1
        else:
            new_index = 0  # 마지막에서 첫 번째로
        
        # 비디오 로드
        load_video_from_module(self.app_instance, video_list[new_index])
    
    def on_frame_selection_changed(self, start_ms, end_ms):
        """프레임 선택이 변경되었을 때 호출"""
        duration = self.media_player.duration()
        if duration > 0:
            start_time = self.format_time(start_ms)
            end_time = self.format_time(end_ms)
            total_time = self.format_time(duration)
            print(f"🎬 프레임 선택: {start_time} ~ {end_time} / {total_time}")
    
    def on_playhead_drag_started(self):
        """헤드 드래그 시작"""
        self.is_playhead_dragging = True
    
    def on_playhead_drag_ended(self):
        """헤드 드래그 종료"""
        self.is_playhead_dragging = False
    
    def on_playhead_position_changed(self, position_ms):
        """재생 헤드 위치가 변경되었을 때 호출 (헤드 드래그 시)"""
        if self.media_player:
            # 동영상 재생 위치 변경
            self.media_player.setPosition(position_ms)
            
            # 플레이어 하단 진행바와 시간 라벨도 실시간 반영
            if self.progress_slider and not self.is_slider_dragging:
                self.progress_slider.setValue(position_ms)
            if self.time_label:
                current_time = self.format_time(position_ms)
                total_time = self.format_time(self.media_player.duration())
                self.time_label.setText(f"{current_time} / {total_time}")
            
            # 프레임 타임라인의 현재 위치도 업데이트 (시각적 동기화)
            if self.timeline_card:
                self.timeline_card.set_current_position(position_ms)
    
    def generate_frames(self, time_list):
        """특정 시간의 프레임들만 생성 (스마트 캐싱)"""
        if not self.current_video_path or len(time_list) == 0:
            return
        
        print(f"🎬 {len(time_list)}개 프레임 생성 시작...")
        
        try:
            import cv2
            
            cap = cv2.VideoCapture(self.current_video_path)
            if not cap.isOpened():
                print("❌ 비디오 파일을 열 수 없습니다")
                return
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # 각 시간에 대해 프레임 추출
            for time_ms in time_list:
                frame_number = int((time_ms / 1000.0) * fps)
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()
                
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image)
                    
                    # 캐시에 추가
                    self.timeline_card.add_frame_to_cache(time_ms, pixmap)
                else:
                    # 실패 시 플레이스홀더
                    thumb = QPixmap(160, 90)
                    thumb.fill(QColor(40, 40, 60))
                    self.timeline_card.add_frame_to_cache(time_ms, thumb)
            
            cap.release()
            print(f"✅ {len(time_list)}개 프레임 생성 완료")
            
        except ImportError:
            print("⚠️ OpenCV가 설치되지 않았습니다")
            # 플레이스홀더
            for time_ms in time_list:
                thumb = QPixmap(160, 90)
                thumb.fill(QColor(60, 65, 80))
                self.timeline_card.add_frame_to_cache(time_ms, thumb)
                
        except Exception as e:
            print(f"❌ 프레임 생성 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def initial_frame_load(self):
        """비디오 로드 후 초기 프레임 요청"""
        if self.timeline_card:
            duration = self.media_player.duration()
            if duration > 0:
                # 현재 재생 위치 가져오기
                current_position = self.media_player.position()
                self.timeline_card.set_duration(duration, current_position)
                # 필요한 프레임 체크 및 요청
                QTimer.singleShot(100, self.timeline_card.check_and_request_frames)
    
    def cleanup(self):
        """리소스 정리"""
        if self.media_player:
            self.media_player.stop()
            self.media_player.setSource(QUrl())


class VideoFrameModule:
    """동영상 프레임 모듈"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.video_preview_card = None
        self.timeline_card = None
        self.frame_container_card = None  # 프레임 컨테이너 카드
        self.overlay_container = None
        self.overlay_plugin = None
        self.right_panel_hidden = False
        self.saved_left_panel_width = None  # 왼쪽 패널 폭 저장용
        self.saved_image_right_panel_width = None  # 이미지 모드용 오른쪽 패널 폭 저장용
        self.saved_video_right_panel_width = None  # 비디오 모드용 오른쪽 패널 폭 저장용
        self.saved_widget_visibility = {}  # 위젯 가시성 상태 저장용
        self.frame_extraction_options = None  # 프레임 추출 옵션 위젯
    
    def initialize(self):
        """모듈 초기화"""
        try:
            # center_panel_overlay_plugin import
            from center_panel_overlay_plugin import CenterPanelOverlayPlugin
            self.overlay_plugin = CenterPanelOverlayPlugin(self.app)
            
            # 비디오 프리뷰 카드 생성 (실제 플레이어 포함)
            self.video_preview_card = VideoPreviewCard(self.app)

            # 타임라인 카드 생성 및 연결
            self.timeline_card = VideoTimelineCard()
            self.video_preview_card.attach_timeline_card(self.timeline_card)

            # 프레임 컨테이너 카드 생성
            from video_frame_container_module import create_video_frame_container_card
            self.frame_container_card = create_video_frame_container_card(self.app)

            # 오버레이 컨테이너 구성
            # 이미지 모드와 동일한 구조:
            # 상단: 비디오 프리뷰(왼쪽) + 프레임 컨테이너(오른쪽) - 같은 높이
            # 하단: 타임라인 - 전체 너비
            self.overlay_container = QWidget()
            main_container_layout = QVBoxLayout(self.overlay_container)
            main_container_layout.setContentsMargins(10, 10, 10, 10)
            main_container_layout.setSpacing(12)
            
            # 상단 레이아웃 (비디오 프리뷰 + 프레임 컨테이너) - 같은 높이로 나란히
            # 이미지 모드의 태그 트리와 동일한 초기 폭을 보장하기 위해 stretch factor 동일하게 설정
            top_layout = QHBoxLayout()
            top_layout.setSpacing(10)
            top_layout.setContentsMargins(0, 0, 0, 0)
            
            # 비디오 프리뷰 (왼쪽, 확장) - 이미지 프리뷰와 동일한 stretch factor
            top_layout.addWidget(self.video_preview_card, 2)  # stretch factor 2
            
            # 프레임 컨테이너 (오른쪽, 고정 너비) - 태그 트리와 동일한 stretch factor 및 폭
            # 태그 트리와 동일한 초기 폭(300px) 보장
            top_layout.addWidget(self.frame_container_card, 1)  # stretch factor 1
            
            # 메인 컨테이너에 상단 레이아웃 추가
            main_container_layout.addLayout(top_layout)
            
            # 타임라인 (하단, 전체 너비)
            main_container_layout.addWidget(self.timeline_card)
            
            self.overlay_container.setStyleSheet("background: transparent;")
            
            print("Video Preview Module 초기화 완료 (프레임 컨테이너 포함)")
        except Exception as e:
            print(f"Video Preview Module 초기화 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def _hide_right_panel(self):
        """오른쪽 패널 내부 위젯들만 숨기기 (패널 자체는 유지)"""
        if hasattr(self.app, 'main_splitter') and self.app.main_splitter:
            # 🔧 이미지 모드의 오른쪽 패널 폭 저장 (비디오 모드로 전환하기 전)
            if self.app.main_splitter.count() > 2:
                right_panel = self.app.main_splitter.widget(2)
                if right_panel:
                    # 이미지 모드의 오른쪽 패널 크기 저장
                    self.saved_image_right_panel_width = right_panel.width()
                    print(f"이미지 모드 오른쪽 패널 폭 저장됨: {self.saved_image_right_panel_width}px")
                    
                    # 오른쪽 패널의 레이아웃 가져오기
                    layout = right_panel.layout()
                    if layout:
                        # 프레임 추출 옵션 위젯 생성 및 추가 (비디오 모드 전용) - 먼저 추가
                        if not self.frame_extraction_options:
                            from video_frame_extraction_module import create_video_frame_extraction_options
                            self.frame_extraction_options = create_video_frame_extraction_options(self.app)
                            self.frame_extraction_options.setObjectName("VideoFrameExtractionOptions")
                        
                        # 옵션 위젯이 레이아웃에 없으면 추가
                        if self.frame_extraction_options.parent() != right_panel:
                            layout.insertWidget(0, self.frame_extraction_options)  # 맨 위에 추가
                            print("프레임 추출 옵션 위젯을 오른쪽 패널에 추가")
                        
                        # 레이아웃의 모든 위젯 숨기기 (가시성 상태 저장)
                        # 프레임 추출 옵션은 제외하고 숨기기
                        self.saved_widget_visibility = {}
                        for i in range(layout.count()):
                            item = layout.itemAt(i)
                            if item and item.widget():
                                widget = item.widget()
                                # 프레임 추출 옵션 위젯은 건너뛰기
                                if widget == self.frame_extraction_options:
                                    widget.setVisible(True)  # 프레임 추출 옵션은 표시
                                    continue
                                # 위젯 ID 생성 (objectName이 있으면 사용, 없으면 인덱스 사용)
                                widget_id = widget.objectName() if widget.objectName() else f"widget_{i}"
                                # 현재 가시성 상태 저장
                                self.saved_widget_visibility[widget_id] = widget.isVisible()
                                # 위젯 숨기기
                                widget.setVisible(False)
                                print(f"오른쪽 패널 위젯 숨김: {widget.objectName() or type(widget).__name__}")
                        
                        print("프레임 추출 옵션 위젯 표시됨")
                    
                    # 태그 스타일시트 에디터 리모컨도 숨기기
                    if hasattr(self.app, 'tag_stylesheet_editor_remote') and self.app.tag_stylesheet_editor_remote:
                        if hasattr(self.app.tag_stylesheet_editor_remote, 'isVisible') and self.app.tag_stylesheet_editor_remote.isVisible():
                            self.app.tag_stylesheet_editor_remote.hide()
                            print("태그 스타일시트 에디터 리모컨 숨김")
                    
                    self.right_panel_hidden = True
                    print("오른쪽 패널 내부 위젯들 숨김 완료 (패널 자체는 유지)")
            
            # 🔧 왼쪽 패널 현재 폭 저장
            if self.app.main_splitter.count() > 0:
                left_panel = self.app.main_splitter.widget(0)
                if left_panel:
                    self.saved_left_panel_width = left_panel.width()
                    print(f"왼쪽 패널 폭 저장됨: {self.saved_left_panel_width}px")
    
    def _show_right_panel(self):
        """오른쪽 패널 내부 위젯들 다시 표시 (main.py와 동일한 방식으로 복구)"""
        print("=" * 50)
        print("[_show_right_panel] 오른쪽 패널 복구 시작")
        if hasattr(self.app, 'main_splitter') and self.app.main_splitter:
            # main_splitter에서 오른쪽 패널(인덱스 2)의 내부 위젯들 다시 표시
            if self.app.main_splitter.count() > 2:
                right_panel = self.app.main_splitter.widget(2)
                print(f"[_show_right_panel] 오른쪽 패널 확인: {right_panel is not None}, right_panel_hidden={self.right_panel_hidden}")
                if right_panel and self.right_panel_hidden:
                    # 오른쪽 패널의 레이아웃 가져오기
                    layout = right_panel.layout()
                    print(f"[_show_right_panel] 레이아웃 확인: {layout is not None}, 레이아웃 아이템 수: {layout.count() if layout else 0}")
                    if layout:
                        # 프레임 추출 옵션 위젯 숨기기
                        if self.frame_extraction_options:
                            self.frame_extraction_options.setVisible(False)
                        
                        # 🔧 간단하게: 모든 위젯 표시 (프레임 추출 옵션 제외)
                        # _hide_right_panel에서 setVisible(False)로 숨겼으므로, 가시성만 복구하면 됨
                        # 이미지 모드로 돌아올 때는 원래 보여야 하는 위젯들이므로 모두 True로 설정
                        for i in range(layout.count()):
                            item = layout.itemAt(i)
                            if item and item.widget():
                                widget = item.widget()
                                # 프레임 추출 옵션 위젯은 건너뛰기
                                if widget == self.frame_extraction_options:
                                    continue
                                
                                # 모든 위젯 표시 (이미지 모드 복구)
                                widget.setVisible(True)
                        
                        # 저장된 상태 초기화
                        self.saved_widget_visibility = {}
                        print("[_show_right_panel] 저장된 가시성 상태로 복구 완료")
                    
                    # 태그 스타일시트 에디터 리모컨도 다시 표시 (이전에 표시되어 있었다면)
                    # (리모컨은 사용자가 직접 여는 것이므로 여기서는 자동으로 표시하지 않음)
                    
                    self.right_panel_hidden = False
                    print("오른쪽 패널 내부 위젯들 다시 표시됨 (이미지 모드 위젯 복구 완료)")
            
            # 🔧 비디오 모드에서 이미지 모드로 전환 시 크기 복구
            if self.app.main_splitter.count() > 0:
                current_sizes = self.app.main_splitter.sizes()
                if len(current_sizes) >= 3:
                    total_width = sum(current_sizes)
                    left_width = current_sizes[0]
                    center_width = current_sizes[1]
                    
                    # 비디오 모드의 오른쪽 패널 크기 저장 (이미지 모드로 전환하기 전)
                    right_panel = self.app.main_splitter.widget(2)
                    if right_panel:
                        self.saved_video_right_panel_width = right_panel.width()
                        print(f"비디오 모드 오른쪽 패널 폭 저장됨: {self.saved_video_right_panel_width}px")
                    
                    # 이미지 모드의 오른쪽 패널 크기 복구 (저장된 값이 있으면)
                    if self.saved_image_right_panel_width is not None:
                        right_width = self.saved_image_right_panel_width
                        center_width = total_width - left_width - right_width
                        
                        # 중앙 패널이 너무 작으면 조정
                        if center_width < 200:
                            center_width = 200
                            right_width = total_width - left_width - center_width
                        
                        new_sizes = [left_width, center_width, right_width]
                        self.app.main_splitter.setSizes(new_sizes)
                        print(f"이미지 모드 오른쪽 패널 크기 복구: {new_sizes}")
                    else:
                        print(f"비디오 모드에서 이미지 모드로 전환 - 이미지 모드 오른쪽 패널 크기 저장값 없음, 현재 크기 유지: {current_sizes}")
                
                # 왼쪽 패널 크기 저장값 초기화 (더 이상 필요 없음)
                self.saved_left_panel_width = None
    
    def show_video_frame(self):
        """비디오 프레임 표시"""
        if not self.overlay_plugin or not self.overlay_container:
            print("Video Preview Module이 초기화되지 않았습니다")
            return
        
        try:
            # 🔧 오른쪽 패널 내부 위젯들만 숨기기 (패널 자체는 유지) - 먼저 실행
            self._hide_right_panel()
            
            # 🔧 태그 트리와 동일한 초기 폭 보장 (맨 처음 켰을 때 기준)
            if hasattr(self.app, 'tag_tree_card') and self.app.tag_tree_card:
                tag_tree_width = self.app.tag_tree_card.width()
                if tag_tree_width > 0 and self.frame_container_card:
                    # 태그 트리의 실제 폭을 프레임 컨테이너에 적용
                    self.frame_container_card.setFixedWidth(tag_tree_width)
                    print(f"프레임 컨테이너 폭을 태그 트리와 동일하게 설정: {tag_tree_width}px")
                elif self.frame_container_card:
                    # 태그 트리가 아직 표시되지 않았으면 기본값(300px) 사용
                    self.frame_container_card.setFixedWidth(300)
                    print("프레임 컨테이너 폭을 기본값(300px)으로 설정")
            
            # 오버레이 플러그인을 사용하여 비디오 프리뷰 + 타임라인 컨테이너 표시
            self.overlay_plugin.show_overlay_card(self.overlay_container, "video_frame")
            
            # 🔧 왼쪽/오른쪽 패널 폭 유지 (비디오 모드에서 현재 폭 유지) - 동일한 타이밍에 적용
            if hasattr(self.app, 'main_splitter') and self.app.main_splitter:
                if self.app.main_splitter.count() > 0:
                    current_sizes = self.app.main_splitter.sizes()
                    total_width = sum(current_sizes)
                    
                    # 왼쪽 패널 크기 유지
                    if self.saved_left_panel_width is not None and len(current_sizes) >= 2:
                        left_width = self.saved_left_panel_width
                        center_width = current_sizes[1] if len(current_sizes) > 1 else 0
                        right_width = current_sizes[2] if len(current_sizes) > 2 else 0
                        
                        # 비디오 모드의 오른쪽 패널 크기 복구 (저장된 값이 있으면)
                        if self.saved_video_right_panel_width is not None and len(current_sizes) >= 3:
                            right_width = self.saved_video_right_panel_width
                            # 중앙 패널 크기 계산 (나머지 공간)
                            center_width = total_width - left_width - right_width
                            
                            # 중앙 패널이 너무 작으면 조정
                            if center_width < 200:
                                center_width = 200
                                # 왼쪽과 오른쪽 패널 크기 유지하면서 중앙 패널 확보
                                available = total_width - center_width
                                if available > 0:
                                    # 왼쪽과 오른쪽 비율 유지
                                    left_ratio = left_width / (left_width + right_width) if (left_width + right_width) > 0 else 0.5
                                    left_width = int(available * left_ratio)
                                    right_width = available - left_width
                        else:
                            # 오른쪽 패널이 없거나 저장되지 않았으면 왼쪽 패널만 유지
                            remaining_width = total_width - left_width
                            if remaining_width > 0:
                                center_width = remaining_width - (right_width if len(current_sizes) > 2 else 0)
                                if len(current_sizes) > 2:
                                    right_width = current_sizes[2]
                                else:
                                    right_width = 0
                        
                        # 크기 적용
                        if len(current_sizes) >= 3:
                            new_sizes = [left_width, center_width, right_width]
                            self.app.main_splitter.setSizes(new_sizes)
                            print(f"왼쪽/오른쪽 패널 폭 유지됨: 왼쪽={left_width}px, 중앙={center_width}px, 오른쪽={right_width}px")
                        elif len(current_sizes) >= 2:
                            new_sizes = [left_width, center_width]
                            self.app.main_splitter.setSizes(new_sizes)
                            print(f"왼쪽 패널 폭 유지됨: {left_width}px")
            
            print("비디오 프레임 카드 표시됨")
        except Exception as e:
            print(f"비디오 프레임 표시 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def hide_video_frame(self):
        """비디오 프레임 숨김"""
        if not self.overlay_plugin:
            print("Video Frame Module이 초기화되지 않았습니다")
            return
        
        try:
            # 오버레이 플러그인을 사용하여 비디오 프레임 카드 숨김
            self.overlay_plugin.hide_overlay_card("video_frame")
            
            # 🔧 오른쪽 패널 내부 위젯들 다시 표시
            self._show_right_panel()
            
            # 🔧 왼쪽 패널 크기 제한 해제 (이미지 모드로 복귀)
            if hasattr(self.app, 'main_splitter') and self.app.main_splitter:
                if self.app.main_splitter.count() > 0:
                    left_panel = self.app.main_splitter.widget(0)
                    if left_panel:
                        # 크기 제한 해제 (기본 동작 복원)
                        left_panel.setMaximumWidth(16777215)  # 최대 크기 제한 해제
                        left_panel.setMinimumWidth(250)  # 최소 크기만 유지
                        print("왼쪽 패널 크기 제한 해제됨")
            
            # 비디오 정지 및 정리
            if self.video_preview_card:
                self.video_preview_card.cleanup()
            
            print("비디오 프레임 카드 숨김됨")
        except Exception as e:
            print(f"비디오 프레임 숨김 오류: {e}")
            import traceback
            traceback.print_exc()


def create_video_frame_module(app_instance):
    """비디오 프레임 모듈 생성 및 초기화"""
    video_frame_module = VideoFrameModule(app_instance)
    video_frame_module.initialize()
    return video_frame_module


def on_video_mode_activated(app_instance):
    """비디오 모드 활성화 시 호출"""
    if not hasattr(app_instance, 'video_frame_module'):
        app_instance.video_frame_module = create_video_frame_module(app_instance)
    
    if app_instance.video_frame_module:
        app_instance.video_frame_module.show_video_frame()


def on_video_mode_deactivated(app_instance):
    """비디오 모드 비활성화 시 호출"""
    if hasattr(app_instance, 'video_frame_module') and app_instance.video_frame_module:
        app_instance.video_frame_module.hide_video_frame()


def load_video_from_module(app_instance, video_path):
    """비디오 프리뷰 모듈의 load_video 함수 호출 (이미지의 load_image와 동일한 역할)"""
    print(f"🔄 [DEBUG] load_video_from_module 호출됨: {video_path}")
    
    # 비디오 프리뷰 모듈이 없으면 생성
    if not hasattr(app_instance, 'video_frame_module') or not app_instance.video_frame_module:
        print("🔄 [DEBUG] 비디오 프리뷰 모듈이 없음 - 생성 중")
        app_instance.video_frame_module = create_video_frame_module(app_instance)
    
    # 비디오 프리뷰 모듈이 있지만 프리뷰 카드가 없는 경우 초기화
    if app_instance.video_frame_module and not app_instance.video_frame_module.video_preview_card:
        print("🔄 [DEBUG] 비디오 프리뷰 카드가 없음 - 초기화 중")
        app_instance.video_frame_module.initialize()
    
    # 현재 비디오 저장 (같은 비디오를 재선택해도 다시 로드)
    app_instance.current_video = video_path
    
    # 비디오 프리뷰 모듈 표시 확인 및 표시
    if app_instance.video_frame_module:
        # 비디오 모드인지 확인
        is_video_mode = False
        if hasattr(app_instance, 'video_filter_btn') and app_instance.video_filter_btn:
            is_video_mode = app_instance.video_filter_btn.isChecked()
        
        # 비디오 모드일 때만 비디오 프레임 표시
        if is_video_mode:
            # 오버레이가 표시되어 있는지 확인
            overlay_visible = False
            if app_instance.video_frame_module.overlay_plugin:
                active_type = getattr(app_instance, '_overlay_active_type', None)
                overlay_visible = (active_type == 'video_frame')
            
            if not overlay_visible:
                # 고급 검색 리셋 중에는 자동 표시 건너뛰기
                if getattr(app_instance, '_skip_video_frame_auto_show', False):
                    print("🔄 [DEBUG] 고급 검색 리셋 중 - 비디오 프레임 자동 표시 건너뜀")
                else:
                    print("🔄 [DEBUG] 비디오 프레임이 표시되지 않음 - 자동 표시")
                    app_instance.video_frame_module.show_video_frame()
        
        # 비디오 로드
        if app_instance.video_frame_module.video_preview_card:
            app_instance.video_frame_module.video_preview_card.load_video(video_path)
    
    # 선택된 썸네일 업데이트
    from search_filter_grid_video_module import _refresh_video_grid_selection_visuals
    _refresh_video_grid_selection_visuals(app_instance)
    
    from pathlib import Path
    app_instance.statusBar().showMessage(f"Loaded: {Path(video_path).name}")
    print(f"✅ [DEBUG] load_video_from_module 완료: {Path(video_path).name}")

