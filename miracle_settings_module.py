"""
미라클 설정 모듈 - API 키 관리
"""

import json
import os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class ApiKeyItem(QFrame):
    """API 키 아이템 위젯"""
    key_edited = Signal(str, str)  # old_key, new_key
    key_removed = Signal(str)  # key
    
    def __init__(self, key: str, index: int, parent_module=None):
        super().__init__()
        self.api_key = key
        self.index = index
        self.parent_module = parent_module
        self.setObjectName("ApiKeyItem")
        self.setStyleSheet("""
            QFrame#ApiKeyItem {
                background: transparent;
                border: none;
                margin: 1px 0px;
            }
            QFrame#ApiKeyItem:hover {
                background: rgba(255,255,255,0.05);
            }
        """)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(46)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # API 키 마스킹 표시
        masked_key = key[:10] + "..." + key[-4:] if len(key) > 14 else key
        self.key_label = QLabel(masked_key)
        self.key_label.setWordWrap(False)
        self.key_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.key_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.key_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #FFFFFF;
            background: transparent;
        """)
        
        layout.addWidget(self.key_label)
        
        # Edit button (펜 모양) - 반투명 하얀색 라운드 사각형
        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setFixedSize(30, 30)
        self.edit_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.3);
                color: #374151;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.5);
                color: #1F2937;
            }
        """)
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        
        # Remove button - 반투명 빨간색 라운드 사각형
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(30, 30)
        self.remove_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.3);
                color: #E5E7EB;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 700;
                text-align: center;
                padding: 0px;
                padding-top: -4px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        self.remove_btn.clicked.connect(self.on_remove_clicked)
        
        layout.addWidget(self.edit_btn)
        layout.addWidget(self.remove_btn)
    
    def on_edit_clicked(self):
        """편집 버튼 클릭"""
        dialog = QDialog()
        dialog.setWindowTitle("API 키 수정")
        dialog.setMinimumWidth(500)
        
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #1A1B23, stop:1 #0F1014);
                color: white;
            }
            QLabel {
                color: #F0F2F5;
                font-size: 12px;
                font-family: 'Segoe UI';
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
            QLineEdit {
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 2px solid #3B82F6;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("새로운 API 키를 입력하세요:")
        layout.addWidget(label)
        
        input_field = QLineEdit()
        input_field.setText(self.api_key)
        input_field.setPlaceholderText("AIzaSy...")
        layout.addWidget(input_field)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("수정")
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.Accepted:
            new_key = input_field.text().strip()
            if new_key and new_key != self.api_key:
                self.key_edited.emit(self.api_key, new_key)
    
    def on_remove_clicked(self):
        """삭제 버튼 클릭"""
        self.key_removed.emit(self.api_key)


class MiracleSettingsModule:
    """미라클 설정 관리 모듈"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        # models 폴더에 설정 파일 저장
        self.models_dir = "models"
        self.config_file = os.path.join(self.models_dir, "miracle_settings.json")
        self.api_keys = []
        self.current_key_index = 0  # 현재 사용 중인 API 키 인덱스
        self.selected_model = "gemini-2.5-flash"  # 기본 모델
        
        # models 폴더가 없으면 생성
        try:
            if not os.path.exists(self.models_dir):
                os.makedirs(self.models_dir)
                print(f"미라클 설정: models 폴더 생성 완료")
        except Exception as e:
            print(f"미라클 설정: models 폴더 생성 실패 - {e}")
        
        self.load_config()
    
    def load_config(self):
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_keys = config.get('api_keys', [])
                    self.selected_model = config.get('selected_model', 'gemini-2.5-flash')
                    print(f"미라클 설정 로드: {len(self.api_keys)}개 API 키, 모델: {self.selected_model}")
        except Exception as e:
            print(f"미라클 설정 로드 실패: {e}")
            self.api_keys = []
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            config = {
                'api_keys': self.api_keys,
                'selected_model': self.selected_model
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"미라클 설정 저장: {len(self.api_keys)}개 API 키, 모델: {self.selected_model}")
        except Exception as e:
            print(f"미라클 설정 저장 실패: {e}")
    
    def get_active_api_key(self):
        """활성 API 키 가져오기 (순환 사용) - 매번 파일에서 새로 읽기"""
        # 매번 설정 파일을 새로 로드
        self.load_config()
        if not self.api_keys:
            return None
        
        # 현재 인덱스 범위 체크 (설정 파일이 변경되었을 경우 대비)
        if self.current_key_index >= len(self.api_keys):
            self.current_key_index = 0
        
        # 현재 인덱스의 키 반환
        api_key = self.api_keys[self.current_key_index]
        current_display = self.current_key_index + 1  # 사람이 읽기 쉽게 1부터 시작
        
        print(f"API 키 순환: {current_display}/{len(self.api_keys)}번째 키 사용 - {api_key[:10]}...")
        
        # 다음 인덱스로 이동 (순환)
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        return api_key
    
    def get_next_api_key(self, failed_key=None):
        """다음 API 키 가져오기 (503 에러 등으로 실패 시 호출)"""
        self.load_config()
        if not self.api_keys:
            return None
        
        # 실패한 키가 있으면 그 키를 건너뛰고 다음 키 반환
        if failed_key and failed_key in self.api_keys:
            # 실패한 키의 인덱스 찾기
            failed_index = self.api_keys.index(failed_key)
            # 다음 키로 이동 (순환)
            self.current_key_index = (failed_index + 1) % len(self.api_keys)
            print(f"API 키 전환: 실패한 키 건너뛰고 {self.current_key_index + 1}번째 키 사용")
        
        # 현재 인덱스의 키 반환
        api_key = self.api_keys[self.current_key_index]
        # 다음번을 위해 인덱스 증가
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        return api_key
    
    def reset_key_index(self):
        """API 키 인덱스 초기화"""
        self.current_key_index = 0
    
    def get_selected_model(self):
        """선택된 모델 가져오기"""
        self.load_config()  # 매번 새로 읽기
        return self.selected_model
    
    def set_selected_model(self, model):
        """선택된 모델 설정"""
        self.selected_model = model
        self.save_config()
    
    def open_settings(self):
        """설정 창 열기"""
        # 설정 창 열 때도 최신 설정 로드
        self.load_config()
        
        settings_dialog = QDialog(self.app_instance)
        settings_dialog.setWindowTitle("미라클 설정")
        settings_dialog.setMinimumSize(700, 500)
        
        settings_dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
            }
            QLabel {
                color: #F0F2F5;
                font-size: 12px;
                font-family: 'Segoe UI';
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
            QLineEdit {
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                color: white;
                font-family: 'Segoe UI';
                font-size: 12px;
                padding: 8px;
            }
            QLineEdit:hover {
                background: rgba(26,27,38,0.85);
                border: 1px solid rgba(75,85,99,0.5);
            }
            QLineEdit:focus {
                border: 2px solid #3B82F6;
            }
            QListWidget {
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: rgba(59,130,246,0.2);
            }
            QListWidget::item:selected {
                background: rgba(59,130,246,0.4);
            }
        """)
        
        layout = QVBoxLayout(settings_dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title_label = QLabel("Google AI API")
        title_label.setStyleSheet("""
            font-size: 25px;
            font-weight: 700;
            color: #E2E8F0;
            margin-bottom: 8px;
            font-family: 'Segoe UI';
        """)
        layout.addWidget(title_label)
        
        # 설명
        desc_label = QLabel("여러 개의 API 키를 등록하면 순환 사용됩니다.\n첫 번째 키가 우선 사용됩니다.")
        desc_label.setStyleSheet("color: #9CA3AF; font-size: 11px; margin-top: 8px;")
        layout.addWidget(desc_label)
        
        # 모델 선택 섹션
        model_label = QLabel("Gemini 모델 선택:")
        model_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 6px;
            padding: 6px 0px;
            border-bottom: 1px solid rgba(75,85,99,0.3);
        """)
        layout.addWidget(model_label)
        
        # CustomComboBox 클래스 정의 (메인 파일과 동일한 스타일)
        class CustomComboBox(QComboBox):
            def __init__(self, parent=None):
                super().__init__(parent)
                # 기본 화살표 완전히 제거
                self.setStyleSheet("""
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
                """)
            
            def paintEvent(self, event):
                super().paintEvent(event)
                
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # 올바른 스타일 옵션 생성
                option = QStyleOptionComboBox()
                self.initStyleOption(option)
                
                # 드롭다운 화살표 영역 계산 (수동으로)
                rect = self.rect()
                arrow_width = 20
                arrow_rect = QRect(rect.width() - arrow_width, 0, arrow_width, rect.height())
                
                # 화살표 텍스트 그리기 (배경 없이)
                painter.setPen(QPen(QColor("#E2E8F0")))
                painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                painter.drawText(arrow_rect, Qt.AlignCenter, "▼")
        
        model_combo = CustomComboBox()
        model_combo.addItems([
            "gemini-2.5-flash (빠름, 기본)",
            "gemini-2.5-pro (고품질)",
            "gemini-2.5-flash-lite (경량)",
            "gemini-2.0-flash (2세대 빠름)",
            "gemini-2.0-flash-lite (2세대 경량)"
        ])
        
        # 현재 선택된 모델에 따라 인덱스 설정
        model_mapping = {
            "gemini-2.5-flash": 0,
            "gemini-2.5-pro": 1,
            "gemini-2.5-flash-lite": 2,
            "gemini-2.0-flash": 3,
            "gemini-2.0-flash-lite": 4
        }
        current_index = model_mapping.get(self.selected_model, 0)
        model_combo.setCurrentIndex(current_index)
        
        # CustomComboBox에 기본 스타일 적용 (드롭다운 버튼 완전 제거)
        model_combo.setStyleSheet("""
            QComboBox {
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                color: white;
                font-family: 'Segoe UI';
                font-size: 12px;
                padding: 6px 8px;
                min-width: 200px;
            }
            QComboBox:hover {
                background: rgba(26,27,38,0.85);
                border: 1px solid rgba(75,85,99,0.5);
            }
            QComboBox:focus {
                border: 2px solid #3B82F6;
            }
            QComboBox::drop-down {
                border: none;
                width: 0px;
                background: transparent;
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
                selection-background-color: rgba(59,130,246,0.4);
            }
        """)
        layout.addWidget(model_combo)
        
        # API 키 리스트
        list_label = QLabel("등록된 API 키:")
        list_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 6px;
            padding: 6px 0px;
            border-bottom: 1px solid rgba(75,85,99,0.3);
        """)
        layout.addWidget(list_label)
        
        # API 키 리스트 컨테이너
        api_key_scroll = QScrollArea()
        api_key_scroll.setWidgetResizable(True)
        api_key_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                background: rgba(26,27,38,0.8);
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        # API 키 리스트 위젯
        api_key_widget = QWidget()
        api_key_layout = QVBoxLayout(api_key_widget)
        api_key_layout.setContentsMargins(8, 8, 8, 8)
        api_key_layout.setSpacing(4)
        api_key_layout.setAlignment(Qt.AlignTop)
        
        # API 키 아이템들 추가
        self.api_key_items = []
        for i, key in enumerate(self.api_keys):
            api_item = ApiKeyItem(key, i, self)
            api_item.key_edited.connect(self.edit_api_key)
            api_item.key_removed.connect(self.delete_api_key)
            api_key_layout.addWidget(api_item)
            self.api_key_items.append(api_item)
        
        api_key_scroll.setWidget(api_key_widget)
        layout.addWidget(api_key_scroll)
        
        # 하단 버튼들 (추가 + 닫기)
        bottom_layout = QHBoxLayout()
        
        # 추가 버튼
        add_btn = QPushButton("+ API 키 추가")
        add_btn.clicked.connect(lambda: self.add_api_key(api_key_layout))
        bottom_layout.addWidget(add_btn)
        
        bottom_layout.addStretch()
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.setMinimumWidth(100)
        
        def save_and_close():
            # 모델 선택 저장
            selected_index = model_combo.currentIndex()
            model_mapping = {
                0: "gemini-2.5-flash",
                1: "gemini-2.5-pro", 
                2: "gemini-2.5-flash-lite",
                3: "gemini-2.0-flash",
                4: "gemini-2.0-flash-lite"
            }
            selected_model = model_mapping.get(selected_index, "gemini-2.5-flash")
            self.set_selected_model(selected_model)
            settings_dialog.accept()
        
        close_btn.clicked.connect(save_and_close)
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)
        
        settings_dialog.exec()
    
    def add_api_key(self, api_key_layout):
        """API 키 추가"""
        dialog = QDialog(self.app_instance)
        dialog.setWindowTitle("API 키 추가")
        dialog.setMinimumWidth(500)
        
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
            }
            QLabel {
                color: #F0F2F5;
                font-size: 12px;
                font-family: 'Segoe UI';
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
            QLineEdit {
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 2px solid #3B82F6;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("Google AI API 키를 입력하세요:")
        layout.addWidget(label)
        
        input_field = QLineEdit()
        input_field.setPlaceholderText("AIzaSy...")
        layout.addWidget(input_field)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("추가")
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.Accepted:
            new_key = input_field.text().strip()
            if new_key:
                self.api_keys.append(new_key)
                self.save_config()
                # 새로운 API 키 아이템 추가
                new_index = len(self.api_keys) - 1
                api_item = ApiKeyItem(new_key, new_index, self)
                api_item.key_edited.connect(self.edit_api_key)
                api_item.key_removed.connect(self.delete_api_key)
                api_key_layout.addWidget(api_item)
                self.api_key_items.append(api_item)
                self._show_styled_message("성공", "API 키가 추가되었습니다.", "info")
    
    def edit_api_key(self, old_key, new_key):
        """API 키 수정"""
        if old_key in self.api_keys:
            index = self.api_keys.index(old_key)
            self.api_keys[index] = new_key
            self.save_config()
            
            # UI에서 해당 아이템 업데이트
            if hasattr(self, 'api_key_items') and index < len(self.api_key_items):
                api_item = self.api_key_items[index]
                api_item.api_key = new_key
                # 마스킹된 키 업데이트
                masked_key = new_key[:10] + "..." + new_key[-4:] if len(new_key) > 14 else new_key
                api_item.key_label.setText(masked_key)
                # 상태 정보 업데이트
                status_text = f"API Key #{index + 1} • {len(new_key)} characters"
                api_item.status_label.setText(status_text)
            
            self._show_styled_message("성공", "API 키가 수정되었습니다.", "info")
    
    def delete_api_key(self, key):
        """API 키 삭제"""
        if key in self.api_keys:
            # 삭제할 아이템 찾기
            item_to_remove = None
            for api_item in self.api_key_items:
                if api_item.api_key == key:
                    item_to_remove = api_item
                    break
            
            # 데이터에서 제거
            self.api_keys.remove(key)
            self.save_config()
            
            # UI에서 아이템 제거
            if item_to_remove:
                item_to_remove.setParent(None)
                self.api_key_items.remove(item_to_remove)
                
                # 나머지 아이템들의 인덱스 업데이트
                for i, api_item in enumerate(self.api_key_items):
                    api_item.index = i
                    status_text = f"API Key #{i + 1} • {len(api_item.api_key)} characters"
                    api_item.status_label.setText(status_text)
            
            self._show_styled_message("성공", "API 키가 삭제되었습니다.", "info")
    
    def _show_styled_message(self, title, message, msg_type="info"):
        """스타일이 적용된 메시지 박스 표시"""
        from PySide6.QtWidgets import QMessageBox
        
        msg_box = QMessageBox(self.app_instance)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        # 아이콘 설정
        if msg_type == "info":
            msg_box.setIcon(QMessageBox.Information)
            button_color_start = "#3B82F6"
            button_color_end = "#1D4ED8"
            button_hover_start = "#60A5FA"
            button_hover_end = "#3B82F6"
            button_pressed_start = "#1D4ED8"
            button_pressed_end = "#1E3A8A"
        elif msg_type == "warning":
            msg_box.setIcon(QMessageBox.Warning)
            button_color_start = "#F59E0B"
            button_color_end = "#D97706"
            button_hover_start = "#FBBF24"
            button_hover_end = "#F59E0B"
            button_pressed_start = "#D97706"
            button_pressed_end = "#B45309"
        elif msg_type == "error":
            msg_box.setIcon(QMessageBox.Critical)
            button_color_start = "#EF4444"
            button_color_end = "#DC2626"
            button_hover_start = "#F87171"
            button_hover_end = "#EF4444"
            button_pressed_start = "#DC2626"
            button_pressed_end = "#B91C1C"
        else:
            msg_box.setIcon(QMessageBox.Information)
            button_color_start = "#3B82F6"
            button_color_end = "#1D4ED8"
            button_hover_start = "#60A5FA"
            button_hover_end = "#3B82F6"
            button_pressed_start = "#1D4ED8"
            button_pressed_end = "#1E3A8A"
        
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # 다크 테마 스타일 적용
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
                font-family: 'Segoe UI';
            }}
            
            QMessageBox QLabel {{
                color: #F0F2F5;
                font-size: 12px;
                padding: 10px;
                background: transparent;
                font-family: 'Segoe UI';
            }}
            
            QMessageBox QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {button_color_start}, stop:1 {button_color_end});
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 600;
                min-width: 80px;
                font-family: 'Segoe UI';
            }}
            
            QMessageBox QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {button_hover_start}, stop:1 {button_hover_end});
            }}
            
            QMessageBox QPushButton:pressed {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {button_pressed_start}, stop:1 {button_pressed_end});
            }}
        """)
        
        msg_box.exec()

