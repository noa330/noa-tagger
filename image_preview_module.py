"""
이미지 프리뷰 섹션 모듈
중앙 상단 패널의 이미지 프리뷰와 네비게이션 기능을 담당
"""

from PySide6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from pathlib import Path


class ImagePreviewLabel(QLabel):
    """이미지 프리뷰를 위한 커스텀 QLabel - 자동 스케일링 지원"""
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.current_pixmap = None
        
    def setPixmap(self, pixmap):
        """픽스맵 설정 및 크기에 맞춰 스케일링"""
        self.current_pixmap = pixmap
        self.update_scaled_pixmap()
        
    def update_scaled_pixmap(self):
        """현재 크기에 맞춰 이미지 스케일링"""
        if self.current_pixmap and not self.current_pixmap.isNull():
            current_size = self.size()
            if current_size.width() > 0 and current_size.height() > 0:
                # 현재 크기에 맞춰 비율 유지하며 스케일링
                scaled_pixmap = self.current_pixmap.scaled(
                    current_size, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                super().setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        """크기 변경 시 이미지 재스케일링"""
        super().resizeEvent(event)
        self.update_scaled_pixmap()


def create_image_preview_section(app_instance, SectionCard):
    """이미지 프리뷰 섹션 생성"""
    # 이미지 프리뷰 카드
    preview_card = SectionCard("IMAGE PREVIEW")
    
    # 이미지 프리뷰와 네비게이션 버튼 레이아웃
    preview_layout = QHBoxLayout()
    preview_layout.setSpacing(8)
    
    # Previous button (left side)
    app_instance.btn_prev = QPushButton("〈")
    app_instance.btn_prev.setMinimumSize(50, 40)
    app_instance.btn_prev.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    app_instance.btn_prev.setToolTip("Previous image")
    app_instance.btn_prev.setStyleSheet("""
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
    
    # Next button (right side)
    app_instance.btn_next = QPushButton("〉")
    app_instance.btn_next.setMinimumSize(50, 40)
    app_instance.btn_next.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    app_instance.btn_next.setToolTip("Next image")
    app_instance.btn_next.setStyleSheet("""
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
    
    # Image preview (커스텀 클래스 사용)
    app_instance.image_preview = ImagePreviewLabel(app_instance)
    app_instance.image_preview.setMinimumSize(300, 200)  # 최소 크기 설정
    app_instance.image_preview.setAlignment(Qt.AlignCenter)
    app_instance.image_preview_loaded = False  # 이미지 로드 상태 추적
    app_instance.image_preview_width_fixed = False  # 너비 고정 상태 추적
    app_instance.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 상대사이즈 설정
    app_instance.image_preview.setStyleSheet("""
        QLabel {
            background: rgba(26,27,38,0.8);
            border: 2px dashed rgba(75,85,99,0.3);
            border-radius: 12px;
            color: #9CA3AF;
            font-size: 14px;
        }
    """)
    app_instance.image_preview.setText("Select an image to preview")
    
    # 레이아웃에 위젯 추가
    preview_layout.addWidget(app_instance.btn_prev)
    preview_layout.addWidget(app_instance.image_preview, 1)  # stretch factor 1
    preview_layout.addWidget(app_instance.btn_next)
    
    preview_card.body.addLayout(preview_layout)
    
    # 이벤트 연결
    app_instance.btn_prev.clicked.connect(lambda: previous_image(app_instance))
    app_instance.btn_next.clicked.connect(lambda: next_image(app_instance))
    
    return preview_card


def previous_image(app_instance):
    """이전 이미지로 이동"""
    if not app_instance.image_files:
        return
    
    # 현재 이미지 태그 저장
    save_current_image_tags(app_instance)
    
    # 현재 이미지 인덱스 찾기
    current_index = -1
    if app_instance.current_image:
        for i, img_path in enumerate(app_instance.image_files):
            if str(img_path) == str(app_instance.current_image):
                current_index = i
                break
    
    # 이전 이미지 인덱스 계산
    if current_index > 0:
        new_index = current_index - 1
    else:
        new_index = len(app_instance.image_files) - 1  # 첫 번째에서 마지막으로
    
    # 이미지 선택
    load_image(app_instance, str(app_instance.image_files[new_index]))


def next_image(app_instance):
    """다음 이미지로 이동"""
    if not app_instance.image_files:
        return
    
    # 현재 이미지 태그 저장
    save_current_image_tags(app_instance)
    
    # 현재 이미지 인덱스 찾기
    current_index = -1
    if app_instance.current_image:
        for i, img_path in enumerate(app_instance.image_files):
            if str(img_path) == str(app_instance.current_image):
                current_index = i
                break
    
    # 다음 이미지 인덱스 계산
    if current_index < len(app_instance.image_files) - 1:
        new_index = current_index + 1
    else:
        new_index = 0  # 마지막에서 첫 번째로
    
    # 이미지 선택
    load_image(app_instance, str(app_instance.image_files[new_index]))


def load_image(app_instance, image_path):
    """이미지 로드 및 프리뷰 표시"""
    print(f"🔄 [DEBUG] load_image 호출됨: {image_path}")
    print(f"🔄 [DEBUG] 현재 이미지: {app_instance.current_image}")
    
    # 같은 이미지를 다시 클릭한 경우 아무것도 하지 않음
    if app_instance.current_image == image_path:
        print(f"🔄 [DEBUG] 같은 이미지 재선택, 리턴")
        return
    
    # 현재 이미지의 태그 상태 저장
    if app_instance.current_image:
        save_current_image_tags(app_instance)
    
    app_instance.current_image = image_path
    
    # 기존 태그들 초기화
    app_instance.current_tags.clear()
    app_instance.removed_tags.clear()
    
    # 저장된 태그가 있으면 불러오기
    if image_path in app_instance.all_tags:
        app_instance.current_tags = app_instance.all_tags[image_path].copy()
    
    # 저장된 취소된 태그가 있으면 불러오기
    if not hasattr(app_instance, 'image_removed_tags'):
        app_instance.image_removed_tags = {}
    
    if image_path in app_instance.image_removed_tags:
        app_instance.removed_tags = app_instance.image_removed_tags[image_path].copy()
    
    # 전체 태그 통계 업데이트 (이미지 로드 시)
    app_instance.update_global_tag_stats()
    
    # 이미지 프리뷰 업데이트
    try:
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            # 커스텀 QLabel의 setPixmap 사용 (자동 스케일링)
            app_instance.image_preview.setPixmap(pixmap)
            app_instance.image_preview.setText("")
            app_instance.image_preview_loaded = True
        else:
            app_instance.image_preview.setText("Failed to load image")
            app_instance.image_preview_loaded = False
    except Exception as e:
        app_instance.image_preview.setText(f"Error loading image: {str(e)}")
        app_instance.image_preview_loaded = False
    
    # 선택된 썸네일 업데이트
    update_thumbnail_selection(app_instance, image_path)
    
    # 현재 태그 표시 업데이트
    print(f"🔄 [DEBUG] update_current_tags_display 호출 시작")
    app_instance.update_current_tags_display()
    print(f"✅ [DEBUG] update_current_tags_display 완료")
    
    # 통계 업데이트
    print(f"🔄 [DEBUG] update_tag_stats 호출 시작")
    app_instance.update_tag_stats()
    print(f"✅ [DEBUG] update_tag_stats 완료")
    
    # 태그 트리 업데이트
    print(f"🔄 [DEBUG] update_tag_tree 호출 시작")
    app_instance.update_tag_tree()
    print(f"✅ [DEBUG] update_tag_tree 완료")
    
    app_instance.statusBar().showMessage(f"Loaded: {Path(image_path).name}")
    print(f"✅ [DEBUG] load_image 완료: {Path(image_path).name}")


def save_current_image_tags(app_instance):
    """현재 이미지의 태그 상태 저장"""
    if not app_instance.current_image:
        return
    
    # 현재 태그들을 저장
    app_instance.all_tags[app_instance.current_image] = app_instance.current_tags.copy()
    
    # 제거된 태그들도 저장
    if not hasattr(app_instance, 'image_removed_tags'):
        app_instance.image_removed_tags = {}
    
    app_instance.image_removed_tags[app_instance.current_image] = app_instance.removed_tags.copy()


def update_thumbnail_selection(app_instance, image_path):
    """선택된 썸네일 업데이트 (모듈에서 처리)"""
    from search_filter_grid_image_module import update_image_selection
    update_image_selection(app_instance, image_path)
