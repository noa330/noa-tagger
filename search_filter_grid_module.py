"""
검색/필터 및 이미지 그리드 모듈
왼쪽 패널의 검색, 필터, 이미지 그리드 섹션을 담당
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLayout,
    QLineEdit, QPushButton, QScrollArea, QLabel, QFrame, QComboBox, QCheckBox, QApplication,
    QSpinBox, QDoubleSpinBox, QSizePolicy
)

# 전역 커스텀 클래스 import
try:
    import sys
    main_module = sys.modules.get('__main__')
    if main_module and hasattr(main_module, 'CustomSpinBox'):
        CustomSpinBox = main_module.CustomSpinBox
        CustomDoubleSpinBox = main_module.CustomDoubleSpinBox
        CustomComboBox = main_module.CustomComboBox
    else:
        # 직접 정의 (fallback)
        CustomSpinBox = QSpinBox
        CustomDoubleSpinBox = QDoubleSpinBox
        CustomComboBox = QComboBox
except:
    # 실패 시 기본 클래스 사용
    CustomSpinBox = QSpinBox
    CustomDoubleSpinBox = QDoubleSpinBox
    CustomComboBox = QComboBox
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint, QEvent, QObject, QTimer
from PySide6.QtGui import QPixmap, QColor, QImage, QPainter, QPen, QBrush, QPolygon
from pathlib import Path

# 공통 상수들
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}

# 공통 스타일시트들
COMMON_FILE_DIALOG_STYLE = """
    QFileDialog {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
        color: #F0F2F5;
        border: 1px solid rgba(75,85,99,0.3);
        border-radius: 8px;
    }
    QPushButton {
        background: #3B82F6;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 12px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #2563EB;
    }
    QPushButton:pressed {
        background: #1D4ED8;
    }
"""

COMMON_ADD_BUTTON_STYLE = """
    QPushButton {
        background: transparent;
        color: #CFD8DC;
        border: none;
        border-radius: 6px;
        font-size: 18px;
        font-weight: bold;
    }
    QPushButton:hover {
        background: transparent;
        color: #FFFFFF;
        border: none;
        font-size: 22px;
    }
    QPushButton:pressed {
        background: transparent;
        color: #CFD8DC;
        border: none;
        margin: 0px;
        padding: 0px;
        font-size: 18px;
    }
"""

COMMON_SCROLL_AREA_STYLE = """
    QScrollArea {
        background: transparent;
        border: none;
        border-radius: 8px;
    }
"""

COMMON_CONTAINER_STYLE = """
    QWidget {
        background: transparent;
    }
"""

def load_image_from_module(app_instance, image_path):
    """이미지 프리뷰 모듈의 load_image 함수 호출"""
    print(f"🔄 [DEBUG] load_image_from_module 호출됨: {image_path}")
    from image_preview_module import load_image
    load_image(app_instance, image_path)
    print(f"✅ [DEBUG] load_image_from_module 완료")

# 공통 유틸리티 함수들
def create_common_file_dialog(parent, title, file_filter):
    """공통 파일 선택 대화상자 생성"""
    from PySide6.QtWidgets import QFileDialog
    file_dialog = QFileDialog(parent)
    file_dialog.setFileMode(QFileDialog.ExistingFiles)
    file_dialog.setNameFilter(file_filter)
    file_dialog.setWindowTitle(title)
    file_dialog.setStyleSheet(COMMON_FILE_DIALOG_STYLE)
    return file_dialog

def create_common_add_button(text, tooltip, callback):
    """공통 + 버튼 생성"""
    from PySide6.QtWidgets import QPushButton
    button = QPushButton(text)
    button.setFixedSize(40, 30)
    button.setToolTip(tooltip)
    button.setStyleSheet(COMMON_ADD_BUTTON_STYLE)
    button.clicked.connect(callback)
    return button

def create_common_scroll_area():
    """공통 스크롤 영역 생성"""
    from PySide6.QtWidgets import QScrollArea
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    # 스크롤바 무한 반복 방지: 적절한 여백 추가
    scroll.setViewportMargins(0, 0, 3, 0)
    scroll.setStyleSheet(COMMON_SCROLL_AREA_STYLE)
    return scroll

def create_common_container():
    """공통 컨테이너 위젯 생성"""
    from PySide6.QtWidgets import QWidget
    container = QWidget()
    # 스크롤바 무한 반복 방지: SizePolicy 설정
    container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    container.setStyleSheet(COMMON_CONTAINER_STYLE)
    return container

def create_common_flow_layout(container):
    """공통 플로우 레이아웃 생성"""
    flow_layout = QFlowLayout(container)
    flow_layout.setSpacing(4)
    flow_layout.setContentsMargins(0, 0, 0, 0)
    return flow_layout

def handle_common_thumbnail_click(app_instance, media_path, media_type):
    """공통 썸네일 클릭 처리 (이미지/동영상 통합)"""
    try:
        mods = QApplication.keyboardModifiers()
        shift = bool(mods & Qt.ShiftModifier)
        ctrl = bool(mods & Qt.ControlModifier)

        # 다중 선택 상태 보장
        multi_selected_attr = f'{media_type}_multi_selected'
        if not hasattr(app_instance, multi_selected_attr):
            setattr(app_instance, multi_selected_attr, set())

        multi_selected = getattr(app_instance, multi_selected_attr)
        
        # 현재 선택 미디어 속성명 (공통으로 사용)
        current_attr = f'current_{media_type}'

        if shift and ctrl:
            # Shift+Ctrl: 다중 선택 토글
            was_in = media_path in multi_selected

            # 디폴트: 현재 선택 미디어는 다중선택에 포함된 상태로 간주
            current_media = getattr(app_instance, current_attr, None)
            if current_media is not None and current_media not in multi_selected:
                multi_selected.add(current_media)

            if was_in:
                multi_selected.discard(media_path)
                # 현재 선택 미디어를 다중선택에서 해제한 경우에만 새 현재 선택 결정
                if current_media == media_path:
                    new_current = choose_replacement_current_from_multi(app_instance, media_path, media_type)
                    if new_current:
                        if media_type == 'image':
                            load_image_from_module(app_instance, new_current)
                        else:  # video
                            from video_preview_module import load_video_from_module
                            load_video_from_module(app_instance, new_current)
                    else:
                        # 다중선택이 비었으면 기본 동작: 클릭된 미디어만 단일 선택으로 표시
                        if media_type == 'image':
                            load_image_from_module(app_instance, media_path)
                        else:  # video
                            from video_preview_module import load_video_from_module
                            load_video_from_module(app_instance, media_path)
            else:
                multi_selected.add(media_path)
                # 현재 선택 미디어가 없을 때만 새로운 미디어 로드
                if current_media is None:
                    if media_type == 'image':
                        load_image_from_module(app_instance, media_path)
                    else:  # video
                        from video_preview_module import load_video_from_module
                        load_video_from_module(app_instance, media_path)

            # 레거시 multi_selected 동기화
            if media_type == 'image':
                app_instance.multi_selected = multi_selected.copy()
            
            # 비주얼 갱신 (current_media는 변경하지 않음)
            refresh_grid_selection_visuals(app_instance, media_type)
            return

        # 기본: 단일 선택
        multi_selected.clear()
        
        # 레거시 multi_selected 동기화
        if media_type == 'image':
            app_instance.multi_selected = multi_selected.copy()
        
        if media_type == 'image':
            print(f"🔄 [DEBUG] 이미지 로드 시작: {media_path}")
            load_image_from_module(app_instance, media_path)
            print(f"✅ [DEBUG] 이미지 로드 완료")
        else:  # video
            print(f"🔄 [DEBUG] 비디오 로드 시작: {media_path}")
            from video_preview_module import load_video_from_module
            load_video_from_module(app_instance, media_path)
            setattr(app_instance, current_attr, media_path)
            print(f"✅ [DEBUG] 비디오 로드 완료")
        
        print(f"🔄 [DEBUG] refresh_grid_selection_visuals 호출")
        refresh_grid_selection_visuals(app_instance, media_type)
        print(f"✅ [DEBUG] refresh_grid_selection_visuals 완료")
    except Exception as e:
        print(f"{media_type} 썸네일 클릭 처리 오류: {e}")

def choose_replacement_current_from_multi(app_instance, reference_path, media_type):
    """현재 선택 해제 시 다중선택 내에서 아래 우선, 없으면 위에서 선택"""
    try:
        list_attr = f'{media_type}_list'
        grid_order = getattr(app_instance, list_attr, [])
        if not grid_order:
            return None
        idx_map = {p: i for i, p in enumerate(grid_order)}
        ref_idx = idx_map.get(reference_path, -1)
        if ref_idx == -1:
            return None

        # 다중선택 후보를 그리드 순서로 정렬
        multi_selected_attr = f'{media_type}_multi_selected'
        multi_selected = getattr(app_instance, multi_selected_attr, set())
        candidates = [p for p in multi_selected if p in idx_map]
        if not candidates:
            return None
        candidates.sort(key=lambda p: idx_map[p])

        # 아래(인덱스 큰 것) 우선
        below = [p for p in candidates if idx_map[p] > ref_idx]
        if below:
            return below[0]
        # 없으면 위(인덱스 작은 것)에서 마지막
        above = [p for p in candidates if idx_map[p] < ref_idx]
        if above:
            return above[-1]
        return None
    except Exception:
        return None

def refresh_grid_selection_visuals(app_instance, media_type):
    """그리드의 현재/다중 선택 테두리 일괄 갱신"""
    try:
        current_attr = f'current_{media_type}'
        multi_selected_attr = f'{media_type}_multi_selected'
        flow_layout_attr = f'{media_type}_flow_layout'
        
        current = getattr(app_instance, current_attr, None)
        multi = getattr(app_instance, multi_selected_attr, set())
        flow_layout = getattr(app_instance, flow_layout_attr, None)
        
        if not flow_layout:
            return
            
        for i in range(flow_layout.count()):
            item = flow_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ImageThumbnail):
                    # 현재 선택된 미디어는 항상 파란색 테두리 유지
                    widget.is_current = (widget.image_path == current)
                    # 다중선택된 미디어들은 초록색 테두리 (현재 선택 미디어 제외)
                    widget.is_multi = (widget.image_path in multi) and (widget.image_path != current)
                    widget.update_selection()
    except Exception:
        pass

def clear_media_grid(app_instance, media_type):
    """미디어 그리드 초기화 (이미지/동영상 통합)"""
    flow_layout_attr = f'{media_type}_flow_layout'
    if hasattr(app_instance, flow_layout_attr) and getattr(app_instance, flow_layout_attr):
        flow_layout = getattr(app_instance, flow_layout_attr)
        while flow_layout.count():
            child = flow_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    # 태그 스타일시트 에디터 초기화 (이미지만)
    if media_type == 'image':
        if hasattr(app_instance, 'tag_stylesheet_editor') and app_instance.tag_stylesheet_editor:
            app_instance.tag_stylesheet_editor.reset_editor()
    
    list_attr = f'{media_type}_list'
    if hasattr(app_instance, list_attr):
        setattr(app_instance, list_attr, [])
    
    # 태깅 패널 초기화 (이미지만)
    if media_type == 'image':
        try:
            from image_tagging_module import clear_tagging_panel
            clear_tagging_panel(app_instance)
        except ImportError:
            pass

def add_media_files_to_current(app_instance, media_type, file_filter, window_title):
    """미디어 파일 추가 (이미지/동영상 통합)"""
    from PySide6.QtWidgets import QFileDialog
    from pathlib import Path
    
    # 파일 선택 대화상자
    file_dialog = create_common_file_dialog(app_instance, window_title, file_filter)
    
    if file_dialog.exec() == QFileDialog.Accepted:
        selected_files = file_dialog.selectedFiles()
        if selected_files:
            # 지원하는 미디어 확장자
            extensions = IMAGE_EXTENSIONS if media_type == 'image' else VIDEO_EXTENSIONS
            
            # 새로 추가할 파일들 필터링
            new_files = []
            for file_path in selected_files:
                path_obj = Path(file_path)
                if path_obj.suffix.lower() in extensions:
                    new_files.append(path_obj)
            
            if new_files:
                # 기존 미디어 목록에 추가
                files_attr = f'{media_type}_files'
                original_files_attr = f'original_{media_type}_files'
                
                if not hasattr(app_instance, files_attr):
                    setattr(app_instance, files_attr, [])
                if not hasattr(app_instance, original_files_attr):
                    setattr(app_instance, original_files_attr, [])
                
                # 중복 제거하면서 추가
                existing_files = getattr(app_instance, files_attr)
                original_files = getattr(app_instance, original_files_attr)
                existing_paths = {str(path) for path in existing_files}
                actually_added = []
                
                for new_file in new_files:
                    if str(new_file) not in existing_paths:
                        existing_files.append(new_file)
                        original_files.append(new_file)
                        actually_added.append(new_file)
                
                # 실제로 추가된 파일이 있을 때만 썸네일 새로고침
                if actually_added:
                    if media_type == 'image':
                        from search_filter_grid_image_module import refresh_image_thumbnails_immediate
                        refresh_image_thumbnails_immediate(app_instance)
                    else:  # video
                        from search_filter_grid_video_module import refresh_video_thumbnails
                        refresh_video_thumbnails(app_instance)
                    
                    # 카운터 업데이트
                    if media_type == 'image':
                        from search_module import update_image_counter
                        update_image_counter(app_instance, len(existing_files), len(existing_files))
                    else:  # video
                        from search_filter_grid_video_module import update_video_counter
                        update_video_counter(app_instance, len(existing_files), len(existing_files))
                    
                    app_instance.statusBar().showMessage(f"{media_type} {len(actually_added)}개가 추가되었습니다.")
                else:
                    app_instance.statusBar().showMessage(f"이미 존재하는 {media_type}들입니다.")
            else:
                app_instance.statusBar().showMessage(f"선택된 {media_type}가 없습니다.")

# 하위 호환성을 위한 레거시 함수들
def get_multi_selected_images(app_instance):
    """이미지 다중선택 항목들을 반환 (하위 호환성)"""
    if hasattr(app_instance, 'image_multi_selected'):
        return list(app_instance.image_multi_selected)
    elif hasattr(app_instance, 'multi_selected'):
        return list(app_instance.multi_selected)
    return []

def get_multi_selected_videos(app_instance):
    """동영상 다중선택 항목들을 반환 (하위 호환성)"""
    if hasattr(app_instance, 'video_multi_selected'):
        return list(app_instance.video_multi_selected)
    return []

def get_all_multi_selected(app_instance):
    """모든 다중선택 항목들을 반환 (하위 호환성)"""
    all_selected = set()
    
    # 이미지 다중선택
    if hasattr(app_instance, 'image_multi_selected'):
        all_selected.update(app_instance.image_multi_selected)
    elif hasattr(app_instance, 'multi_selected'):
        all_selected.update(app_instance.multi_selected)
    
    # 동영상 다중선택
    if hasattr(app_instance, 'video_multi_selected'):
        all_selected.update(app_instance.video_multi_selected)
    
    return list(all_selected)

def sync_legacy_multi_selected(app_instance):
    """레거시 multi_selected와 새로운 변수들을 동기화"""
    # 이미지 다중선택을 레거시 변수에 동기화
    if hasattr(app_instance, 'image_multi_selected'):
        app_instance.multi_selected = app_instance.image_multi_selected.copy()
    elif not hasattr(app_instance, 'multi_selected'):
        app_instance.multi_selected = set()
    
    # 동영상 다중선택이 있으면 이미지와 합치기
    if hasattr(app_instance, 'video_multi_selected'):
        app_instance.multi_selected.update(app_instance.video_multi_selected)

class ImageThumbnail(QFrame):
    clicked = Signal(str)
    
    def __init__(self, image_path, image_name):
        super().__init__()
        self.image_path = image_path
        self.image_name = image_name
        self.selected = False
        self.is_current = False
        self.is_multi = False
        # ✅ 원본 캐시
        self._orig_pixmap = None
        self._has_placeholder = False
        # ✅ 마지막 스케일 기준 기억
        self._last_scaled_width = 0
        self._last_columns = None  # ✅ 변경: 마지막 열수 기록
        # ✅ 비디오 파일 여부 확인
        self._is_video = self._check_is_video()
        # ✅ 호버 상태
        self._is_hovered = False
        # 토큰 경고 상태
        self._token_warning = False
        self.setup_ui()
        
    def setup_ui(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("ImageThumb")
        
        # 메인 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)  # 테두리를 위한 여백 증가
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # 이미지 레이블 (컨테이너 없이 직접 사용)
        self.thumb_label = QLabel()
        self.thumb_label.setScaledContents(False)
        self.thumb_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.thumb_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
        """)
        
        # Load actual image once
        self._load_original()
        self.load_thumbnail()  # 초기 표시
        
        # Name
        self.name_label = QLabel(self.image_name[:12] + "..." if len(self.image_name) > 12 else self.image_name)
        self.name_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 10px;
            font-weight: 500;
            background: transparent;
        """)
        self.name_label.setAlignment(Qt.AlignLeft)
        
        layout.addWidget(self.thumb_label)
        layout.addWidget(self.name_label)
        
        self.update_selection()

    # ✅ 레이아웃이 실제 크기를 정확히 알 수 있도록 sizeHint 제공
    def sizeHint(self) -> QSize:
        w = self.thumb_label.width() + 8
        h = self.thumb_label.height() + 34
        # 초기 단계에서 0이 나올 수 있으므로 안전 하한
        return QSize(max(w, 60), max(h, 60))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _load_original(self):
        """원본 이미지/비디오를 1회만 로드하여 캐시"""
        try:
            # 파일 확장자 확인
            file_extension = Path(self.image_path).suffix.lower()
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            
            if file_extension in video_extensions:
                # 비디오 파일의 경우 첫 번째 프레임 추출
                pm = self._extract_video_thumbnail()
            else:
                # 이미지 파일의 경우 일반 로드
                pm = QPixmap(self.image_path)
            
            if not pm.isNull():
                self._orig_pixmap = pm
                self._has_placeholder = False
            else:
                self._make_placeholder(280)  # 초기 폭 임시값
        except Exception:
            self._make_placeholder(280)

    def _extract_video_thumbnail(self):
        """비디오 파일에서 첫 번째 프레임을 추출하여 썸네일 생성"""
        try:
            # OpenCV를 사용한 비디오 프레임 추출
            import cv2
            
            # 비디오 파일 열기
            cap = cv2.VideoCapture(self.image_path)
            if not cap.isOpened():
                return QPixmap()
            
            # 첫 번째 프레임 읽기
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                return QPixmap()
            
            # OpenCV BGR을 RGB로 변환
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame_rgb.shape
            bytes_per_line = 3 * width
            
            # QImage로 변환
            q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # QPixmap으로 변환
            pixmap = QPixmap.fromImage(q_image)
            
            # 리사이징 전에는 재생 버튼을 추가하지 않음 (리사이징 후에 추가)
            return pixmap
            
        except ImportError:
            # OpenCV가 없는 경우 비디오 아이콘 표시
            return self._make_video_placeholder()
        except Exception as e:
            print(f"비디오 썸네일 추출 오류: {e}")
            return self._make_video_placeholder()
    
    def _make_video_placeholder(self):
        """비디오 파일용 플레이스홀더 생성"""
        ph_w = 120
        ph_h = int(ph_w * 0.75)  # 4:3 비율
        placeholder = QPixmap(ph_w, ph_h)
        placeholder.fill(QColor("#1F2937"))
        
        # 비디오 아이콘 그리기 (간단한 삼각형)
        painter = QPainter(placeholder)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#6B7280"), 2))
        painter.setBrush(QBrush(QColor("#6B7280")))
        
        # 삼각형 (재생 버튼 모양)
        triangle = QPolygon([
            QPoint(ph_w//2 - 15, ph_h//2 - 10),
            QPoint(ph_w//2 - 15, ph_h//2 + 10),
            QPoint(ph_w//2 + 15, ph_h//2)
        ])
        painter.drawPolygon(triangle)
        painter.end()
        
        return placeholder
    
    def _add_play_button_overlay(self, pixmap, hover=False):
        """비디오 썸네일에 재생 버튼 오버레이 추가"""
        if pixmap.isNull():
            return pixmap
            
        # 오버레이용 QPixmap 생성
        overlay = QPixmap(pixmap.size())
        overlay.fill(Qt.transparent)
        
        painter = QPainter(overlay)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 반투명 배경 원
        center_x = pixmap.width() // 2
        center_y = pixmap.height() // 2
        
        # 고정된 버튼 크기 (동영상 크기에 관계없이 일정한 크기)
        radius = 24  # 고정 크기 (12 * 2)
        alpha_bg = 160  # 반투명 배경
        alpha_triangle = 255  # 흰색 삼각형
        
        # 테두리 없이 원만 그리기
        painter.setPen(Qt.NoPen)  # 테두리 제거
        painter.setBrush(QBrush(QColor(0, 0, 0, alpha_bg)))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # 재생 버튼 삼각형 (테두리 없이 채우기만)
        triangle_size = radius * 0.6
        painter.setPen(Qt.NoPen)  # 테두리 제거 (작은 동그라미 방지)
        painter.setBrush(QBrush(QColor(255, 255, 255, alpha_triangle)))
        
        triangle = QPolygon([
            QPoint(center_x - triangle_size//2, center_y - triangle_size//2),
            QPoint(center_x - triangle_size//2, center_y + triangle_size//2),
            QPoint(center_x + triangle_size//2, center_y)
        ])
        painter.drawPolygon(triangle)
        painter.end()
        
        # 원본 이미지에 오버레이 합성
        result = QPixmap(pixmap)
        result_painter = QPainter(result)
        result_painter.drawPixmap(0, 0, overlay)
        result_painter.end()
        
        return result
    
    def _check_is_video(self):
        """파일이 비디오인지 확인"""
        try:
            file_extension = Path(self.image_path).suffix.lower()
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            return file_extension in video_extensions
        except Exception:
            return False
    
    def enterEvent(self, event):
        """마우스 진입 이벤트"""
        if self._is_video:
            self._is_hovered = True
            self._update_video_thumbnail_with_hover()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """마우스 벗어남 이벤트"""
        if self._is_video:
            self._is_hovered = False
            self._update_video_thumbnail_with_hover()
        super().leaveEvent(event)
    
    def _update_video_thumbnail_with_hover(self):
        """호버 상태에 따른 비디오 썸네일 업데이트"""
        if not self._is_video or self._orig_pixmap is None:
            return
        
        try:
            # 현재 표시된 크기에 맞춰 먼저 스케일링
            if hasattr(self, 'thumb_label') and self.thumb_label:
                current_size = self.thumb_label.size()
                if current_size.width() > 0 and current_size.height() > 0:
                    # 원본 픽스맵을 먼저 스케일링 (재생 버튼 없이)
                    scaled_pixmap = self._orig_pixmap.scaled(current_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    # 스케일링된 픽스맵에 재생 버튼 오버레이 추가
                    final_pixmap = self._add_play_button_overlay(scaled_pixmap, hover=False)
                    self.thumb_label.setPixmap(final_pixmap)
        except Exception as e:
            print(f"비디오 썸네일 호버 업데이트 오류: {e}")

    def _make_placeholder(self, width):
        ph_w = max(width - 8, 50)
        placeholder = QPixmap(ph_w, int(ph_w * 0.75))  # 4:3 비율
        placeholder.fill(QColor("#1F2937"))
        self._orig_pixmap = placeholder
        self._has_placeholder = True
    
    def load_thumbnail(self, available_width=280, smooth=True, force=False, columns=1, spacing=4):
        """
        실제 이미지 썸네일 로드/업데이트 - 패널 폭에 '꽉 차게' 맞춰 크기 조정
        smooth=True  -> Qt.SmoothTransformation (최종)
        smooth=False -> Qt.FastTransformation   (드래그 중 미리보기)
        force=True   -> 임계값 무시하고 강제 스케일
        columns      -> 1(풀폭) / 2(두 칼럼)
        spacing      -> 항목 간 간격(px). FlowLayout의 spacing과 동일하게 전달
        """
        try:
            if self._orig_pixmap is None:
                self._load_original()

            # ✅ 열 수에 따른 목표 아이템 폭 계산
            # 아이템 총 폭 = 이미지 폭 + 8 (프레임 여백 더함)
            if columns >= 2:
                # 2열일 때는 spacing을 2번 고려: ((available_width - spacing*2) / 2)
                item_width_target = int((available_width - spacing * 2) / 2)
                max_img_width = max(item_width_target - 8, 100)  # 이미지 폭 (아이템폭 - 프레임여백)
            else:
                # 1열일 때는 왼쪽 spacing 1번을 고려: (available_width - spacing)
                item_width_target = max(available_width - spacing, 60)  # 1열 예산(이미지+프레임 전)
                max_img_width = max(item_width_target - 8, 50)          # 프레임(8px) 반영

            # ✅ 폭 변화가 작으면 스킵 (디폴트 8px 기준은 이미지 폭 기준)
            if not force and abs(max_img_width - self._last_scaled_width) < 8:
                return

            transform_mode = Qt.SmoothTransformation if smooth else Qt.FastTransformation
            scaled_pixmap = self._orig_pixmap.scaledToWidth(max_img_width, transform_mode)
            
            # 비디오인 경우 재생 버튼 오버레이 추가
            # 1) 먼저 스케일 완료
            final_pixmap = scaled_pixmap
            # 2) 비디오면 재생 오버레이 합성
            if self._is_video:
                final_pixmap = self._add_play_button_overlay(final_pixmap, hover=False)
            # 3) 토큰 경고면 경고 오버레이를 '마지막'에 합성 (왜곡 방지)
            if getattr(self, "_token_warning", False):
                final_pixmap = self._add_warning_overlay(final_pixmap)
            # 4) 표시
            self.thumb_label.setPixmap(final_pixmap)

            # 썸네일 크기에 맞춰 위젯 크기 조정 (테두리 여백 포함)
            self.thumb_label.setFixedSize(scaled_pixmap.size())
            self.setFixedSize(scaled_pixmap.width() + 8, scaled_pixmap.height() + 34)  # 테두리(4px) + 여백(4px) + 이름 라벨(30px)

            self._last_scaled_width = max_img_width
            self._last_columns = columns  # ✅ 변경: 마지막 열수 업데이트
        except Exception:
            # 오류 발생 시 플레이스홀더
            self._make_placeholder(available_width)
            if columns >= 2:
                item_width_target = int((available_width - spacing * 2) / 2)
                max_img_width = max(item_width_target - 8, 100)
            else:
                item_width_target = max(available_width - spacing, 60)
                max_img_width = max(item_width_target - 8, 50)
            scaled_pixmap = self._orig_pixmap.scaledToWidth(max_img_width, Qt.FastTransformation if not smooth else Qt.SmoothTransformation)
            
            # 비디오인 경우 재생 버튼 오버레이 추가
            final_pixmap = scaled_pixmap
            if self._is_video:
                final_pixmap = self._add_play_button_overlay(final_pixmap, hover=False)
            if getattr(self, "_token_warning", False):
                final_pixmap = self._add_warning_overlay(final_pixmap)
            self.thumb_label.setPixmap(final_pixmap)
            self.thumb_label.setFixedSize(scaled_pixmap.size())
            self.setFixedSize(scaled_pixmap.width() + 8, scaled_pixmap.height() + 34)
            self._last_scaled_width = max_img_width
            self._last_columns = columns  # ✅ 변경: 예외에서도 기록
    
    def update_selection(self):
        # 우선순위: 현재 선택(파란색) > 다중선택(초록색) > 기본
        if self.is_current:
            self.setStyleSheet("""
                QFrame#ImageThumb {
                    background: transparent;
                    border: 2px solid #3B82F6;
                    border-radius: 4px;
                }
            """)
        elif self.is_multi:
            self.setStyleSheet("""
                QFrame#ImageThumb {
                    background: transparent;
                    border: 2px solid #10B981;
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#ImageThumb {
                    background: transparent;
                    border: 2px solid transparent;
                }
            """)
        self.thumb_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
        """)
        # 항상 원본에서 재합성하여 이전 오버레이 잔상 제거
        try:
            base = self._compose_base_pixmap()
            if base is not None and not base.isNull():
                final_pm = base
                if self._token_warning:
                    final_pm = self._add_warning_overlay(final_pm)
                self.thumb_label.setPixmap(final_pm)
        except Exception:
            pass

    def _add_warning_overlay(self, pixmap):
        if pixmap.isNull():
            return pixmap
        overlay = QPixmap(pixmap.size())
        overlay.fill(Qt.transparent)
        p = QPainter(overlay)
        p.setRenderHint(QPainter.Antialiasing)
        cx = pixmap.width() // 2
        cy = pixmap.height() // 2
        # 비디오 재생 아이콘과 동일한 고정 반경/투명도 사용으로 일관성 유지
        radius = 24
        alpha_bg = 170
        # 배경 원
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 183, 77, alpha_bg)))  # 주황 반투명
        p.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
        # 느낌표(막대 + 점)
        p.setPen(QPen(QColor(30, 30, 30, 255), 3))
        bar_top = QPoint(cx, cy - int(radius * 0.5))
        bar_bottom = QPoint(cx, cy + int(radius * 0.25))
        p.drawLine(bar_top, bar_bottom)
        p.drawPoint(QPoint(cx, cy + int(radius * 0.55)))
        p.end()
        result = QPixmap(pixmap)
        rp = QPainter(result)
        rp.drawPixmap(0, 0, overlay)
        rp.end()
        return result

    def _compose_base_pixmap(self):
        """현재 크기에 맞춰 원본에서 다시 스케일하고, 비디오이면 재생버튼 오버레이 포함."""
        try:
            if self._orig_pixmap is None:
                return None
            # 현재 표시 크기 추정: label 또는 sizeHint
            target_size = self.thumb_label.size() if hasattr(self, 'thumb_label') else QSize(self.width(), self.height())
            if target_size.width() <= 0 or target_size.height() <= 0:
                # fallback: 최근 스케일 폭 기반
                return self._orig_pixmap
            scaled = self._orig_pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if self._is_video:
                return self._add_play_button_overlay(scaled, hover=False)
            return scaled
        except Exception:
            return self._orig_pixmap
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.image_path)
            # selected 플래그는 전역 상태 기반으로 스타일이 갱신되므로 여기서 직접 건드리지 않음


class ResizeWatcher(QObject):
    """스크롤 뷰포트 리사이즈 감지용 이벤트 필터 (디바운스/스로틀)"""
    def __init__(self, on_resize_callback):
        super().__init__()
        self._cb = on_resize_callback
        # ✅ 드래그 중 스로틀 타이머(빠른 미리보기)
        self._throttle_timer = QTimer()
        self._throttle_timer.setSingleShot(True)
        self._throttle_interval_ms = 80  # 드래그 중 최대 12.5fps
        self._throttle_timer.timeout.connect(self._on_throttle_timeout)
        # ✅ 멈춘 후 최종 디바운스
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_interval_ms = 160
        self._debounce_timer.timeout.connect(self._on_debounce_timeout)

    def _on_throttle_timeout(self):
        if callable(self._cb):
            self._cb(preview=True)

    def _on_debounce_timeout(self):
        if callable(self._cb):
            self._cb(preview=False)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            # 스로틀: 아직 동작 중이 아니면 시작
            if not self._throttle_timer.isActive():
                self._throttle_timer.start(self._throttle_interval_ms)
            # 디바운스: 항상 재시작
            self._debounce_timer.start(self._debounce_interval_ms)
        return False


def create_filter_widget(app_instance):
    """필터 위젯 생성"""
    # Filter dropdown (기본값: 이미지 모드 옵션)
    app_instance.filter_dropdown = CustomComboBox()
    app_instance.filter_dropdown.addItems(["전체 이미지", "태깅 이미지", "노태깅 이미지"])
    app_instance.filter_dropdown.setCurrentIndex(0)  # 기본값: 전체 이미지
    
    # 드롭박스 스타일 (face_align_module.py에서 복사)
    app_instance.filter_dropdown.setStyleSheet("""
        QComboBox {
            background: rgba(26,27,38,0.8);
            border: 1px solid rgba(75,85,99,0.3);
            color: white;
            font-family: 'Segoe UI';
            font-size: 12px;
            min-width: 0px;
        }
        QComboBox:hover {
            background: rgba(26,27,38,0.85);
            border: 1px solid rgba(75,85,99,0.5);
        }
        QComboBox::drop-down {
            border: none;
            width: 0px;
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
            border: 1px solid rgba(75,85,99,0.3);
            border-radius: 4px;
            color: white;
            selection-background-color: #3B82F6;
        }
        QComboBox:focus {
            border: 2px solid #3B82F6;
        }
    """)
    
    # 이벤트 연결
    app_instance.filter_dropdown.currentTextChanged.connect(lambda text: on_filter_dropdown_changed(app_instance, text))
    
    return app_instance.filter_dropdown

def update_filter_dropdown_for_mode(app_instance):
    """미디어 모드에 따라 필터 드롭다운 옵션 업데이트"""
    # 미디어 필터 상태 확인
    is_video_mode = False
    if hasattr(app_instance, 'image_filter_btn') and hasattr(app_instance, 'video_filter_btn'):
        is_video_mode = app_instance.video_filter_btn.isChecked() and not app_instance.image_filter_btn.isChecked()
    
    # 필터 드롭다운 옵션 업데이트
    if hasattr(app_instance, 'filter_dropdown') and app_instance.filter_dropdown:
        current_filter_text = app_instance.filter_dropdown.currentText()
        
        if is_video_mode:
            # 비디오 모드: "전체 비디오"만 표시 (태깅 기능 없음)
            video_filter_options = ["전체 비디오"]
            app_instance.filter_dropdown.clear()
            app_instance.filter_dropdown.addItems(video_filter_options)
            app_instance.filter_dropdown.setCurrentText("전체 비디오")
        else:
            # 이미지 모드: 모든 옵션 표시
            image_filter_options = ["전체 이미지", "태깅 이미지", "노태깅 이미지"]
            app_instance.filter_dropdown.clear()
            app_instance.filter_dropdown.addItems(image_filter_options)
            
            # 현재 선택된 옵션이 이미지 모드에 없으면 "전체 이미지"로 설정
            if current_filter_text not in image_filter_options:
                app_instance.filter_dropdown.setCurrentText("전체 이미지")
            else:
                app_instance.filter_dropdown.setCurrentText(current_filter_text)
        
        print(f"필터 드롭다운 업데이트: {'비디오' if is_video_mode else '이미지'} 모드")

def create_image_grid_section(app_instance, SectionCard):
    """이미지 그리드 섹션 생성 - 하위 모듈 위임"""
    from search_filter_grid_image_module import create_image_grid_section as create_image_grid
    return create_image_grid(app_instance, SectionCard)


# 이미지 관련 함수들은 search_filter_grid_image_module.py로 이동됨


# 이미지 썸네일 생성 함수들은 search_filter_grid_image_module.py로 이동됨
# 첫 번째 이미지 선택 후 선택 상태 강제 업데이트는 이미지 모듈에서 처리됨


# 이미지 썸네일 새로고침 함수들은 search_filter_grid_image_module.py로 이동됨


# 썸네일 비동기 생성 함수들은 search_filter_grid_image_module.py로 이동됨


def create_thumbnail_batch(app_instance, filtered_images, job_token=None):
    """배치 썸네일 생성 (UI 블로킹 방지)"""
    # ✅ 오래된 작업이면 즉시 중단
    if job_token is not None and job_token != getattr(app_instance, '_thumb_active_token', None):
        print(f"⏭️ 오래된 배치 무시: {job_token} != {getattr(app_instance, '_thumb_active_token', None)}")
        return
    
    # 레이아웃이 존재하는지 확인
    if not hasattr(app_instance, 'image_flow_layout') or not app_instance.image_flow_layout:
        print("이미지 레이아웃이 없음 - 썸네일 생성 중단")
        return

    # 스크롤 영역의 실제 폭 계산
    available_width = get_available_width(app_instance)
    print(f"배치 썸네일 생성 - 사용 가능한 폭: {available_width}")
    columns, spacing = get_columns_and_spacing(app_instance, available_width)
    
    # 한 번에 처리할 썸네일 수 (UI 반응성 유지)
    batch_size = 10
    start_idx = getattr(app_instance, 'thumbnail_batch_start', 0)
    end_idx = min(start_idx + batch_size, len(filtered_images))
    
    # 현재 배치의 썸네일 생성
    for i in range(start_idx, end_idx):
        # ✅ 진행 중 토큰 재확인 (중간에 무효화될 수 있음)
        if job_token is not None and job_token != getattr(app_instance, '_thumb_active_token', None):
            print(f"⏭️ 배치 중단(토큰 변경): {job_token} != {getattr(app_instance, '_thumb_active_token', None)}")
            return

        image_path = filtered_images[i]
        thumb = ImageThumbnail(str(image_path), image_path.name)
        thumb.clicked.connect(lambda path=str(image_path): handle_common_thumbnail_click(app_instance, path, 'image'))
        
        # 패널 폭/열수에 맞춰 썸네일 로드 (배치: 매끄럽게)
        thumb.load_thumbnail(available_width, smooth=True, force=True, columns=columns, spacing=spacing)
        
        # 플로우 레이아웃에 추가 (자동 배치) - 안전성 검사 추가
        if hasattr(app_instance, 'image_flow_layout') and app_instance.image_flow_layout:
            try:
                app_instance.image_flow_layout.addWidget(thumb)
            except RuntimeError as e:
                print(f"썸네일 추가 중 오류 (무시): {e}")
                # 레이아웃이 이미 삭제된 경우 썸네일도 삭제
                thumb.deleteLater()
                return
    
    # 다음 배치가 있으면 계속 처리
    if end_idx < len(filtered_images):
        app_instance.thumbnail_batch_start = end_idx
        # ✅ 다음 배치에도 동일 토큰 전달
        QTimer.singleShot(1, lambda: create_thumbnail_batch(app_instance, filtered_images, job_token))
    else:
        # 모든 썸네일 생성 완료
        app_instance.thumbnail_batch_start = 0
        print("썸네일 새로고침 완료")
        
        # 썸네일 생성 완료 후 현재 선택 상태 강제 업데이트
        _refresh_grid_selection_visuals(app_instance)


def get_available_width(app_instance):
    """스크롤 영역의 실제 사용 가능한 폭 계산 - 통합 버전"""
    try:
        scroll_ref = None
        container_ref = None
        
        # 현재 활성 모드에 따라 스크롤 영역 선택
        if hasattr(app_instance, 'video_filter_btn') and hasattr(app_instance, 'image_filter_btn'):
            video_checked = app_instance.video_filter_btn.isChecked()
            image_checked = app_instance.image_filter_btn.isChecked()
            
            if video_checked and not image_checked:
                scroll_ref = getattr(app_instance, 'video_scroll', None)
                container_ref = getattr(app_instance, 'video_container', None)
            else:
                scroll_ref = getattr(app_instance, 'image_scroll', None)
                container_ref = getattr(app_instance, 'image_container', None)
        else:
            scroll_ref = getattr(app_instance, 'image_scroll', None)
            container_ref = getattr(app_instance, 'image_container', None)
        
        if scroll_ref:
            viewport = scroll_ref.viewport()
            if viewport:
                viewport_width = viewport.width()
                available = max(viewport_width, 200)
                print(f"스크롤 뷰포트 폭: {viewport_width} -> 사용 가능한 폭: {available}")
                return available

        if container_ref:
            parent = container_ref.parentWidget()
            if parent:
                pw = parent.width()
                available = max(pw, 200)
                print(f"부모 위젯 폭: {pw} -> 사용 가능한 폭: {available}")
                return available
    except Exception as e:
        print(f"폭 계산 오류: {e}")
    return 280


def get_columns_and_spacing(app_instance, available_width):
    """
    현재 폭에 따른 열 수와 플로우 간격을 반환 - 레퍼런스와 동일한 로직
    - 500px 이상이면 2열, 아니면 1열
    """
    spacing = 4
    try:
        flow_layout = None
        if hasattr(app_instance, 'video_filter_btn') and hasattr(app_instance, 'image_filter_btn'):
            video_checked = app_instance.video_filter_btn.isChecked()
            image_checked = app_instance.image_filter_btn.isChecked()
            
            if video_checked and not image_checked:
                flow_layout = getattr(app_instance, 'video_flow_layout', None)
            else:
                flow_layout = getattr(app_instance, 'image_flow_layout', None)
        else:
            flow_layout = getattr(app_instance, 'image_flow_layout', None)
        
        if flow_layout and hasattr(flow_layout, '_spacing'):
            spacing = flow_layout._spacing
    except Exception:
        spacing = 4
    columns = 2 if available_width >= 500 else 1
    return columns, spacing


def update_image_selection(app_instance, selected_path):
    """선택 상태 갱신 (현재/다중 선택 반영)"""
    _refresh_grid_selection_visuals(app_instance)


# handle_thumbnail_click 함수는 handle_common_thumbnail_click으로 통합됨


def _choose_replacement_current_from_multi(app_instance, reference_path):
    """현재 선택 해제 시 다중선택 내에서 아래 우선, 없으면 위에서 선택"""
    try:
        grid_order = getattr(app_instance, 'image_list', [])
        if not grid_order:
            return None
        idx_map = {p: i for i, p in enumerate(grid_order)}
        ref_idx = idx_map.get(reference_path, -1)
        if ref_idx == -1:
            return None

        # 다중선택 후보를 그리드 순서로 정렬
        candidates = [p for p in app_instance.multi_selected if p in idx_map]
        if not candidates:
            return None
        candidates.sort(key=lambda p: idx_map[p])

        # 아래(인덱스 큰 것) 우선
        below = [p for p in candidates if idx_map[p] > ref_idx]
        if below:
            return below[0]
        # 없으면 위(인덱스 작은 것)에서 마지막
        above = [p for p in candidates if idx_map[p] < ref_idx]
        if above:
            return above[-1]
        return None
    except Exception:
        return None


def _refresh_grid_selection_visuals(app_instance):
    """그리드의 현재/다중 선택 테두리 일괄 갱신"""
    try:
        current = getattr(app_instance, 'current_image', None)
        multi = getattr(app_instance, 'multi_selected', set())
        
        for i in range(app_instance.image_flow_layout.count()):
            item = app_instance.image_flow_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ImageThumbnail):
                    # 현재 선택된 이미지는 항상 파란색 테두리 유지
                    widget.is_current = (widget.image_path == current)
                    # 다중선택된 이미지들은 초록색 테두리 (현재 선택 이미지 제외)
                    widget.is_multi = (widget.image_path in multi) and (widget.image_path != current)
                    widget.update_selection()
    except Exception:
        pass


class QFlowLayout(QLayout):
    """이미지들을 자동으로 배치하는 플로우 레이아웃"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._spacing = 4
        self._viewport_width = 280  # 뷰포트 폭 강제 동기화용
    
    def setSpacing(self, spacing):
        self._spacing = spacing
        self.update()
    
    def setViewportWidth(self, width):
        """뷰포트 폭을 강제 동기화"""
        self._viewport_width = width
        self.update()
    
    def addItem(self, item):
        self._items.append(item)
        self.invalidate()
        self.update()
    
    def count(self):
        return len(self._items)
    
    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            self.update()
            return item
        return None
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        if not self._items:
            return QSize(0, 0)
            
        # 실제 배치된 크기 계산
        margins = self.contentsMargins()
        x = margins.left()
        y = margins.top()
        line_height = 0
        spacing = self._spacing
        max_width = 0

        # 뷰포트 폭으로 강제 동기화
        parent_width = self._viewport_width
        
        # 열 수를 강제로 결정 (500px 기준)
        max_cols = 2 if parent_width >= 500 else 1
        items_per_row = 0
        
        for item in self._items:
            widget = item.widget()
            if widget:
                widget_size = widget.sizeHint()
                space_x = spacing + widget_size.width()
                space_y = spacing + widget_size.height()
                
                # 행당 아이템 개수로 줄바꿈 판단
                if items_per_row >= max_cols and line_height > 0:
                    x = margins.left()
                    y = y + line_height + spacing
                    items_per_row = 0
                    line_height = 0
                
                x = x + space_x
                items_per_row += 1
                line_height = max(line_height, space_y)
                max_width = max(max_width, x - margins.left())
        
        total_height = y + line_height + margins.bottom()
        total_width = max_width + margins.right()
        
        return QSize(total_width, total_height)
    
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect)
    
    def doLayout(self, rect):
        """이미지들을 왼쪽부터 자동으로 배치"""
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        line_height = 0
        spacing = self._spacing
        max_width = 0
        
        # 뷰포트 폭으로 강제 동기화하여 열 수 결정
        viewport_width = self._viewport_width
        max_cols = 2 if viewport_width >= 500 else 1
        items_per_row = 0
        
        for item in self._items:
            widget = item.widget()
            if widget:
                widget_size = item.widget().sizeHint()
                space_x = spacing + widget_size.width()
                space_y = spacing + widget_size.height()
                
                # 행당 아이템 개수로 줄바꿈 판단
                if items_per_row >= max_cols and line_height > 0:
                    x = rect.x() + margins.left()  # 다음 줄 시작
                    y = y + line_height + spacing
                    items_per_row = 0
                    line_height = 0
                
                # 위젯 위치 설정
                item.setGeometry(QRect(QPoint(x, y), widget_size))
                x = x + space_x
                items_per_row += 1
                line_height = max(line_height, space_y)
                max_width = max(max_width, x - rect.x())
        
        # 컨테이너 크기 업데이트 (스크롤을 위해)
        if self.parent():
            container_height = y + line_height + margins.bottom()

            # ✅ 가로는 뷰포트(rect.width())로 고정해 수평 팽창 방지
            container_width = rect.width()

            # 최소 사이즈만 갱신하고 실제 리사이즈는 ScrollArea에 맡김
            cur = self.parent().minimumSize()
            if cur.width() != container_width or cur.height() != container_height:
                self.parent().setMinimumSize(container_width, container_height)

            # (기존) self.parent().resize(container_width, container_height)  ← 제거


def on_panel_resized(app_instance, preview=True):
    """
    패널(스크롤 뷰포트) 리사이즈 시 썸네일들을 가용 폭에 맞춰 재스케일 - 통합 버전
    preview=True  : 빠른 미리보기(빠른 변환), 스로틀된 호출
    preview=False : 최종 고품질(부드러운 변환), 디바운스된 호출
    """
    try:
        available_width = get_available_width(app_instance)
        columns, spacing = get_columns_and_spacing(app_instance, available_width)
        print(f"패널 리사이즈 감지 - 재스케일 가용 폭: {available_width} (columns={columns}, preview={preview})")
        smooth = not preview

        flow_layout = None
        container = None
        
        # 현재 활성 모드에 따라 레이아웃과 컨테이너 선택
        if hasattr(app_instance, 'video_filter_btn') and hasattr(app_instance, 'image_filter_btn'):
            video_checked = app_instance.video_filter_btn.isChecked()
            image_checked = app_instance.image_filter_btn.isChecked()
            
            if video_checked and not image_checked:
                flow_layout = getattr(app_instance, 'video_flow_layout', None)
                container = getattr(app_instance, 'video_container', None)
            else:
                flow_layout = getattr(app_instance, 'image_flow_layout', None)
                container = getattr(app_instance, 'image_container', None)
        else:
            flow_layout = getattr(app_instance, 'image_flow_layout', None)
            container = getattr(app_instance, 'image_container', None)

        if flow_layout:
            flow_layout.setViewportWidth(available_width)

        if flow_layout:
            for i in range(flow_layout.count()):
                item = flow_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, ImageThumbnail):
                        must_force = (getattr(widget, "_last_columns", None) != columns) or (not preview)
                        widget.load_thumbnail(available_width, smooth=smooth, force=must_force, columns=columns, spacing=spacing)

        if not preview and container:
            container.update()
    except Exception as e:
        print(f"리사이즈 재스케일 오류: {e}")

def add_images_to_current(app_instance):
    """현재 이미지 목록에 추가 이미지 로드"""
    from PySide6.QtWidgets import QFileDialog
    from pathlib import Path
    
    # 파일 선택 대화상자
    file_dialog = QFileDialog(app_instance)
    file_dialog.setFileMode(QFileDialog.ExistingFiles)
    file_dialog.setNameFilter("미디어 파일 (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v)")
    file_dialog.setWindowTitle("추가할 파일 선택")
    
    # 스타일 적용
    file_dialog.setStyleSheet("""
        QFileDialog {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
            color: #F0F2F5;
            border: 1px solid rgba(75,85,99,0.3);
            border-radius: 8px;
        }
        QPushButton {
            background: #3B82F6;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #2563EB;
        }
        QPushButton:pressed {
            background: #1D4ED8;
        }
    """)
    
    if file_dialog.exec() == QFileDialog.Accepted:
        selected_files = file_dialog.selectedFiles()
        if selected_files:
            # 지원하는 미디어 확장자
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
            
            # 새로 추가할 파일들을 이미지/동영상으로 분리
            new_images = []
            new_videos = []
            for file_path in selected_files:
                path_obj = Path(file_path)
                if path_obj.suffix.lower() in image_extensions:
                    new_images.append(path_obj)
                elif path_obj.suffix.lower() in video_extensions:
                    new_videos.append(path_obj)
            
            # 이미지 파일 추가
            if new_images:
                if not hasattr(app_instance, 'image_files'):
                    app_instance.image_files = []
                if not hasattr(app_instance, 'original_image_files'):
                    app_instance.original_image_files = []
                
                # 중복 제거하면서 추가
                existing_paths = {str(path) for path in app_instance.image_files}
                for new_image in new_images:
                    if str(new_image) not in existing_paths:
                        app_instance.image_files.append(new_image)
                        app_instance.original_image_files.append(new_image)
                
                # 이미지 썸네일 새로고침
                from search_filter_grid_image_module import refresh_image_thumbnails_immediate
                refresh_image_thumbnails_immediate(app_instance)
                
                # 이미지 카운터 업데이트
                from search_module import update_image_counter
                update_image_counter(app_instance, len(app_instance.image_files), len(app_instance.image_files))
            
            # 동영상 파일 추가
            if new_videos:
                if not hasattr(app_instance, 'video_files'):
                    app_instance.video_files = []
                if not hasattr(app_instance, 'original_video_files'):
                    app_instance.original_video_files = []
                
                # 중복 제거하면서 추가
                existing_paths = {str(path) for path in app_instance.video_files}
                for new_video in new_videos:
                    if str(new_video) not in existing_paths:
                        app_instance.video_files.append(new_video)
                        app_instance.original_video_files.append(new_video)
                
                # 동영상 썸네일 새로고침
                from search_filter_grid_video_module import create_video_thumbnails_async
                create_video_thumbnails_async(app_instance, app_instance.video_files)
                
                # 동영상 카운터 업데이트
                from search_filter_grid_video_module import update_video_counter
                update_video_counter(app_instance, len(app_instance.video_files), len(app_instance.video_files))
                
                total_added = len(new_images) + len(new_videos)
                message = f"미디어 {total_added}개가 추가되었습니다"
                if new_images and new_videos:
                    message += f" (이미지 {len(new_images)}개, 동영상 {len(new_videos)}개)"
                elif new_images:
                    message += f" (이미지 {len(new_images)}개)"
                elif new_videos:
                    message += f" (동영상 {len(new_videos)}개)"
                app_instance.statusBar().showMessage(message)
            else:
                app_instance.statusBar().showMessage("선택된 미디어가 없습니다.")


def on_media_filter_changed(app_instance, media_type, checked):
    """미디어 필터 버튼 변경 처리"""
    print(f"미디어 필터 변경: {media_type} = {checked}")
    
    # 상호 배타적 선택 (하나만 선택 가능)
    if checked:
        if media_type == "image":
            if hasattr(app_instance, 'video_filter_btn') and app_instance.video_filter_btn:
                app_instance.video_filter_btn.setChecked(False)
            # 이미지 그리드로 전환
            switch_to_image_grid(app_instance)
        elif media_type == "video":
            if hasattr(app_instance, 'image_filter_btn') and app_instance.image_filter_btn:
                app_instance.image_filter_btn.setChecked(False)
            # 비디오 그리드로 전환
            switch_to_video_grid(app_instance)
        
        # 필터 드롭다운 업데이트 (모드에 따라 옵션 변경)
        update_filter_dropdown_for_mode(app_instance)


def switch_to_image_grid(app_instance):
    """이미지 그리드로 전환"""
    from search_filter_grid_image_module import switch_to_image_grid as switch_to_image
    switch_to_image(app_instance)


def switch_to_video_grid(app_instance):
    """비디오 그리드로 전환"""
    from search_filter_grid_video_module import switch_to_video_grid as switch_to_video
    switch_to_video(app_instance)


def create_video_grid_in_place(app_instance):
    """기존 이미지 그리드와 동일한 스크롤 영역에 비디오 그리드 생성"""
    try:
        # 기존 이미지 스크롤 영역이 있는지 확인
        if hasattr(app_instance, 'image_scroll') and app_instance.image_scroll:
            # 비디오 컨테이너 생성
            app_instance.video_container = QWidget()
            app_instance.video_container.setStyleSheet("""
                QWidget {
                    background: transparent;
                }
            """)
            
            # 비디오 플로우 레이아웃 생성
            app_instance.video_flow_layout = QFlowLayout(app_instance.video_container)
            app_instance.video_flow_layout.setSpacing(4)
            app_instance.video_flow_layout.setContentsMargins(0, 0, 0, 0)
            
            # 컨테이너에 레이아웃 설정
            app_instance.video_container.setLayout(app_instance.video_flow_layout)
            
            # 비디오 스크롤 영역 설정 (이미지와 동일한 스크롤 사용)
            app_instance.video_scroll = app_instance.image_scroll
            
            # 초기에는 숨김 상태로 설정
            app_instance.video_container.setVisible(False)
            
            # 이미지 컨테이너와 비디오 컨테이너를 같은 부모에 추가
            if hasattr(app_instance, 'image_container') and app_instance.image_container:
                parent_widget = app_instance.image_container.parentWidget()
                if parent_widget:
                    # 비디오 컨테이너를 이미지 컨테이너와 같은 부모에 추가
                    app_instance.video_container.setParent(parent_widget)
                    print("비디오 컨테이너를 이미지 컨테이너와 같은 부모에 추가")
            
            print("비디오 그리드 생성 완료 (이미지 스크롤 영역 재사용)")
        else:
            print("이미지 스크롤 영역을 찾을 수 없습니다.")
    except Exception as e:
        print(f"비디오 그리드 생성 오류: {e}")


def on_filter_dropdown_changed(app_instance, text):
    """필터 드롭박스 변경 처리"""
    print(f"필터 드롭박스 변경: {text}")
    
    # 미디어 모드 확인
    if hasattr(app_instance, 'image_filter_btn') and hasattr(app_instance, 'video_filter_btn'):
        video_checked = app_instance.video_filter_btn.isChecked()
        image_checked = app_instance.image_filter_btn.isChecked()
        
        if video_checked and not image_checked:
            # 비디오 모드: 비디오 그리드 업데이트
            print("비디오 모드 - 비디오 그리드 업데이트")
            from search_filter_grid_video_module import refresh_video_thumbnails
            if hasattr(app_instance, 'video_files') and app_instance.video_files:
                refresh_video_thumbnails(app_instance)
            return
    
    # 이미지 모드: 이미지 모듈의 함수 호출 (페이지네이션 포함)
    from search_filter_grid_image_module import refresh_image_thumbnails_immediate
    refresh_image_thumbnails_immediate(app_instance)



# refresh_image_thumbnails_immediate 함수는 search_filter_grid_image_module.py로 이동됨
# 필터 드롭다운 변경 시 해당 모듈의 함수가 직접 호출됨


# 비디오 그리드 섹션 생성 함수는 search_filter_grid_video_module.py로 이동됨


# 비디오 폭 계산 함수는 search_filter_grid_video_module.py로 이동됨


# 비디오 패널 리사이즈 함수는 search_filter_grid_video_module.py로 이동됨


# 비디오 추가 함수는 search_filter_grid_video_module.py로 이동됨


# 비디오 썸네일 새로고침 함수는 search_filter_grid_video_module.py로 이동됨


# 나머지 모든 비디오 관련 함수들은 search_filter_grid_video_module.py로 이동됨
