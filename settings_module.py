"""
설정 모듈 - AI Image Tagger 설정 관리 (간소화된 메인 설정)
"""

import json
import os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

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

# WD 설정 모듈 import
try:
    from wd_settings_module import WdSettingsModule
    WD_SETTINGS_AVAILABLE = True
except ImportError:
    WD_SETTINGS_AVAILABLE = False

# LLaVA 설정 모듈 import
try:
    from llava_settings_module import LlavaSettingsModule
    LLAVA_SETTINGS_AVAILABLE = True
except ImportError:
    LLAVA_SETTINGS_AVAILABLE = False


class SettingsModule:
    """설정 관리 모듈"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.models_dir = "models"  # 모델 폴더 경로
        self.wd_settings = None  # WD 설정 모듈 인스턴스
        self.llava_settings = None  # LLaVA 설정 모듈 인스턴스
        
    def open_settings(self):
        """설정 창 열기"""
        # 간단한 설정 다이얼로그 생성
        settings_dialog = QDialog(self.app_instance)
        settings_dialog.setWindowTitle("설정")
        # 창 크기를 무제한으로 설정
        settings_dialog.setMinimumSize(0, 0)  # 최소 크기 무제한
        settings_dialog.setMaximumSize(16777215, 16777215)  # 최대 크기 무제한
        
        # 상대적 크기 계산 (고정값 사용)
        button_padding = 8  # 고정 패딩 (miracle_settings_module과 동일)
        indicator_size = 28  # 고정 인디케이터 크기
        
        settings_dialog.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
            }}
            QLabel {{
                color: #F0F2F5;
                font-size: 12px;
                font-family: 'Segoe UI';
            }}
            QPushButton {{
                background: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: {button_padding}px {button_padding * 2}px;
                font-size: 12px;
                font-weight: 600;
                min-width: 100px;
                font-family: 'Segoe UI';
            }}
            QPushButton:hover {{
                background: #2563EB;
            }}
            QComboBox {{
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                color: white;
                font-family: 'Segoe UI';
                font-size: 12px;
                min-width: 80px;
            }}
            QComboBox:hover {{
                background: rgba(26,27,38,0.85);
                border: 1px solid rgba(75,85,99,0.5);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #CFD8DC;
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background: rgba(26,27,38,0.95);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                color: white;
                selection-background-color: #3B82F6;
            }}
            QComboBox:focus {{
                border: 2px solid #3B82F6;
            }}
            QTextEdit {{
                background: rgba(26,27,38,0.8);
                color: white;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
            }}
            QTextEdit:hover {{
                background: rgba(26,27,38,0.85);
                border: 1px solid rgba(75,85,99,0.5);
            }}
            QTextEdit:focus {{
                border: 2px solid #3B82F6;
            }}
            QLineEdit {{
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                color: white;
                font-family: 'Segoe UI';
                font-size: 12px;
            }}
            QLineEdit:hover {{
                background: rgba(26,27,38,0.85);
                border: 1px solid rgba(75,85,99,0.5);
            }}
            QLineEdit:focus {{
                border: 2px solid #3B82F6;
            }}
            QLineEdit:disabled {{
                background: rgba(26,27,38,0.4);
                border: 1px solid rgba(75,85,99,0.2);
                color: #6B7280;
            }}
        """)
        
        layout = QVBoxLayout(settings_dialog)
        # 고정 여백과 간격 설정
        margin = 20  # 고정 여백
        spacing = 8  # 고정 간격
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)
        
        # 제목
        title_label = QLabel("Settings")
        title_label.setStyleSheet("""
            font-size: 25px;
            font-weight: 700;
            color: #E2E8F0;
            margin-bottom: 8px;
        """)
        layout.addWidget(title_label)
        
        # 모델 선택
        model_label = QLabel("Current Model")
        model_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 6px;
            padding: 6px 0px;
            border-bottom: 1px solid rgba(75,85,99,0.3);
        """)
        layout.addWidget(model_label)
        
        # 모델 목록 가져오기
        model_list = self.get_available_models()
        model_combo = CustomComboBox()
        model_combo.addItems(model_list)
        
        # 현재 모델 선택
        current_model = getattr(self.app_instance, 'current_model', '')
        if current_model in model_list:
            model_combo.setCurrentText(current_model)
        
        layout.addWidget(model_combo)
        
        # 모델별 설정 섹션 컨테이너
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.settings_container)
        
        # 모델 변경 시 설정 섹션 업데이트
        model_combo.currentTextChanged.connect(self.on_model_changed)
        
        # 초기 모델 설정 로드
        self.on_model_changed(model_combo.currentText())
        
        # 여백
        layout.addStretch()
        
        # 버튼들
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # 저장 버튼 (왼쪽)
        save_button = QPushButton("저장")
        save_button.setMinimumWidth(100)  # 최소 너비 설정
        save_button.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
        """)
        save_button.clicked.connect(lambda: self.save_config(settings_dialog, model_combo.currentText()))
        button_layout.addWidget(save_button)
        
        # 스트레치로 중간 공간 채우기
        button_layout.addStretch()
        
        # 닫기 버튼 (오른쪽)
        close_button = QPushButton("닫기")
        close_button.setMinimumWidth(100)  # 최소 너비 설정
        close_button.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
        """)
        close_button.clicked.connect(settings_dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # 다이얼로그 실행
        settings_dialog.exec()
    
    def get_available_models(self):
        """사용 가능한 모델 목록 가져오기"""
        models = []
        if os.path.exists(self.models_dir):
            for item in os.listdir(self.models_dir):
                item_path = os.path.join(self.models_dir, item)
                if os.path.isdir(item_path):
                    # config.json 파일이 있는지 확인
                    config_path = os.path.join(item_path, "config.json")
                    if os.path.exists(config_path):
                        models.append(item)
        
        # WD 모델들을 맨 앞에 정렬
        wd_models = [model for model in models if model.lower().startswith('wd')]
        other_models = [model for model in models if not model.lower().startswith('wd')]
        
        return wd_models + other_models
    
    def _clear_layout(self, layout):
        """레이아웃의 모든 자식 요소들을 재귀적으로 제거"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
                child.layout().setParent(None)
    
    def on_model_changed(self, model_name):
        """모델 변경 시 설정 섹션 업데이트"""
        # 기존 설정 섹션 완전 제거 (한 번에 모든 위젯 제거)
        while self.settings_layout.count() > 0:
            child = self.settings_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
        
        # 설정 모듈 초기화
        self.wd_settings = None
        self.llava_settings = None
        
        if not model_name:
            return
        
        # 디버그 로그
        print(f"[settings] model={model_name} -> llava={self.is_llava_model(model_name)} wd={self.is_wd_model(model_name)}")
            
        # ✅ LLaVA 먼저 판정하고, 렌더 후 즉시 return
        if self.is_llava_model(model_name):
            if LLAVA_SETTINGS_AVAILABLE:
                self.llava_settings = LlavaSettingsModule(self.app_instance)
                self.llava_settings.create_llava_settings_section(self.settings_layout, model_name)
            else:
                info_label = QLabel("LLaVA 설정 모듈을 찾을 수 없습니다.")
                info_label.setStyleSheet("""
                    color: #F59E0B;
                        font-size: 12px;
                    padding: 10px;
                """)
                self.settings_layout.addWidget(info_label)
            return

        # 그 다음에 WD 판정
        if self.is_wd_model(model_name):
            if WD_SETTINGS_AVAILABLE:
                self.wd_settings = WdSettingsModule(self.app_instance)
                self.wd_settings.create_wd_settings_section(self.settings_layout, model_name)
            else:
                info_label = QLabel("WD 설정 모듈을 찾을 수 없습니다.")
                info_label.setStyleSheet("""
                    color: #F59E0B;
                        font-size: 12px;
                    padding: 10px;
                """)
                self.settings_layout.addWidget(info_label)
            return
        
        # 기타 모델인 경우 안내 메시지
        info_label = QLabel("이 모델은 설정이 지원되지 않습니다.")
        info_label.setStyleSheet("""
            color: #6B7280;
                                font-size: 12px;
            padding: 10px;
        """)
        self.settings_layout.addWidget(info_label)
    
    def is_wd_model(self, model_name):
        """WD 모델인지 확인"""
        # 모델명이 'wd'로 시작하는 것만 WD 모델로 인식
        return model_name.lower().startswith('wd')
    
    def is_llava_model(self, model_name):
        """LLaVA 모델인지 확인"""
        name = (model_name or "").lower()
        if name.startswith("llava") or "llava" in name:
            return True
        # config.json 힌트로 보조 판정
        try:
            import json, os
            cfg_path = os.path.join(self.models_dir, model_name, "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    j = json.load(f)
                dump = json.dumps(j).lower()
                # LLaVA 계열에서 흔한 키워드
                return ("vision_tower" in dump) or ("mm_projector" in dump)
        except Exception:
            pass
        return False
    
    def save_config(self, dialog, model_name):
        """설정 저장"""
        if not model_name:
            return
        
        # WD 설정이 있는 경우 저장
        if self.wd_settings:
            success = self.wd_settings.save_wd_config(model_name)
            if success:
                print(f"✅ {model_name} WD 설정 저장 완료")
                dialog.accept()
            else:
                print(f"❌ {model_name} WD 설정 저장 실패")
        # LLaVA 설정이 있는 경우 저장
        elif self.llava_settings:
            success = self.llava_settings.save_llava_config(model_name)
            if success:
                print(f"✅ {model_name} LLaVA 설정 저장 완료")
                dialog.accept()
            else:
                print(f"❌ {model_name} LLaVA 설정 저장 실패")
        else:
            print(f"ℹ️ {model_name} 모델은 별도 설정이 없습니다.")
            dialog.accept()
    
