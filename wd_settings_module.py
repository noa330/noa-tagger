"""
WD Tagger 전용 설정 모듈
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

# WD Tagger 설정 함수들 import
try:
    from wd_tagger import get_tagger_config_value
    TAGGER_AVAILABLE = True
except ImportError:
    TAGGER_AVAILABLE = False


class WdSettingsModule:
    """WD Tagger 전용 설정 관리 모듈"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.models_dir = "models"  # 모델 폴더 경로
        self.wd_config_file = "models/wd_tagger_config.json"  # WD 전용 설정 파일
    
    def load_wd_config(self):
        """WD 설정 불러오기"""
        try:
            if os.path.exists(self.wd_config_file):
                with open(self.wd_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 설정 반환
                return self._get_default_wd_config()
        except Exception as e:
            print(f"WD 설정 불러오기 오류: {str(e)}")
            return self._get_default_wd_config()
    
    def _save_wd_config_to_file(self, config):
        """WD 설정을 파일에 저장 (내부 메서드)"""
        try:
            # models 폴더가 없으면 생성
            os.makedirs(os.path.dirname(self.wd_config_file), exist_ok=True)
            
            with open(self.wd_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"WD 설정 저장 오류: {str(e)}")
            return False
    
    def _get_default_wd_config(self):
        """WD 기본 설정 반환"""
        return {
            "general_threshold": 0.35,
            "character_threshold": 0.85,
            "character_mcut_min": 0.15,
            "max_tags": 30,
            "general_mcut_enabled": False,
            "character_mcut_enabled": False,
            "general_mcut_min_enabled": False,
            "general_mcut_min": 0.15,
            "character_mcut_min_enabled": False,
            "apply_sigmoid": False,
            "tta_enabled": False,
            "tta_horizontal_flip": True,
            "tta_merge_mode": "mean",
            "perf_tier": "balanced"  # "speed", "balanced", "quality"
        }
        
    def create_wd_settings_section(self, layout, model_name):
        """WD Tagger 설정 섹션 생성"""
        if not TAGGER_AVAILABLE:
            return
            
        # 섹션 제목
        tagger_title = QLabel("WD Tagger Settings")
        tagger_title.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-top: 12px;
            margin-bottom: 6px;
            padding: 6px 0px;
            border-bottom: 1px solid rgba(75,85,99,0.3);
        """)
        layout.addWidget(tagger_title)
        
        # 설정 필드들을 7열로 배치
        wd_config = self.load_wd_config()
        
        # 필드 정의 (논리적 그룹화)
        tagger_fields = [
            # 기본 설정
            ("general_threshold", "일반 태그 임계값"),
            ("character_threshold", "캐릭터 태그 임계값"),
            ("max_tags", "최대 태그 수"),
            
            # 일반 MCut 설정
            ("general_mcut_enabled", "일반 MCut 활성화"),
            ("general_mcut_min_enabled", "일반 MCut 최소값 활성화"),
            ("general_mcut_min", "일반 MCut 최소값"),
            
            # 캐릭터 MCut 설정
            ("character_mcut_enabled", "캐릭터 MCut 활성화"),
            ("character_mcut_min_enabled", "캐릭터 MCut 최소값 활성화"),
            ("character_mcut_min", "캐릭터 MCut 최소값"),
            
            # 고급 기능
            ("apply_sigmoid", "Sigmoid 적용"),
            ("tta_enabled", "TTA 활성화"),
            ("tta_horizontal_flip", "TTA 수평 뒤집기"),
            ("tta_merge_mode", "TTA 병합 모드")
        ]
        
        # 7열로 배치
        row_layout = QHBoxLayout()
        row_layout.setSpacing(2)
        
        # 모든 필드 생성
        for field_key, field_label in tagger_fields:
            # 필드 컨테이너
            field_container = QVBoxLayout()
            field_container.setSpacing(4)
            
            # 라벨
            label = QLabel(f"{field_label}:")
            label.setStyleSheet("""
                font-size: 11px;
                font-weight: 500;
                color: #9CA3AF;
                margin-bottom: 3px;
            """)
            field_container.addWidget(label)
            
            # 입력 필드 생성
            value = wd_config.get(field_key, self._get_default_value(field_key))
            
            # 체크박스 필드들
            if field_key in ["general_mcut_enabled", "character_mcut_enabled", "general_mcut_min_enabled", "character_mcut_min_enabled", "apply_sigmoid", "tta_enabled", "tta_horizontal_flip"]:
                # 커스텀 체크박스 클래스 정의
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
                
                input_field = CustomCheckBox()
                input_field.setChecked(bool(value))
            elif field_key == "tta_merge_mode":
                # 드롭다운 필드
                input_field = CustomComboBox()
                input_field.addItems(["mean", "max"])
                input_field.setCurrentText(str(value))
                input_field.setStyleSheet("""
                    QComboBox {
                        background: rgba(26,27,38,0.8);
                        border: 1px solid rgba(75,85,99,0.3);
                        color: white;
                        font-family: 'Segoe UI';
                        font-size: 12px;
                        min-width: 80px;
                    }
                    QComboBox:hover {
                        background: rgba(26,27,38,0.85);
                        border: 1px solid rgba(75,85,99,0.5);
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
                        border: 1px solid rgba(75,85,99,0.3);
                        border-radius: 4px;
                        color: white;
                        selection-background-color: #3B82F6;
                    }
                    QComboBox:focus {
                        border: 2px solid #3B82F6;
                    }
                    QComboBox:disabled {
                        background: rgba(26,27,38,0.4);
                        border: 1px solid rgba(75,85,99,0.2);
                        color: #6B7280;
                    }
                    QComboBox::down-arrow:disabled {
                        border-top: 5px solid #6B7280;
                    }
                """)
            else:
                # 텍스트 입력 필드
                input_field = QLineEdit(str(value))
                input_field.setStyleSheet("""
                    QLineEdit {
                        background: rgba(26,27,38,0.8);
                        border: 1px solid rgba(75,85,99,0.3);
                        color: white;
                        font-family: 'Segoe UI';
                        font-size: 12px;
                    }
                    QLineEdit:hover {
                        background: rgba(26,27,38,0.85);
                        border: 1px solid rgba(75,85,99,0.5);
                    }
                    QLineEdit:focus {
                        border: 2px solid #3B82F6;
                    }
                    QLineEdit:disabled {
                        background: rgba(26,27,38,0.4);
                        border: 1px solid rgba(75,85,99,0.2);
                        color: #6B7280;
                    }
                """)
            
            # 인스턴스 변수로 저장
            self._set_field_reference(field_key, input_field)
            
            field_container.addWidget(input_field)
            
            # 필드 컨테이너를 행 레이아웃에 추가
            field_widget = QWidget()
            field_widget.setLayout(field_container)
            row_layout.addWidget(field_widget)
        
        # 모든 필드 생성 후 연결 설정
        self._setup_field_dependencies()
        
        # 초기 상태 설정
        self._set_initial_field_states()
        
        # 빈 공간 채우기 (13개 필드이므로 1개 더 추가)
        for _ in range(1):
            row_layout.addWidget(QWidget())
        
        layout.addLayout(row_layout)
        
        # JSON 기반 모델별 설정 필드들 추가
        self.create_config_fields(layout, model_name)
    
    def create_config_fields(self, layout, model_name):
        """Config 필드들을 생성 (모델별 개별 설정)"""
        config_data = self.load_model_config_data(model_name)
        if not config_data:
            return
        
        # 실제 config.json에 있는 필드들만 표시
        field_groups = [
            {
                "title": "Model Architecture",
                "fields": [
                    ("architecture", "Architecture"),
                    ("num_classes", "Number of Classes"),
                    ("num_features", "Number of Features"),
                    ("global_pool", "Global Pool"),
                    ("model_args.act_layer", "Activation Layer"),
                    ("model_args.global_pool", "Model Global Pool"),
                    ("pretrained_cfg.num_classes", "Pretrained Classes")
                ]
            },
            {
                "title": "Size & Dimensions",
                "fields": [
                    ("model_args.img_size", "Image Size"),
                    ("model_args.patch_size", "Patch Size"),
                    ("pretrained_cfg.input_size", "Input Size"),
                    ("pretrained_cfg.pool_size", "Pool Size"),
                    ("pretrained_cfg.fixed_input_size", "Fixed Input Size"),
                    ("pretrained_cfg.crop_pct", "Crop Percentage"),
                    ("pretrained_cfg.crop_mode", "Crop Mode")
                ]
            },
            {
                "title": "Normalization & Processing",
                "fields": [
                    ("pretrained_cfg.mean", "Mean"),
                    ("pretrained_cfg.std", "Standard Deviation"),
                    ("pretrained_cfg.interpolation", "Interpolation"),
                    ("model_args.class_token", "Class Token"),
                    ("model_args.fc_norm", "FC Norm"),
                    ("pretrained_cfg.custom_load", "Custom Load"),
                    ("pretrained_cfg.first_conv", "First Conv")
                ]
            },
            {
                "title": "Advanced Components",
                "fields": [
                    ("pretrained_cfg.classifier", "Classifier")
                ]
            }
        ]
        
        for group in field_groups:
            # 그룹 제목
            group_title = QLabel(group["title"])
            group_title.setStyleSheet("""
                font-size: 13px;
                font-weight: 600;
                color: #E2E8F0;
                margin-top: 12px;
                margin-bottom: 6px;
                padding: 4px 0px;
                border-bottom: 1px solid rgba(75,85,99,0.3);
            """)
            layout.addWidget(group_title)
            
            # 그룹 내 필드들을 7열로 배치
            fields = group["fields"]
            for i in range(0, len(fields), 7):  # 7열로 배치
                row_layout = QHBoxLayout()
                row_layout.setSpacing(2)
                
                # 현재 행의 필드들 (최대 7개)
                row_fields = fields[i:i+7]
                
                for field_key, field_label in row_fields:
                    # 필드 컨테이너
                    field_container = QVBoxLayout()
                    field_container.setSpacing(4)
                    
                    # 라벨
                    label = QLabel(f"{field_label}:")
                    label.setStyleSheet("""
                        font-size: 11px;
                        font-weight: 500;
                        color: #9CA3AF;
                        margin-bottom: 3px;
                    """)
                    field_container.addWidget(label)
                    
                    # 입력 필드
                    value = self.get_nested_value(config_data, field_key)
                    if isinstance(value, (list, tuple)):
                        value_str = str(value).replace("'", '"')
                    elif isinstance(value, bool):
                        value_str = str(value).lower()
                    else:
                        value_str = str(value) if value is not None else ""
                    
                    if field_key in ["pretrained_cfg.fixed_input_size", "model_args.class_token", "model_args.fc_norm", "pretrained_cfg.custom_load"]:
                        # 커스텀 체크박스 클래스 정의
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
                        
                        # 체크박스로 처리
                        checkbox = CustomCheckBox()
                        checkbox.setChecked(bool(value))
                        # 인스턴스 변수로 저장
                        setattr(self, f"config_{field_key.replace('.', '_')}_input", checkbox)
                        field_container.addWidget(checkbox)
                    else:
                        # 텍스트 입력으로 처리
                        input_field = QLineEdit(value_str)
                        input_field.setStyleSheet("""
                            QLineEdit {
                                background: rgba(26,27,38,0.8);
                                border: 1px solid rgba(75,85,99,0.3);
                                color: white;
                                font-family: 'Segoe UI';
                                font-size: 12px;
                            }
                            QLineEdit:hover {
                                background: rgba(26,27,38,0.85);
                                border: 1px solid rgba(75,85,99,0.5);
                            }
                            QLineEdit:focus {
                                border: 2px solid #3B82F6;
                            }
                            QLineEdit:disabled {
                                background: rgba(26,27,38,0.4);
                                border: 1px solid rgba(75,85,99,0.2);
                                color: #6B7280;
                            }
                        """)
                        # 인스턴스 변수로 저장
                        setattr(self, f"config_{field_key.replace('.', '_')}_input", input_field)
                        field_container.addWidget(input_field)
                    
                    # 필드 컨테이너를 행 레이아웃에 추가
                    field_widget = QWidget()
                    field_widget.setLayout(field_container)
                    row_layout.addWidget(field_widget)
                
                # 빈 공간 채우기 (7개 미만인 경우)
                while row_layout.count() < 7:
                    row_layout.addWidget(QWidget())
                
                layout.addLayout(row_layout)
    
    def get_nested_value(self, data, key):
        """중첩된 키에서 값을 가져오기"""
        keys = key.split('.')
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current
    
    def set_nested_value(self, data, key, value):
        """중첩된 키에 값을 설정하기"""
        keys = key.split('.')
        current = data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    
    def load_model_config_data(self, model_name):
        """모델의 config.json 파일을 딕셔너리로 로드"""
        config_path = os.path.join(self.models_dir, model_name, "config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Config 파일 읽기 오류: {str(e)}")
        return None
    
    def _setup_field_dependencies(self):
        """필드 간 의존성 설정"""
        # 일반 MCut 활성화에 따른 관련 필드 활성화/비활성화
        if hasattr(self, 'general_mcut_enabled_input'):
            if hasattr(self, 'general_mcut_min_enabled_input'):
                self.general_mcut_enabled_input.toggled.connect(
                    lambda checked: self.general_mcut_min_enabled_input.setEnabled(checked)
                )
            if hasattr(self, 'general_mcut_min_input'):
                self.general_mcut_enabled_input.toggled.connect(
                    lambda checked: self.general_mcut_min_input.setEnabled(checked)
                )
        
        # 캐릭터 MCut 활성화에 따른 관련 필드 활성화/비활성화
        if hasattr(self, 'character_mcut_enabled_input'):
            if hasattr(self, 'character_mcut_min_enabled_input'):
                self.character_mcut_enabled_input.toggled.connect(
                    lambda checked: self.character_mcut_min_enabled_input.setEnabled(checked)
                )
            if hasattr(self, 'character_mcut_min_input'):
                self.character_mcut_enabled_input.toggled.connect(
                    lambda checked: self.character_mcut_min_input.setEnabled(checked)
                )
        
        # TTA 활성화에 따른 관련 필드 활성화/비활성화
        if hasattr(self, 'tta_enabled_input'):
            if hasattr(self, 'tta_horizontal_flip_input'):
                self.tta_enabled_input.toggled.connect(
                    lambda checked: self.tta_horizontal_flip_input.setEnabled(checked)
                )
            if hasattr(self, 'tta_merge_mode_input'):
                self.tta_enabled_input.toggled.connect(
                    lambda checked: self.tta_merge_mode_input.setEnabled(checked)
                )
    
    def _set_initial_field_states(self):
        """초기 필드 상태 설정"""
        # 일반 MCut 관련 필드들의 초기 상태
        if hasattr(self, 'general_mcut_enabled_input'):
            general_mcut_enabled = self.general_mcut_enabled_input.isChecked()
            if hasattr(self, 'general_mcut_min_enabled_input'):
                self.general_mcut_min_enabled_input.setEnabled(general_mcut_enabled)
            if hasattr(self, 'general_mcut_min_input'):
                self.general_mcut_min_input.setEnabled(general_mcut_enabled)
        
        # 캐릭터 MCut 관련 필드들의 초기 상태
        if hasattr(self, 'character_mcut_enabled_input'):
            character_mcut_enabled = self.character_mcut_enabled_input.isChecked()
            if hasattr(self, 'character_mcut_min_enabled_input'):
                self.character_mcut_min_enabled_input.setEnabled(character_mcut_enabled)
            if hasattr(self, 'character_mcut_min_input'):
                self.character_mcut_min_input.setEnabled(character_mcut_enabled)
        
        # TTA 관련 필드들의 초기 상태
        if hasattr(self, 'tta_enabled_input'):
            tta_enabled = self.tta_enabled_input.isChecked()
            if hasattr(self, 'tta_horizontal_flip_input'):
                self.tta_horizontal_flip_input.setEnabled(tta_enabled)
            if hasattr(self, 'tta_merge_mode_input'):
                self.tta_merge_mode_input.setEnabled(tta_enabled)
    
    def _get_default_value(self, field_key):
        """필드별 기본값 반환"""
        defaults = {
            "general_threshold": 0.35,
            "character_threshold": 0.85,
            "character_mcut_min": 0.15,
            "max_tags": 30,
            "general_mcut_enabled": False,
            "character_mcut_enabled": False,
            "general_mcut_min_enabled": False,
            "general_mcut_min": 0.15,
            "character_mcut_min_enabled": False,
            "apply_sigmoid": False,
            "tta_enabled": False,
            "tta_horizontal_flip": True,
            "tta_merge_mode": "mean"
        }
        return defaults.get(field_key, "")
    
    def _set_field_reference(self, field_key, input_field):
        """필드 참조를 인스턴스 변수로 저장"""
        field_refs = {
            "general_threshold": "general_threshold_input",
            "character_threshold": "character_threshold_input",
            "character_mcut_min": "character_mcut_min_input",
            "max_tags": "max_tags_input",
            "general_mcut_enabled": "general_mcut_enabled_input",
            "character_mcut_enabled": "character_mcut_enabled_input",
            "general_mcut_min_enabled": "general_mcut_min_enabled_input",
            "general_mcut_min": "general_mcut_min_input",
            "character_mcut_min_enabled": "character_mcut_min_enabled_input",
            "apply_sigmoid": "apply_sigmoid_input",
            "tta_enabled": "tta_enabled_input",
            "tta_horizontal_flip": "tta_horizontal_flip_input",
            "tta_merge_mode": "tta_merge_mode_input"
        }
        
        if field_key in field_refs:
            setattr(self, field_refs[field_key], input_field)
    
    def save_wd_config(self, model_name=None):
        """WD Tagger 설정 저장 (공통 설정 + 모델별 JSON 설정)"""
        success = True
        
        # 1. WD Tagger 공통 설정 저장
        if TAGGER_AVAILABLE:
            try:
                wd_config = self.load_wd_config()
                
                # 모든 필드 값 수집
                field_values = {}
                
                # 텍스트 입력 필드들 (비활성화된 필드는 기본값으로 저장)
                if hasattr(self, 'general_threshold_input'):
                    if self.general_threshold_input.isEnabled():
                        field_values["general_threshold"] = float(self.general_threshold_input.text().strip())
                    else:
                        field_values["general_threshold"] = 0.35  # 기본값
                if hasattr(self, 'character_threshold_input'):
                    if self.character_threshold_input.isEnabled():
                        field_values["character_threshold"] = float(self.character_threshold_input.text().strip())
                    else:
                        field_values["character_threshold"] = 0.85  # 기본값
                if hasattr(self, 'character_mcut_min_input'):
                    if self.character_mcut_min_input.isEnabled():
                        field_values["character_mcut_min"] = float(self.character_mcut_min_input.text().strip())
                    else:
                        field_values["character_mcut_min"] = 0.15  # 기본값
                if hasattr(self, 'max_tags_input'):
                    if self.max_tags_input.isEnabled():
                        field_values["max_tags"] = int(self.max_tags_input.text().strip())
                    else:
                        field_values["max_tags"] = 30  # 기본값
                if hasattr(self, 'general_mcut_min_input'):
                    if self.general_mcut_min_input.isEnabled():
                        field_values["general_mcut_min"] = float(self.general_mcut_min_input.text().strip())
                    else:
                        field_values["general_mcut_min"] = 0.15  # 기본값
                if hasattr(self, 'tta_merge_mode_input'):
                    if self.tta_merge_mode_input.isEnabled():
                        field_values["tta_merge_mode"] = self.tta_merge_mode_input.currentText()
                    else:
                        field_values["tta_merge_mode"] = "mean"  # 기본값
                
                # 체크박스 필드들 (비활성화된 필드는 기본값으로 저장)
                if hasattr(self, 'general_mcut_enabled_input'):
                    if self.general_mcut_enabled_input.isEnabled():
                        field_values["general_mcut_enabled"] = self.general_mcut_enabled_input.isChecked()
                    else:
                        field_values["general_mcut_enabled"] = False  # 기본값
                if hasattr(self, 'character_mcut_enabled_input'):
                    if self.character_mcut_enabled_input.isEnabled():
                        field_values["character_mcut_enabled"] = self.character_mcut_enabled_input.isChecked()
                    else:
                        field_values["character_mcut_enabled"] = False  # 기본값
                if hasattr(self, 'general_mcut_min_enabled_input'):
                    if self.general_mcut_min_enabled_input.isEnabled():
                        field_values["general_mcut_min_enabled"] = self.general_mcut_min_enabled_input.isChecked()
                    else:
                        field_values["general_mcut_min_enabled"] = False  # 기본값
                if hasattr(self, 'character_mcut_min_enabled_input'):
                    if self.character_mcut_min_enabled_input.isEnabled():
                        field_values["character_mcut_min_enabled"] = self.character_mcut_min_enabled_input.isChecked()
                    else:
                        field_values["character_mcut_min_enabled"] = False  # 기본값
                if hasattr(self, 'apply_sigmoid_input'):
                    if self.apply_sigmoid_input.isEnabled():
                        field_values["apply_sigmoid"] = self.apply_sigmoid_input.isChecked()
                    else:
                        field_values["apply_sigmoid"] = False  # 기본값
                if hasattr(self, 'tta_enabled_input'):
                    if self.tta_enabled_input.isEnabled():
                        field_values["tta_enabled"] = self.tta_enabled_input.isChecked()
                    else:
                        field_values["tta_enabled"] = False  # 기본값
                if hasattr(self, 'tta_horizontal_flip_input'):
                    if self.tta_horizontal_flip_input.isEnabled():
                        field_values["tta_horizontal_flip"] = self.tta_horizontal_flip_input.isChecked()
                    else:
                        field_values["tta_horizontal_flip"] = False  # 기본값
                
                # 설정 업데이트
                wd_config.update(field_values)
                
                # 파일에 저장
                self._save_wd_config_to_file(wd_config)
                print("✅ WD Tagger 공통 설정 저장 완료")
                
            except Exception as e:
                print(f"❌ WD Tagger 공통 설정 저장 실패: {str(e)}")
                success = False
        
        # 2. 모델별 JSON 설정 저장
        if model_name:
            try:
                config_data = self.load_model_config_data(model_name)
                if config_data:
                    # 모든 config 필드 값들을 수집
                    config_field_keys = [
                        "architecture", "num_classes", "num_features", "global_pool",
                        "model_args.act_layer", "model_args.global_pool", "pretrained_cfg.num_classes",
                        "model_args.img_size", "model_args.patch_size", "pretrained_cfg.input_size",
                        "pretrained_cfg.pool_size", "pretrained_cfg.fixed_input_size", "pretrained_cfg.crop_pct",
                        "pretrained_cfg.crop_mode", "pretrained_cfg.mean", "pretrained_cfg.std",
                        "pretrained_cfg.interpolation", "model_args.class_token", "model_args.fc_norm",
                        "pretrained_cfg.custom_load", "pretrained_cfg.first_conv", "pretrained_cfg.classifier"
                    ]
                    
                    for field_key in config_field_keys:
                        input_attr_name = f"config_{field_key.replace('.', '_')}_input"
                        if hasattr(self, input_attr_name):
                            widget = getattr(self, input_attr_name)
                            if isinstance(widget, QCheckBox):
                                value = widget.isChecked()
                            elif isinstance(widget, QLineEdit):
                                text = widget.text().strip()
                                # 빈 문자열이면 null로 처리
                                if not text:
                                    value = None
                                # 타입 변환 시도
                                elif text.lower() in ['true', 'false']:
                                    value = text.lower() == 'true'
                                elif text.startswith('[') and text.endswith(']'):
                                    try:
                                        value = json.loads(text)
                                    except:
                                        value = text
                                elif text.isdigit():
                                    value = int(text)
                                elif text.replace('.', '').isdigit():
                                    value = float(text)
                                else:
                                    value = text
                            else:
                                continue
                            
                            self.set_nested_value(config_data, field_key, value)
                    
                    # 파일에 저장
                    config_path = os.path.join(self.models_dir, model_name, "config.json")
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config_data, f, indent=2, ensure_ascii=False)
                    print(f"✅ {model_name} 모델별 JSON 설정 저장 완료")
                else:
                    print(f"⚠️ {model_name} 모델의 config.json을 찾을 수 없습니다.")
                    
            except Exception as e:
                print(f"❌ {model_name} 모델별 JSON 설정 저장 실패: {str(e)}")
                success = False
        
        return success
