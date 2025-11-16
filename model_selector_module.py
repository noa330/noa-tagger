"""
모델 선택 모듈 - 액션 탭에서 사용할 모델 선택 드롭박스 관리
확장성을 고려하여 별도 모듈로 분리
"""

import os
from PySide6.QtWidgets import *
from PySide6.QtCore import *

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


class ModelSelectorModule:
    """모델 선택 관리 모듈 - 확장 가능한 구조"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.models_dir = "models"  # 모델 폴더 경로
        self.current_model_id = None
        
        # 사용 가능한 모델들 정의 (하드코딩)
        self.available_models = [
            # WD Tagger 모델들 (v3 - 최신, 안정적)
            ("SmilingWolf/wd-vit-large-tagger-v3", "WD VIT Large v3 (기본)"),
            ("SmilingWolf/wd-eva02-large-tagger-v3", "WD EVA02 Large v3"),
            ("SmilingWolf/wd-convnext-tagger-v3", "WD ConvNeXT v3"),
            ("SmilingWolf/wd-swinv2-tagger-v3", "WD SwinV2 v3"),
            ("SmilingWolf/wd-vit-tagger-v3", "WD VIT v3"),
            
            # WD Tagger 모델들 (v2)
            ("SmilingWolf/wd-v1-4-swinv2-tagger-v2", "WD v1.4 SwinV2 v2"),
            ("SmilingWolf/wd-v1-4-convnext-tagger-v2", "WD v1.4 ConvNeXT v2"),
            ("SmilingWolf/wd-v1-4-convnextv2-tagger-v2", "WD v1.4 ConvNeXTV2 v2"),
            ("SmilingWolf/wd-v1-4-vit-tagger-v2", "WD v1.4 VIT v2"),
            ("SmilingWolf/wd-v1-4-moat-tagger-v2", "WD v1.4 MOAT v2"),
            
            # LLaVA 캡셔너 모델들
            ("llava-hf/llava-1.5-7b-hf", "LLaVA 1.5 7B"),
            ("llava-hf/llava-1.5-13b-hf", "LLaVA 1.5 13B"),
            
            # LLaVA 변형 모델들
            # LLaVA-NeXT (1.6) 모델들
            ("llava-hf/llava-v1.6-mistral-7b-hf", "LLaVA-NeXT 1.6 Mistral 7B"),
            ("llava-hf/llava-v1.6-vicuna-7b-hf", "LLaVA-NeXT 1.6 Vicuna 7B"),
            ("llava-hf/llava-v1.6-vicuna-13b-hf", "LLaVA-NeXT 1.6 Vicuna 13B"),
            ("llava-hf/llava-v1.6-34b-hf", "LLaVA-NeXT 1.6 34B"),
            
            # LLaVA-Interleave 모델들
            ("llava-hf/llava-interleave-qwen-7b-hf", "LLaVA-Interleave Qwen 7B"),
            ("llava-hf/llava-interleave-vicuna-7b-hf", "LLaVA-Interleave Vicuna 7B"),
            ("llava-hf/llava-interleave-vicuna-13b-hf", "LLaVA-Interleave Vicuna 13B"),
            
            # ViP-LLaVA 모델들
            ("llava-hf/vip-llava-7b-hf", "ViP-LLaVA 7B"),
            ("llava-hf/vip-llava-13b-hf", "ViP-LLaVA 13B"),
            
            # 기타 LLaVA 변형 모델들
            ("llava-hf/llava-llama-3-8b-v1_1-transformers", "LLaVA-Llama-3 8B v1.1"),
            ("llava-hf/llava-llama-3-8b-instruct-transformers", "LLaVA-Llama-3 8B Instruct"),
        ]
        
        # 기본 모델 설정
        self.current_model_id = "SmilingWolf/wd-vit-large-tagger-v3"
        
    def create_model_selector(self):
        """모델 선택 드롭박스 생성"""
        model_combo = CustomComboBox()
        model_combo.setStyleSheet("""
            QComboBox {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 12px;
                min-width: 200px;
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
        
        # 모델 목록 추가
        for model_id, display_name in self.available_models:
            model_combo.addItem(display_name, model_id)
        
        # 기본 모델 선택
        model_combo.setCurrentText("WD VIT Large v3 (기본)")
        
        # 모델 변경 시그널 연결
        model_combo.currentTextChanged.connect(self.on_model_changed)
        
        return model_combo
    
    def on_model_changed(self, display_name):
        """모델 선택 변경 시 호출"""
        # 선택된 모델 ID 찾기
        for model_id, name in self.available_models:
            if name == display_name:
                self.current_model_id = model_id
                print(f"모델 변경: {display_name} -> {model_id}")
                
                # 앱 인스턴스의 현재 모델 ID 업데이트
                if hasattr(self.app_instance, 'current_model_id'):
                    self.app_instance.current_model_id = model_id
                
                # 모델 타입에 따른 추가 처리
                self._handle_model_type_change(model_id)
                
                # 메인 앱의 on_model_changed 메서드 호출
                if hasattr(self.app_instance, 'on_model_changed'):
                    self.app_instance.on_model_changed(display_name)
                break
    
    def _handle_model_type_change(self, model_id):
        """모델 타입 변경에 따른 추가 처리"""
        # 단순히 메인 앱의 처리만 호출
        print(f"모델 선택됨: {model_id}")
        if hasattr(self.app_instance, 'update_button_texts_for_tagger'):
            self.app_instance.update_button_texts_for_tagger()
    
    def get_current_model_id(self):
        """현재 선택된 모델 ID 반환"""
        return self.current_model_id
    
    
    def get_available_models(self):
        """사용 가능한 모델 목록 반환"""
        return self.available_models
    
    def add_model(self, model_id, display_name):
        """새로운 모델 추가 (확장성)"""
        self.available_models.append((model_id, display_name))
        print(f"새 모델 추가: {display_name} ({model_id})")
    
    def remove_model(self, model_id):
        """모델 제거 (확장성)"""
        self.available_models = [(mid, name) for mid, name in self.available_models if mid != model_id]
        print(f"모델 제거: {model_id}")
    
    def get_model_display_name(self, model_id):
        """모델 ID로부터 표시 이름 반환"""
        for mid, name in self.available_models:
            if mid == model_id:
                return name
        return model_id
    
    def set_current_model(self, model_id):
        """특정 모델 ID로 현재 모델 설정"""
        for mid, name in self.available_models:
            if mid == model_id:
                self.current_model_id = model_id
                print(f"현재 모델 설정: {name} ({model_id})")
                return True
        print(f"모델을 찾을 수 없음: {model_id}")
        return False
    
    def refresh_models(self):
        """모델 목록 새로고침 (확장성)"""
        # 로컬 모델 폴더에서 모델 검색
        local_models = self._scan_local_models()
        
        # 로컬 모델들을 available_models에 추가 (중복 제거)
        for model_id, display_name in local_models:
            if not any(mid == model_id for mid, _ in self.available_models):
                self.available_models.append((model_id, display_name))
        
        print(f"모델 목록 새로고침 완료: {len(self.available_models)}개 모델")
    
    def _scan_local_models(self):
        """로컬 모델 폴더에서 모델 스캔"""
        local_models = []
        
        if not os.path.exists(self.models_dir):
            return local_models
        
        try:
            for item in os.listdir(self.models_dir):
                item_path = os.path.join(self.models_dir, item)
                if os.path.isdir(item_path):
                    # 폴더명을 모델명으로 사용
                    display_name = f"로컬: {item}"
                    local_models.append((item, display_name))
        except Exception as e:
            print(f"로컬 모델 스캔 중 오류: {e}")
        
        return local_models
    
    def create_model_info_widget(self):
        """모델 정보 표시 위젯 생성 (확장성)"""
        info_widget = QWidget()
        layout = QVBoxLayout(info_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 현재 모델 정보
        current_model_label = QLabel(f"현재 모델: {self.get_model_display_name(self.current_model_id)}")
        current_model_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                padding: 4px 8px;
                background: rgba(17,17,27,0.5);
                border-radius: 6px;
                border: 1px solid rgba(75,85,99,0.3);
            }
        """)
        layout.addWidget(current_model_label)
        
        return info_widget
    
    def create_model_management_panel(self):
        """모델 관리 패널 생성 (확장성)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 제목
        title_label = QLabel("모델 관리")
        title_label.setStyleSheet("""
            QLabel {
                color: #F9FAFB;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(title_label)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("모델 목록 새로고침")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 1.0);
            }
            QPushButton:pressed {
                background: rgba(37, 99, 235, 1.0);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_models)
        layout.addWidget(refresh_btn)
        
        # 모델 추가 버튼 (예시)
        add_model_btn = QPushButton("모델 추가")
        add_model_btn.setStyleSheet("""
            QPushButton {
                background: rgba(34, 197, 94, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(34, 197, 94, 1.0);
            }
            QPushButton:pressed {
                background: rgba(21, 128, 61, 1.0);
            }
        """)
        add_model_btn.clicked.connect(self._show_add_model_dialog)
        layout.addWidget(add_model_btn)
        
        layout.addStretch()
        return panel
    
    def _show_add_model_dialog(self):
        """모델 추가 다이얼로그 표시 (확장성)"""
        dialog = QDialog(self.app_instance)
        dialog.setWindowTitle("새 모델 추가")
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background: rgba(17,17,27,0.95);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # 모델 ID 입력
        id_label = QLabel("모델 ID:")
        id_input = QLineEdit()
        id_input.setPlaceholderText("예: SmilingWolf/wd-vit-large-tagger-v4")
        
        # 표시 이름 입력
        name_label = QLabel("표시 이름:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("예: WD VIT Large v4")
        
        # 버튼들
        button_layout = QHBoxLayout()
        add_btn = QPushButton("추가")
        cancel_btn = QPushButton("취소")
        
        add_btn.clicked.connect(lambda: self._add_model_from_dialog(
            id_input.text(), name_input.text(), dialog))
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(id_label)
        layout.addWidget(id_input)
        layout.addWidget(name_label)
        layout.addWidget(name_input)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _add_model_from_dialog(self, model_id, display_name, dialog):
        """다이얼로그에서 모델 추가"""
        if model_id and display_name:
            self.add_model(model_id, display_name)
            dialog.accept()
            QMessageBox.information(self.app_instance, "성공", 
                                  f"모델이 추가되었습니다: {display_name}")
        else:
            QMessageBox.warning(self.app_instance, "오류", 
                              "모델 ID와 표시 이름을 모두 입력해주세요.")
    
    def is_llava_model(self, model_id=None):
        """LLaVA 모델인지 확인 (모든 LLaVA 변형 포함)"""
        if model_id is None:
            model_id = self.current_model_id
        return any(variant in model_id.lower() for variant in [
            "llava-1.5", "llava-v1.6", "llava-interleave", "vip-llava", "llava-llama-3"
        ])
    
    def is_wd_tagger_model(self, model_id=None):
        """WD Tagger 모델인지 확인"""
        if model_id is None:
            model_id = self.current_model_id
        return not self.is_llava_model(model_id)
    
