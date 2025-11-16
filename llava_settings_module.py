"""
LLaVA 전용 설정 모듈
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


class LlavaSettingsModule:
    """LLaVA 전용 설정 관리 모듈"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.models_dir = "models"  # 모델 폴더 경로
        # llava_config_file은 이제 동적으로 결정됨
    
    def _resolve_llava_config_path(self, model_name: str | None = None) -> str:
        """모델명에 따라 적절한 설정 파일 경로를 반환"""
        name = (model_name or getattr(self.app_instance, "current_model_id", "") or "").lower()
        
        # 변종/시리즈별 전용 설정 파일 매핑
        if "llava-interleave" in name:
            config_path = "models/llava_interleave_config.json"   # interleave 전용
        elif "llava-llama-3" in name or "llama-3" in name:
            config_path = "models/llava_llama3_config.json"       # llama3 전용
        elif "llava-v1.6" in name or "llava-next" in name:
            config_path = "models/llava_next_config.json"         # NeXT/1.6 전용
        elif "vip-llava" in name or "vip_llava" in name:
            config_path = "models/llava_vip_config.json"          # ViP-LLaVA 전용
        else:
            # 그 외(=기본 1.5/공용) → 기존 파일
            config_path = "models/llava_tagger_config.json"
        
        print(f"[DEBUG] 모델명 '{name}' → 설정 파일: {config_path}")
        return config_path
    
    def load_llava_config(self, model_name: str | None = None):
        """LLaVA 설정 불러오기"""
        config_path = self._resolve_llava_config_path(model_name)
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 설정 반환
                return self._get_default_llava_config()
        except Exception as e:
            print(f"LLaVA 설정 불러오기 오류: {str(e)}")
            return self._get_default_llava_config()
    
    def _save_llava_config_to_file(self, config, model_name: str | None = None):
        """LLaVA 설정을 파일에 저장 (내부 메서드)"""
        config_path = self._resolve_llava_config_path(model_name)
        try:
            # models 폴더가 없으면 생성
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"LLaVA 설정 저장 오류: {str(e)}")
            return False
    
    def _get_default_llava_config(self):
        """LLaVA 기본 설정 반환 (확장된 버전)"""
        return {
            # 기존 생성 옵션
            "max_tokens": 500,
            "temperature": 0.1,
            "top_p": 0.9,
            "num_beams": 1,
            
            # 추가 디코딩/샘플링 제어
            "top_k": None,
            "typical_p": None,
            "repetition_penalty": 1.0,
            "no_repeat_ngram_size": 0,
            "length_penalty": 1.0,
            "min_new_tokens": 1,
            "early_stopping": None,
            "do_sample": None,
            
            # 종료/토큰 관련
            "eos_token_id": None,
            "pad_token_id": None,
            
            # 실행/메모리/속도
            "quantization_type": "4bit",
            "use_flash_attention": True,
            "device_map": None,
            "torch_dtype": None,
            "max_memory": None,
            "offload_policy": "auto",
            
            # 프롬프트 스타일/페르소나
            "prompt_style": "sentence_caption",
            "prompt_persona": "neutral",
            "custom_prompt": "",
            "custom_persona": "",
            
            # 변종별 추가 옵션
            "multi_image_max": 4,
            "image_aspect_policy": "auto"
        }
        
    def create_llava_settings_section(self, layout, model_name):
        """LLaVA 설정 섹션 생성"""
        print(f"[DEBUG] LLaVA 설정 섹션 생성 시작: {model_name}")
        
        # 설정 불러오기 (모델명 기반)
        llava_config = self.load_llava_config(model_name=model_name)
        
        # 섹션 제목
        llava_title = QLabel("LLaVA Settings")
        llava_title.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-top: 12px;
            margin-bottom: 6px;
            padding: 6px 0px;
            border-bottom: 1px solid rgba(75,85,99,0.3);
        """)
        layout.addWidget(llava_title)
        
        # WD 설정 모듈과 일치하는 공통 스타일
        common_input_style = """
            background: rgba(26,27,38,0.8);
            border: 1px solid rgba(75,85,99,0.3);
            color: white;
            font-family: 'Segoe UI';
            font-size: 12px;
        """
        
        common_hover_style = """
            background: rgba(26,27,38,0.85);
            border: 1px solid rgba(75,85,99,0.5);
        """
        
        common_focus_style = """
            border: 2px solid #3B82F6;
        """
        
        common_combobox_style = f"""
            QComboBox {{
                {common_input_style}
                min-width: 80px;
            }}
            QComboBox:hover {{
                {common_hover_style}
            }}
            QComboBox:focus {{
                {common_focus_style}
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background: rgba(26,27,38,0.95);
                border: 1px solid rgba(75,85,99,0.5);
                border-radius: 4px;
                color: white;
                selection-background-color: #3B82F6;
            }}
        """
        
        # 모델별 지원 옵션 정의
        def get_supported_fields(model_name):
            name = (model_name or "").lower()
            
            # 공통 기본 옵션 (모든 LLaVA 모델)
            common_fields = [
                ("max_tokens", "최대 토큰 수"),
                ("temperature", "Temperature"),
                ("top_p", "Top P"),
                ("num_beams", "Beam Size"),
                ("quantization_type", "양자화 타입"),
                ("use_flash_attention", "FlashAttention2"),
                ("prompt_style", "프롬프트 스타일"),
                ("prompt_persona", "페르소나"),
                ("custom_prompt", "커스텀 프롬프트"),
                ("custom_persona", "커스텀 페르소나"),
            ]
            
            # 고급 디코딩 옵션 (모든 모델 지원)
            advanced_fields = [
                ("top_k", "Top K"),
                ("typical_p", "Typical P"),
                ("repetition_penalty", "반복 억제"),
                ("no_repeat_ngram_size", "N-그램 반복 금지"),
                ("length_penalty", "길이 가중치"),
                ("min_new_tokens", "최소 토큰 수"),
                ("early_stopping", "조기 종료"),
                ("do_sample", "샘플링 활성화"),
                ("num_return_sequences", "후보 수"),
                ("seed", "시드"),
            ]
            
            # 변종별 특수 옵션
            variant_fields = []
            
            if "interleave" in name:
                # LLaVA-Interleave 전용 옵션 (멀티이미지 지원)
                variant_fields = [
                    ("multi_image_max", "멀티 이미지 최대"),
                    ("image_aspect_policy", "이미지 정책"),
                ]
            elif "next" in name or "1.6" in name:
                # LLaVA-NeXT/1.6 전용 옵션 (이미지 정책만)
                variant_fields = [
                    ("image_aspect_policy", "이미지 정책"),
                ]
            elif "vip" in name:
                # ViP-LLaVA 전용 옵션 (이미지 정책만)
                variant_fields = [
                    ("image_aspect_policy", "이미지 정책"),
                ]
            elif "llama-3" in name or "llama3" in name:
                # LLaVA-Llama-3 전용 옵션 (이미지 정책만)
                variant_fields = [
                    ("image_aspect_policy", "이미지 정책"),
                ]
            
            # 시스템 옵션 (모든 모델)
            system_fields = [
                ("offload_policy", "오프로드 정책"),
            ]
            
            return common_fields, advanced_fields, variant_fields, system_fields
        
        # 모델별 필드 가져오기
        common_fields, advanced_fields, variant_fields, system_fields = get_supported_fields(model_name)
        
        # 행별로 배치
        llava_fields_row1 = common_fields[:6]  # 기본 6개
        llava_fields_row2 = common_fields[6:] + advanced_fields[:2]  # 나머지 기본 + 고급 2개
        llava_fields_row3 = advanced_fields[2:]  # 나머지 고급 옵션들
        llava_fields_row4 = variant_fields + system_fields  # 변종별 + 시스템 옵션
        
        # 빈 행 제거
        all_rows = [llava_fields_row1, llava_fields_row2, llava_fields_row3, llava_fields_row4]
        non_empty_rows = [row for row in all_rows if row]
        
        # 행별로 배치
        for row_fields in non_empty_rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(2)
            
            # 각 행의 필드 생성
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
                
                # 입력 필드 생성
                value = llava_config.get(field_key, self._get_default_llava_config().get(field_key, ""))
                
                if field_key == "quantization_type":
                    # 양자화 타입 드롭다운
                    input_field = CustomComboBox()
                    input_field.addItems(["none", "4bit", "8bit", "FP16", "BF16", "FP32"])
                    input_field.setCurrentText(str(value) if value else "none")
                    input_field.setStyleSheet(common_combobox_style)
                elif field_key == "prompt_style":
                    # 프롬프트 스타일 드롭다운 (새로운 스타일들)
                    input_field = CustomComboBox()
                    input_field.addItems(["booru", "sentence_caption", "midjourney", "art_critic", "detailed", "brief", "custom"])
                    input_field.setCurrentText(str(value) if value else "sentence_caption")
                    input_field.setStyleSheet(common_combobox_style)
                elif field_key == "prompt_persona":
                    # 페르소나 드롭다운 (새로운 톤들)
                    input_field = CustomComboBox()
                    input_field.setEditable(True)  # 커스텀 입력 가능
                    input_field.addItems(["neutral", "professional", "friendly", "creative", "analytical", "casual", "custom"])
                    input_field.setCurrentText(str(value) if value else "neutral")
                    input_field.setStyleSheet(common_combobox_style)
                elif field_key == "custom_prompt":
                    # 커스텀 프롬프트 텍스트 필드
                    input_field = QLineEdit(str(value) if value else "")
                    input_field.setPlaceholderText("프롬프트 스타일이 'custom'일 때 사용됩니다")
                    input_field.setStyleSheet(f"""
                        QLineEdit {{
                            {common_input_style}
                        }}
                        QLineEdit:hover {{
                            {common_hover_style}
                        }}
                        QLineEdit:focus {{
                            {common_focus_style}
                        }}
                        QLineEdit::placeholder {{
                            color: #9CA3AF;
                        }}
                    """)
                elif field_key == "custom_persona":
                    # 커스텀 페르소나 텍스트 필드
                    input_field = QLineEdit(str(value) if value else "")
                    input_field.setPlaceholderText("페르소나가 'custom'일 때 사용됩니다")
                    input_field.setStyleSheet(f"""
                        QLineEdit {{
                            {common_input_style}
                        }}
                        QLineEdit:hover {{
                            {common_hover_style}
                        }}
                        QLineEdit:focus {{
                            {common_focus_style}
                        }}
                        QLineEdit::placeholder {{
                            color: #9CA3AF;
                        }}
                    """)
                elif field_key in ["max_tokens"]:
                    # 숫자 필드 - 스핀박스
                    input_field = CustomSpinBox()
                    input_field.setRange(1, 4096)  # 상한 확대 (1000 → 4096)
                    input_field.setValue(int(value) if value else 500)
                    input_field.setStyleSheet(f"""
                        QSpinBox {{
                            {common_input_style}
                        }}
                        QSpinBox:hover {{
                            {common_hover_style}
                        }}
                        QSpinBox:focus {{
                            {common_focus_style}
                        }}
                        QSpinBox::up-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QSpinBox::down-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QSpinBox::up-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                        QSpinBox::down-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                    """)
                elif field_key in ["num_beams"]:
                    # 빔 사이즈 필드 - 스핀박스
                    input_field = CustomSpinBox()
                    input_field.setRange(1, 8)  # 빔 사이즈 범위 (1-8)
                    input_field.setValue(int(value) if value else 1)
                    input_field.setStyleSheet(f"""
                        QSpinBox {{
                            {common_input_style}
                        }}
                        QSpinBox:hover {{
                            {common_hover_style}
                        }}
                        QSpinBox:focus {{
                            {common_focus_style}
                        }}
                        QSpinBox::up-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QSpinBox::down-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QSpinBox::up-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                        QSpinBox::down-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                    """)
                elif field_key in ["temperature"]:
                    # 실수 필드 - 더블 스핀박스
                    input_field = CustomDoubleSpinBox()
                    input_field.setRange(0.0, 2.0)
                    input_field.setSingleStep(0.1)
                    input_field.setDecimals(1)
                    input_field.setValue(float(value) if value else 0.1)
                    input_field.setStyleSheet(f"""
                        QDoubleSpinBox {{
                            {common_input_style}
                        }}
                        QDoubleSpinBox:hover {{
                            {common_hover_style}
                        }}
                        QDoubleSpinBox:focus {{
                            {common_focus_style}
                        }}
                        QDoubleSpinBox::up-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QDoubleSpinBox::down-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QDoubleSpinBox::up-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                        QDoubleSpinBox::down-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                    """)
                elif field_key in ["top_p"]:
                    # 실수 필드 - 더블 스핀박스
                    input_field = CustomDoubleSpinBox()
                    input_field.setRange(0.0, 1.0)
                    input_field.setSingleStep(0.05)  # 정밀도 향상 (0.1 → 0.05)
                    input_field.setDecimals(2)  # 소수점 자리 확대 (1 → 2)
                    input_field.setValue(float(value) if value else 0.9)
                    input_field.setStyleSheet(f"""
                        QDoubleSpinBox {{
                            {common_input_style}
                        }}
                        QDoubleSpinBox:hover {{
                            {common_hover_style}
                        }}
                        QDoubleSpinBox:focus {{
                            {common_focus_style}
                        }}
                        QDoubleSpinBox::up-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QDoubleSpinBox::down-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QDoubleSpinBox::up-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                        QDoubleSpinBox::down-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                    """)
                elif field_key in ["use_flash_attention"]:
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
                                
                                # 체크 표시 그리기
                                painter.setPen(QPen(QColor("#FFFFFF"), 2))
                                painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
                                
                                # 체크박스 영역 계산
                                rect = self.rect()
                                indicator_rect = QRect(1, (rect.height() - 14) // 2, 14, 14)
                                
                                # 체크 표시 (🗸) 그리기
                                painter.drawText(indicator_rect, Qt.AlignCenter, "🗸")
                    
                    # 체크박스 필드
                    input_field = CustomCheckBox()
                    input_field.setChecked(bool(value))
                elif field_key in ["top_k", "min_new_tokens", "no_repeat_ngram_size", "multi_image_max", "num_return_sequences", "seed"]:
                    # 정수 입력 필드
                    input_field = CustomSpinBox()
                    if field_key == "top_k":
                        input_field.setRange(1, 100)
                        input_field.setValue(int(value) if value is not None else 50)
                    elif field_key == "min_new_tokens":
                        input_field.setRange(1, 100)
                        input_field.setValue(int(value) if value is not None else 1)
                    elif field_key == "no_repeat_ngram_size":
                        input_field.setRange(0, 10)
                        input_field.setValue(int(value) if value is not None else 0)
                    elif field_key == "multi_image_max":
                        input_field.setRange(1, 10)
                        input_field.setValue(int(value) if value is not None else 4)
                    elif field_key == "num_return_sequences":
                        input_field.setRange(1, 5)
                        input_field.setValue(int(value) if value is not None else 1)
                    elif field_key == "seed":
                        input_field.setRange(-1, 2147483647)  # -1은 랜덤, 최대 int32
                        input_field.setValue(int(value) if value is not None else -1)
                    input_field.setStyleSheet(f"""
                        QSpinBox {{
                            {common_input_style}
                        }}
                        QSpinBox:hover {{
                            {common_hover_style}
                        }}
                        QSpinBox:focus {{
                            {common_focus_style}
                        }}
                        QSpinBox::up-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QSpinBox::down-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QSpinBox::up-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                        QSpinBox::down-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                    """)
                elif field_key in ["typical_p", "repetition_penalty", "length_penalty"]:
                    # 실수 입력 필드
                    input_field = CustomDoubleSpinBox()
                    if field_key == "typical_p":
                        input_field.setRange(0.0, 1.0)
                        input_field.setDecimals(2)
                        input_field.setSingleStep(0.05)
                        input_field.setValue(float(value) if value is not None else 0.0)
                    elif field_key == "repetition_penalty":
                        input_field.setRange(0.1, 2.0)
                        input_field.setDecimals(2)
                        input_field.setSingleStep(0.1)
                        input_field.setValue(float(value) if value is not None else 1.0)
                    elif field_key == "length_penalty":
                        input_field.setRange(0.0, 5.0)
                        input_field.setDecimals(2)
                        input_field.setSingleStep(0.1)
                        input_field.setValue(float(value) if value is not None else 1.0)
                    input_field.setStyleSheet(f"""
                        QDoubleSpinBox {{
                            {common_input_style}
                        }}
                        QDoubleSpinBox:hover {{
                            {common_hover_style}
                        }}
                        QDoubleSpinBox:focus {{
                            {common_focus_style}
                        }}
                        QDoubleSpinBox::up-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QDoubleSpinBox::down-button {{
                            background: transparent;
                            border: none;
                            width: 20px;
                        }}
                        QDoubleSpinBox::up-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                        QDoubleSpinBox::down-arrow {{
                            image: none;
                            border: none;
                            background: transparent;
                            width: 0px;
                            height: 0px;
                        }}
                    """)
                elif field_key in ["device_map", "torch_dtype", "offload_policy", "image_aspect_policy"]:
                    # 선택 가능한 값이 있는 드롭다운
                    input_field = CustomComboBox()
                    if field_key == "device_map":
                        input_field.addItems(["auto", "cpu", "cuda", "cuda:0", "cuda:1"])
                    elif field_key == "torch_dtype":
                        input_field.addItems(["auto", "float16", "float32", "bfloat16"])
                    elif field_key == "offload_policy":
                        input_field.addItems(["auto", "cpu", "disk", "none"])
                    elif field_key == "image_aspect_policy":
                        input_field.addItems(["auto", "pad", "resize", "crop"])
                    input_field.setCurrentText(str(value) if value else "auto")
                    input_field.setStyleSheet(common_combobox_style)
                elif field_key in ["early_stopping", "do_sample"]:
                    # 불린 값 드롭다운
                    input_field = CustomComboBox()
                    input_field.addItems(["auto", "true", "false"])
                    if value is True:
                        input_field.setCurrentText("true")
                    elif value is False:
                        input_field.setCurrentText("false")
                    else:
                        input_field.setCurrentText("auto")
                    input_field.setStyleSheet(common_combobox_style)
                elif field_key in ["eos_token_id", "pad_token_id", "max_memory"]:
                    # 토큰 ID나 메모리 설정 (텍스트 입력)
                    input_field = QLineEdit(str(value) if value else "")
                    if field_key == "max_memory":
                        input_field.setPlaceholderText("예: 8GB, 4096MB")
                    else:
                        input_field.setPlaceholderText("토큰 ID (숫자)")
                    input_field.setStyleSheet(f"""
                        QLineEdit {{
                            {common_input_style}
                        }}
                        QLineEdit:hover {{
                            {common_hover_style}
                        }}
                        QLineEdit:focus {{
                            {common_focus_style}
                        }}
                        QLineEdit::placeholder {{
                            color: #9CA3AF;
                        }}
                    """)
                else:
                    # 기본 텍스트 입력 필드
                    input_field = QLineEdit(str(value) if value is not None else "")
                    input_field.setStyleSheet(f"""
                        QLineEdit {{
                            {common_input_style}
                        }}
                        QLineEdit:hover {{
                            {common_hover_style}
                        }}
                        QLineEdit:focus {{
                            {common_focus_style}
                        }}
                        QLineEdit::placeholder {{
                            color: #9CA3AF;
                        }}
                    """)
                
                # 인스턴스 변수로 저장
                setattr(self, f"{field_key}_input", input_field)
                
                field_container.addWidget(input_field)
                
                # 필드 컨테이너를 행 레이아웃에 추가
                field_widget = QWidget()
                field_widget.setLayout(field_container)
                row_layout.addWidget(field_widget)
            
            # 행을 메인 레이아웃에 추가
            layout.addLayout(row_layout)
    
    def save_llava_config(self, model_name=None):
        """LLaVA 설정 저장"""
        print(f"[DEBUG] LLaVA 설정 저장: {model_name}")
        
        try:
            # 모든 필드 값 수집
            field_values = {}
            
            # 모델별 지원 필드만 수집
            def get_supported_field_keys(model_name):
                name = (model_name or "").lower()
                
                # 공통 기본 필드
                common_keys = [
                    "max_tokens", "temperature", "top_p", "num_beams", "quantization_type", "use_flash_attention",
                    "prompt_style", "prompt_persona", "custom_prompt", "custom_persona"
                ]
                
                # 고급 디코딩 필드
                advanced_keys = [
                    "top_k", "typical_p", "repetition_penalty", "no_repeat_ngram_size", "length_penalty", "min_new_tokens", "early_stopping", "do_sample", "num_return_sequences", "seed"
                ]
                
                # 변종별 특수 필드
                variant_keys = []
                if "interleave" in name:
                    variant_keys = ["multi_image_max", "image_aspect_policy"]
                elif "next" in name or "1.6" in name or "vip" in name or "llama-3" in name or "llama3" in name:
                    variant_keys = ["image_aspect_policy"]
                
                # 시스템 필드
                system_keys = ["offload_policy"]
                
                return common_keys + advanced_keys + variant_keys + system_keys
            
            # 모델별 지원 필드만 가져오기
            llava_fields = get_supported_field_keys(model_name)
            
            for field_key in llava_fields:
                input_attr_name = f"{field_key}_input"
                if hasattr(self, input_attr_name):
                    widget = getattr(self, input_attr_name)
                    if isinstance(widget, QCheckBox):
                        value = widget.isChecked()
                    elif isinstance(widget, (QSpinBox, CustomSpinBox)):
                        value = widget.value()
                    elif isinstance(widget, (QDoubleSpinBox, CustomDoubleSpinBox)):
                        value = widget.value()
                    elif isinstance(widget, (QComboBox, CustomComboBox)):
                        text = widget.currentText()
                        # 불린 값 드롭다운 특별 처리
                        if field_key in ["early_stopping", "do_sample"]:
                            if text == "true":
                                value = True
                            elif text == "false":
                                value = False
                            else:  # "auto"
                                value = None
                        else:
                            value = text
                    elif isinstance(widget, QLineEdit):
                        text = widget.text().strip()
                        if not text:
                            value = None
                        elif text.lower() in ['true', 'false']:
                            value = text.lower() == 'true'
                        elif text.isdigit():
                            value = int(text)
                        elif text.replace('.', '').isdigit():
                            value = float(text)
                        else:
                            value = text
                    else:
                        continue
                    
                    field_values[field_key] = value
            
            # 설정 저장 (모델명 기반)
            success = self._save_llava_config_to_file(field_values, model_name=model_name)
            if success:
                print("✅ LLaVA 설정 저장 완료")
                return True
            else:
                print("❌ LLaVA 설정 저장 실패")
                return False
                
        except Exception as e:
            print(f"❌ LLaVA 설정 저장 실패: {str(e)}")
            return False