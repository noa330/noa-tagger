# -*- coding: utf-8 -*-
"""
Miracle Manager Module - 미라클 매니저 모듈 (배치 작업 전용)
- 단일 작업 로직은 miracle_manager_single.py로 이동됨
"""

from PySide6.QtWidgets import (QPushButton, QLineEdit, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QFrame)
from PySide6.QtCore import Signal, Qt, QTimer, QEvent
from PySide6.QtGui import QFont

import os
import traceback
from pathlib import Path

# 미라클 설정 모듈
from miracle_settings_module import MiracleSettingsModule

# 단일 작업 로직 임포트
from miracle_manager_single import (
    CustomSpinBox,
    process_miracle_command_async,
    on_miracle_finished,
    on_miracle_error,
    process_miracle_command,
    apply_tag_moves,
    apply_tag_renames,
    validate_tags,
    get_allowed_tags,
    get_tag_categories,
    validate_single_tag,
    compose_message,
    get_current_grid_images,
    apply_miracle_tags_to_ui,
    apply_tags_to_single_image,
    get_current_image_path,
    get_current_image_name,
    interpret_natural_language_with_ai,
    call_google_ai_api_with_image,
    get_current_image_tags
)

# 배치 작업 로직 임포트
from miracle_manager_batch import (
    BatchWorker,
    on_batch_progress,
    on_batch_finished,
    apply_tags_to_multiple_images,
    create_image_tag_mapping,
    _build_simple_to_actual_name_map,
    postprocess_ai_response_for_batch_display,
    call_google_ai_api_with_multiple_images,
    parse_multi_image_response
)

# Google API 키는 miracle_manager_single에서 임포트됨
# CustomSpinBox는 miracle_manager_single에서 임포트됨


class AIResponseOverlay(QWidget):
    pass

class MiracleManagerButton(QPushButton):
    """미라클 매니저 버튼 클래스"""

    # 시그널 정의
    miracle_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_button()

    def setup_button(self):
        """버튼 설정"""
        self.setText("✨")
        self.setFixedSize(60, 50)
        self.setToolTip("Miracle Manager")
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #CFD8DC;
                border: none;
                font-size: 18px;
                text-decoration: none;
                outline: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.2);
            }
        """)

        # 클릭 시그널 연결
        self.clicked.connect(self.miracle_clicked.emit)

    def get_miracle_button(self):
        """미라클 매니저 버튼 반환"""
        return self


class MiracleTagInput(QWidget):
    """미라클 태그 입력 위젯 - 기존 ModernTagInput과 동일한 크기와 디자인"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.llava_model_cache = {}  # (HF 경로는 더 이상 사용하지 않지만, 인터페이스 유지)
        self.ai_response_message = None  # AI 응답 메시지 저장
        self.ai_overlay = None  # AI 응답 오버레이
        self._input_height_locked = False  # 입력창 높이 고정 여부
        self.miracle_settings = None  # 미라클 설정 모듈
        self.setup_ui()

    def setup_ui(self):
        """미라클 UI 설정 - 기존과 동일한 레이아웃과 크기"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 미라클 태그 입력 필드
        self.miracle_tag_input = QLineEdit()
        self.miracle_tag_input.setPlaceholderText("미라클 태그 추가...")
        # 스타일은 모드에 따라 동적으로 적용됨 (apply_outline_styles)
        layout.addWidget(self.miracle_tag_input)
        # 첫 포커스 시 현재 높이로 자동 고정 (엔터 후 수축 방지)
        try:
            self.miracle_tag_input.installEventFilter(self)
        except Exception:
            pass

        # 숨김 트리거 버튼(유지)
        from PySide6.QtWidgets import QPushButton
        self.miracle_trigger_btn = QPushButton("미라클")
        self.miracle_trigger_btn.setFlat(True)
        self.miracle_trigger_btn.setFixedSize(60, 36)
        self.miracle_trigger_btn.setCursor(Qt.PointingHandCursor)
        self.miracle_trigger_btn.setToolTip("미라클 모드 토글")
        self.miracle_trigger_btn.setCheckable(True)
        self.miracle_trigger_btn.setChecked(False)
        self.miracle_trigger_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #6B7280, stop:1 #4B5563);
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 11px;
                font-weight: 500;
                padding: 0px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #9CA3AF, stop:1 #6B7280);
                color: white;
                padding: 0px 12px;
            }
            QPushButton:checked {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #8B5CF6, stop:1 #7C3AED);
                color: white;
                padding: 0px 12px;
            }
            QPushButton:checked:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #A78BFA, stop:1 #8B5CF6);
                padding: 0px 12px;
            }
            QPushButton:pressed {
                padding: 0px 12px;
            }
        """)
        self.miracle_trigger_btn.hide()
        layout.addWidget(self.miracle_trigger_btn)

        # 미라클 개별/일괄 토글 버튼
        self.miracle_mode_btn = QPushButton("미라클 개별")
        self.miracle_mode_btn.setFlat(True)
        self.miracle_mode_btn.setFixedSize(118, 36)
        self.miracle_mode_btn.setCursor(Qt.PointingHandCursor)
        self.miracle_mode_btn.setToolTip("미라클 개별/일괄 입력 모드 토글")
        self.miracle_mode_btn.setCheckable(True)
        self.miracle_mode_btn.setChecked(False)
        self.miracle_mode_btn.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 18px;
                font-size: 12px;
                font-weight: 700;
                padding: 0px 12px;
            }
            QPushButton:hover {
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:checked {
                background: #2D3748;
                border-color: #2D3748;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:checked:hover {
                background: #1A202C;
                border-color: #1A202C;
                color: #CBD5E0;
                padding: 0px 12px;
            }
            QPushButton:pressed {
                padding: 0px 12px;
            }
        """)
        # 배치 사이즈 스핀박스 (일괄 모드에서 한 번에 보낼 이미지 수) - 토글 버튼의 왼쪽에 배치
        try:
            from PySide6.QtWidgets import QSpinBox
            self.batch_size_spin = CustomSpinBox()
            self.batch_size_spin.setMinimum(2)
            self.batch_size_spin.setMaximum(999)
            self.batch_size_spin.setValue(2)
            # 텍스트 입력 필드 높이에 맞춰 스핀박스 높이 통일
            try:
                target_h = int(self.miracle_tag_input.sizeHint().height())
                self.batch_size_spin.setFixedHeight(target_h)
            except Exception:
                pass
            self.batch_size_spin.setFixedWidth(72)
            self.batch_size_spin.setToolTip("일괄 모드 배치 크기(한 번에 보낼 이미지 수)")
            # 스타일은 모드에 따라 동적으로 적용됨 (apply_outline_styles)
            self.batch_size_spin.hide()
            layout.addWidget(self.batch_size_spin)
        except Exception:
            self.batch_size_spin = None

        self.miracle_mode_btn.clicked.connect(self.toggle_miracle_mode)
        layout.addWidget(self.miracle_mode_btn)

        # 미라클 설정 버튼 (톱니바퀴)
        self.miracle_settings_btn = QPushButton("⚙️")
        self.miracle_settings_btn.setFlat(True)
        self.miracle_settings_btn.setFixedSize(36, 36)
        self.miracle_settings_btn.setCursor(Qt.PointingHandCursor)
        self.miracle_settings_btn.setToolTip("미라클 설정 (API 키 관리)")
        self.miracle_settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9CA3AF;
                border: none;
                border-radius: 18px;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(156,163,175,0.2);
                color: #F3F4F6;
            }
            QPushButton:pressed {
                background: rgba(156,163,175,0.3);
                color: #FFFFFF;
            }
        """)
        self.miracle_settings_btn.clicked.connect(self.open_miracle_settings)
        layout.addWidget(self.miracle_settings_btn)

        # 엔터키로 실행
        self.miracle_tag_input.returnPressed.connect(self.run_miracle_inference)
        # 엔터 직전에도 높이 고정
        try:
            self.miracle_tag_input.returnPressed.connect(self.lock_input_height)
        except Exception:
            pass

        # app_instance 참조
        self.app_instance = None

        # 초기 윤곽선 스타일 적용 (단일 기본: 파랑)
        try:
            self.apply_outline_styles()
        except Exception:
            pass
    
    def open_miracle_settings(self):
        """미라클 설정 창 열기"""
        try:
            if not self.miracle_settings:
                self.miracle_settings = MiracleSettingsModule(self.app_instance)
            self.miracle_settings.open_settings()
        except Exception as e:
            print(f"미라클 설정 열기 오류: {e}")
            import traceback
            traceback.print_exc()

    def eventFilter(self, obj, event):
        try:
            if obj is self.miracle_tag_input:
                if (event.type() == QEvent.FocusIn) and not self._input_height_locked:
                    self.lock_input_height()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def lock_input_height(self):
        """현재 입력창 높이를 고정하여 엔터 후 수축을 방지"""
        try:
            if self._input_height_locked:
                return
            h = int(self.miracle_tag_input.sizeHint().height() or self.miracle_tag_input.height() or 0)
            if h > 0:
                self.miracle_tag_input.setMinimumHeight(h)
                self.miracle_tag_input.setMaximumHeight(h)
                self._input_height_locked = True
        except Exception:
            pass

    def apply_outline_styles(self):
        """모드에 따라 입력/스핀박스 윤곽선을 통일 적용 (단일: 파랑, 배치: 초록)"""
        try:
            is_batch = bool(self.miracle_mode_btn.isChecked())
        except Exception:
            is_batch = False
        border_color = "#22c55e" if is_batch else "#3B82F6"
        # 입력창 스타일
        try:
            self.miracle_tag_input.setStyleSheet(f"""
                QLineEdit {{
                    background: rgba(26,27,38,0.8);
                    color: #F9FAFB;
                    border: 2px solid {border_color};
                    font-size: 12px;
                }}
                QLineEdit:focus {{
                    border: 2px solid {border_color};
                    background: rgba(26,27,38,0.9);
                }}
                QLineEdit:hover {{
                    border: 2px solid {border_color};
                    background: rgba(26,27,38,0.85);
                }}
            """)
        except Exception:
            pass
        # 배치 사이즈 스핀박스 스타일
        try:
            if hasattr(self, 'batch_size_spin') and self.batch_size_spin:
                # 높이 재동기화 (입력 필드 높이에 맞춤)
                try:
                    target_h = int(self.miracle_tag_input.sizeHint().height())
                    self.batch_size_spin.setFixedHeight(target_h)
                except Exception:
                    pass
                self.batch_size_spin.setStyleSheet(f"""
                    QSpinBox {{
                        background: rgba(26,27,38,0.8);
                        color: #F9FAFB;
                        border: 2px solid {border_color};
                        font-size: 12px;
                        min-width: 60px;
                    }}
                    QSpinBox:focus {{
                        border: 2px solid {border_color};
                        background: rgba(26,27,38,0.9);
                    }}
                    /* 기본 버튼 영역은 투명하게 유지 (화살표는 paintEvent로 그림) */
                    QSpinBox::up-button, QSpinBox::down-button {{
                        width: 20px; border: none; background: transparent; margin: 0; padding: 0;
                    }}
                    /* 기본 이미지 화살표는 숨김 (텍스트 화살표만 표시) */
                    QSpinBox::up-arrow, QSpinBox::down-arrow {{
                        image: none; width: 0px; height: 0px; border: none; background: transparent; margin: 0; padding: 0;
                    }}
                """)
        except Exception:
            pass

    def toggle_miracle_mode(self):
        """미라클 개별/일괄 모드 토글"""
        if self.miracle_mode_btn.isChecked():
            self.miracle_mode_btn.setText("미라클 일괄")
            self.miracle_mode_btn.setToolTip("미라클 일괄 입력 모드")
            # 배치 사이즈 컨트롤 표시
            if hasattr(self, 'batch_size_spin') and self.batch_size_spin:
                self.batch_size_spin.show()
            # 배치 스타일(초록) 적용
            try:
                self.apply_outline_styles()
            except Exception:
                pass
        else:
            self.miracle_mode_btn.setText("미라클 개별")
            self.miracle_mode_btn.setToolTip("미라클 개별 입력 모드")
            # 배치 사이즈 컨트롤 숨김
            if hasattr(self, 'batch_size_spin') and self.batch_size_spin:
                self.batch_size_spin.hide()
            # 단일 스타일(파랑) 적용
            try:
                self.apply_outline_styles()
            except Exception:
                pass

    def get_batch_size(self):
        try:
            if hasattr(self, 'batch_size_spin') and self.batch_size_spin:
                v = int(self.batch_size_spin.value())
                return max(1, min(999, v))
        except Exception:
            pass
        return 10

    def show_loading_indicator(self, message="처리 중..."):
        """로딩 상태 표시 (UI 스로틀링 방지)"""
        try:
            if hasattr(self, 'miracle_manager') and self.miracle_manager:
                # 우측 응답 섹션에 로딩 메시지 표시
                self.miracle_manager.update_right_response(f"⏳ {message}")
        except Exception as e:
            print(f"로딩 인디케이터 표시 중 오류: {e}")

    def hide_loading_indicator(self):
        """로딩 상태 숨김"""
        try:
            # 로딩 메시지는 AI 응답으로 자동 대체됨
            pass
        except Exception as e:
            print(f"로딩 인디케이터 숨김 중 오류: {e}")

    def start_miracle_progress(self, total=1, prefix="미라클 태깅 중..."):
        """미라클 명령 실행 시 태깅 진행 표시 시작"""
        app = getattr(self, 'app_instance', None)
        if not app:
            return
        try:
            total = int(total)
        except Exception:
            total = 1
        total = max(1, total)
        self._miracle_progress_total = total
        self._miracle_progress_current = 0
        self._miracle_progress_prefix = prefix or "미라클 태깅 중..."
        self._miracle_progress_active = True
        try:
            if hasattr(app, 'ai_progress_label') and app.ai_progress_label:
                app.ai_progress_label.setText(f"{self._miracle_progress_prefix} (0/{total})")
                app.ai_progress_label.show()
            if hasattr(app, 'ai_progress_bar') and app.ai_progress_bar:
                app.ai_progress_bar.setMaximum(total)
                app.ai_progress_bar.setValue(0)
                app.ai_progress_bar.show()
        except Exception as e:
            print(f"[MiracleProgress] 표시 시작 오류: {e}")

    def increment_miracle_progress(self, step=1):
        """태깅 진행률을 증가시켜 갱신"""
        if not getattr(self, '_miracle_progress_active', False):
            return
        app = getattr(self, 'app_instance', None)
        if not app:
            return
        try:
            step = int(step)
        except Exception:
            step = 1
        if not hasattr(self, '_miracle_progress_total'):
            return
        total = max(1, int(getattr(self, '_miracle_progress_total', 1)))
        current = max(0, int(getattr(self, '_miracle_progress_current', 0))) + max(0, step)
        if current > total:
            current = total
        self._miracle_progress_current = current
        prefix = getattr(self, '_miracle_progress_prefix', "미라클 태깅 중...")
        try:
            if hasattr(app, 'ai_progress_label') and app.ai_progress_label:
                app.ai_progress_label.setText(f"{prefix} ({current}/{total})")
                app.ai_progress_label.show()
            if hasattr(app, 'ai_progress_bar') and app.ai_progress_bar:
                app.ai_progress_bar.setMaximum(total)
                app.ai_progress_bar.setValue(current)
                app.ai_progress_bar.show()
        except Exception as e:
            print(f"[MiracleProgress] 진행 갱신 오류: {e}")

    def complete_miracle_progress(self):
        """미라클 태깅 진행 표시 종료"""
        if not getattr(self, '_miracle_progress_active', False):
            return
        app = getattr(self, 'app_instance', None)
        if not app:
            return
        try:
            if hasattr(self, '_miracle_progress_total'):
                total = max(1, int(getattr(self, '_miracle_progress_total', 1)))
                self._miracle_progress_current = total
                prefix = getattr(self, '_miracle_progress_prefix', "미라클 태깅 중...")
                if hasattr(app, 'ai_progress_label') and app.ai_progress_label:
                    app.ai_progress_label.setText(f"{prefix} ({total}/{total})")
            if hasattr(app, 'ai_progress_label') and app.ai_progress_label:
                app.ai_progress_label.hide()
            if hasattr(app, 'ai_progress_bar') and app.ai_progress_bar:
                app.ai_progress_bar.hide()
        except Exception as e:
            print(f"[MiracleProgress] 종료 처리 오류: {e}")
        finally:
            self._miracle_progress_active = False

    # 단일 작업 로직은 miracle_manager_single 모듈로 이동됨
    # 배치 작업 로직은 miracle_manager_batch 모듈로 이동됨
    # BatchWorker는 miracle_manager_batch에서 임포트됨

    def on_batch_progress(self, data: dict):
        """배치 프로그레스 수신 슬롯 - miracle_manager_batch 모듈의 함수 사용"""
        return on_batch_progress(self, data)

    def on_batch_finished(self):
        """배치 종료 슬롯 - miracle_manager_batch 모듈의 함수 사용"""
        return on_batch_finished(self)
    
    def on_miracle_finished(self, result):
        """미라클 처리 완료 시 호출 - 배치 작업만 처리"""
        try:
            import json
            print(f"✨ Miracle Manager: 처리 결과 - {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 배치 모드 확인
            is_batch_mode = False
            try:
                is_batch_mode = bool(self.miracle_mode_btn.isChecked()) and len(get_current_grid_images(self)) > 1
            except Exception:
                is_batch_mode = False

            if is_batch_mode:
                # 배치 모드: BatchWorker로 비동기 배치 해석 시작
                try:
                    # 새 배치 시작 전, 기존 윤곽선 제거 및 실패 정보 초기화
                    try:
                        if hasattr(self.app_instance, 'miracle_manager') and hasattr(self.app_instance.miracle_manager, 'clear_right_response_borders'):
                            self.app_instance.miracle_manager.clear_right_response_borders()
                        # 실패 정보 초기화 (새 배치 시작 시)
                        if hasattr(self.app_instance, 'miracle_manager'):
                            self.app_instance.miracle_manager._failed_batch_info = None
                    except Exception:
                        pass
                    # 다중선택된 이미지들이 있으면 우선 사용
                    from search_filter_grid_module import get_multi_selected_images
                    multi_selected_images = get_multi_selected_images(self.app_instance)
                    if multi_selected_images:
                        target_images = multi_selected_images
                        print(f"✨ Miracle Manager: 다중선택된 이미지 {len(target_images)}개에 배치 처리 적용")
                    else:
                        target_images = get_current_grid_images(self)
                    batch_size = self.get_batch_size() if hasattr(self, 'get_batch_size') else 10
                    try:
                        if target_images:
                            self.start_miracle_progress(len(target_images))
                        else:
                            self.start_miracle_progress(1)
                    except Exception as prog_err:
                        print(f"[MiracleProgress] 배치 진행 초기화 실패: {prog_err}")
                    from PySide6.QtCore import QThread
                    self.batch_thread = QThread()
                    self.batch_worker = BatchWorker(result.get("command", ""), target_images, batch_size, self)
                    self.batch_worker.moveToThread(self.batch_thread)
                    self.batch_thread.started.connect(self.batch_worker.run)
                    self.batch_worker.progress.connect(self.on_batch_progress)
                    self.batch_worker.finished.connect(self.on_batch_finished)
                    # 정리 연결
                    self.batch_worker.finished.connect(self.batch_thread.quit)
                    self.batch_thread.finished.connect(self.batch_thread.deleteLater)
                    self.batch_worker.finished.connect(self.batch_worker.deleteLater)
                    self.batch_thread.start()
                except Exception as _e:
                    print(f"✨ Miracle Manager: 배치 워커 시작 실패 - {_e}")
                return
            else:
                # 단일 모드: miracle_manager_single 모듈의 함수 사용
                on_miracle_finished(self, result)
                
        except Exception as e:
            print(f"✨ Miracle Manager: 처리 완료 후 오류 - {e}")
            on_miracle_finished(self, result)
    
    def on_miracle_error(self, error_msg):
        """미라클 처리 오류 시 호출 - miracle_manager_single 모듈의 함수 사용"""
        on_miracle_error(self, error_msg)

    def run_miracle_inference(self):
        """미라클 추론 실행 - 명령어 파싱 및 태그 처리"""
        user_input = self.miracle_tag_input.text().strip()
        if not user_input:
            return

        # 새로운 질문이 들어오면 재시도 버튼 제거
        try:
            if hasattr(self.app_instance, 'miracle_manager'):
                mm = self.app_instance.miracle_manager
                if hasattr(mm, 'remove_retry_button'):
                    mm.remove_retry_button()
        except Exception as e:
            print(f"재시도 버튼 제거 중 오류: {e}")

        # 미라클 모드가 활성화되어 있는지 확인
        is_miracle_active = False
        try:
            if hasattr(self.app_instance, 'miracle_manager'):
                is_miracle_active = getattr(self.app_instance.miracle_manager, 'is_miracle_mode', False)
        except Exception as e:
            print(f"미라클 모드 상태 확인 중 오류: {e}")
        
        if not is_miracle_active:
            result = {
                "version": "v1",
                "ok": False,
                "reason": "miracle-mode-off",
                "command": user_input,
                "targets_count": 0,
                "targets": None,
                "add": [],
                "dilet": [],
                "rejected": {},
                "notes": ["미라클 모드가 비활성화되어 처리하지 않았습니다."],
                "flat": "",
                "message": "미라클 모드가 꺼져 있어 적용하지 않았습니다."
            }
            print(f"✨ Miracle Manager: 미라클 모드 비활성화 - {result}")
            self.miracle_tag_input.clear()
            return

        print(f"✨ Miracle Manager: 명령어 처리 - '{user_input}'")
        # 중복 실행 방지
        if getattr(self, '_miracle_busy', False):
            print("✨ Miracle Manager: 아직 이전 작업이 진행 중입니다. 요청을 무시합니다.")
            return
        self._miracle_busy = True
        
        # 로딩 상태 표시
        self.show_loading_indicator("AI 분석 중...")
        
        # 처리 중 UI 비활성화
        self.miracle_tag_input.setEnabled(False)
        self.miracle_tag_input.setPlaceholderText("AI 분석 중... 잠시만 기다려주세요")
        self.miracle_tag_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                color: #888888;
                border: 2px solid #4CAF50;
                font-size: 12px;
            }
        """)
        
        # miracle_manager_single 모듈의 함수 사용
        process_miracle_command_async(self, user_input)

    def process_miracle_command(self, command):
        """미라클 명령어 파싱 및 처리 - miracle_manager_single 모듈의 함수 사용"""
        # 단일 작업 로직은 miracle_manager_single 모듈로 이동됨
        return process_miracle_command(self, command)

    def apply_tag_moves(self, tag_moves):
        """태그 위치 조작 수행 - miracle_manager_single 모듈의 함수 사용"""
        return apply_tag_moves(self, tag_moves)
    
    def apply_tag_renames(self, renames):
        """태그 이름 변경 수행 - miracle_manager_single 모듈의 함수 사용"""
        return apply_tag_renames(self, renames)

    def show_ai_response_overlay(self, response_text):
        return

    def validate_tags(self, add_tags, dilet_tags):
        """태그 검증 - miracle_manager_single 모듈의 함수 사용"""
        return validate_tags(self, add_tags, dilet_tags)

    def get_allowed_tags(self):
        """태그 트리에서 허용 가능한 태그들 가져오기 - miracle_manager_single 모듈의 함수 사용"""
        return get_allowed_tags(self)

    def get_tag_categories(self):
        """태그 카테고리들 가져오기 - miracle_manager_single 모듈의 함수 사용"""
        return get_tag_categories(self)

    def validate_single_tag(self, tag, allowed_tags, categories):
        """단일 태그 유효성 검사 - miracle_manager_single 모듈의 함수 사용"""
        return validate_single_tag(tag, allowed_tags, categories)

    def compose_message(self, reason, add_final, dilet_ok, targets_count, rejected):
        """자연어 메시지 생성 - miracle_manager_single 모듈의 함수 사용"""
        return compose_message(reason, add_final, dilet_ok, targets_count, rejected)

    def get_current_grid_images(self):
        """현재 선택된 이미지 목록 가져오기 - miracle_manager_single 모듈의 함수 사용"""
        return get_current_grid_images(self)

    def apply_miracle_tags_to_ui(self, result):
        """미라클 결과를 실제 UI에 반영 - miracle_manager_single 모듈의 함수 사용"""
        return apply_miracle_tags_to_ui(self, result)

    def apply_tags_to_single_image(self, image_path, add_tags, dilet_tags):
        """단일 이미지에 태그 적용 - miracle_manager_single 모듈의 함수 사용"""
        return apply_tags_to_single_image(self, image_path, add_tags, dilet_tags)

    def apply_tags_to_multiple_images(self, image_paths, add_tags, dilet_tags, tag_renames=None):
        """다중 이미지에 태그 적용 - miracle_manager_batch 모듈의 함수 사용"""
        return apply_tags_to_multiple_images(self, image_paths, add_tags, dilet_tags, tag_renames)

    def create_image_tag_mapping(self, image_paths, add_tags, dilet_tags):
        """AI 응답에서 각 이미지별 태그 매핑 생성 - miracle_manager_batch 모듈의 함수 사용"""
        return create_image_tag_mapping(self, image_paths, add_tags, dilet_tags)

    def update_ui_after_tag_changes(self):
        """태그 변경 후 UI 업데이트"""
        try:
            if hasattr(self.app_instance, 'update_current_tags_display'):
                self.app_instance.update_current_tags_display()

            # 태그 통계 + 트리까지 한 번에 정리되는 경로
            if hasattr(self.app_instance, 'update_tag_stats'):
                self.app_instance.update_tag_stats()

            # 안전망: 트리를 명시적으로 다시
            if hasattr(self.app_instance, 'update_tag_tree'):
                self.app_instance.update_tag_tree()

            # 스타일시트 에디터 열려있으면 동기화
            if hasattr(self.app_instance, 'tag_stylesheet_editor') and self.app_instance.tag_stylesheet_editor:
                self.app_instance.tag_stylesheet_editor.schedule_update()

            print("✨ Miracle Manager: UI 업데이트 완료")
        except Exception as e:
            print(f"✨ Miracle Manager: UI 업데이트 중 오류 - {e}")

    def get_current_image_path(self):
        """현재 이미지 경로 가져오기 - miracle_manager_single 모듈의 함수 사용"""
        return get_current_image_path(self)

    def get_current_image_name(self):
        """현재 이미지의 파일명 가져오기 - miracle_manager_single 모듈의 함수 사용"""
        return get_current_image_name(self)

    def interpret_natural_language_with_ai(self, command, is_batch_mode=False, target_images=None):
        """자연어 명령어를 AI 모델로 해석 - miracle_manager_single 모듈의 함수 사용 (배치/단일 통합)"""
        # 배치 모드일 때는 call_google_ai_api_with_multiple_images를 직접 호출
        # 단일 모드일 때는 miracle_manager_single 모듈의 interpret_natural_language_with_ai를 호출
        num_images = len(target_images) if target_images else 0
        print(f"✨ Miracle Manager Module: interpret_natural_language_with_ai 호출 - is_batch_mode={is_batch_mode}, 이미지 수={num_images}")
        
        if is_batch_mode and target_images and len(target_images) > 1:
            # 배치 모드: call_google_ai_api_with_multiple_images 직접 호출
            print(f"✨ Miracle Manager Module: 배치 모드로 처리 (다중 이미지 프롬프트)")
            prompt = f'사용자 명령어: "{command}"'
            return call_google_ai_api_with_multiple_images(self, prompt, target_images)
        else:
            # 단일 모드: miracle_manager_single 모듈 함수 호출
            print(f"✨ Miracle Manager Module: 단일 모드로 처리 (개별 프롬프트)")
            return interpret_natural_language_with_ai(self, command, is_batch_mode, target_images)

    def _build_simple_to_actual_name_map(self, image_paths):
        """파일명 매핑 생성 - miracle_manager_batch 모듈의 함수 사용"""
        return _build_simple_to_actual_name_map(image_paths)

    def postprocess_ai_response_for_batch_display(self, text, image_paths):
        """배치 표시 후처리 - miracle_manager_batch 모듈의 함수 사용"""
        return postprocess_ai_response_for_batch_display(self, text, image_paths)

    def call_google_ai_api_with_image(self, prompt, image_paths):
        """이미지를 포함한 Google AI API 호출 - miracle_manager_single/batch 모듈의 함수 사용"""
        return call_google_ai_api_with_image(self, prompt, image_paths)

    def call_google_ai_api_with_multiple_images(self, prompt, image_paths):
        """다중 이미지를 포함한 Google AI API 호출 - miracle_manager_batch 모듈의 함수 사용"""
        return call_google_ai_api_with_multiple_images(self, prompt, image_paths)

    def parse_multi_image_response(self, ai_response, target_images):
        """다중 이미지 응답 파싱 - miracle_manager_batch 모듈의 함수 사용"""
        return parse_multi_image_response(ai_response, target_images)

    def get_current_image_tags(self):
        """현재 이미지의 태그들 가져오기 - miracle_manager_single 모듈의 함수 사용"""
        return get_current_image_tags(self)

class MiracleManager:
    """미라클 매니저 - 태깅 섹션 UI 토글 관리"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.is_miracle_mode = False
        self.miracle_tag_input = None
        self.miracle_settings = None  # 미라클 설정 모듈
        # 우측 패널 대체 카드 및 라벨
        self.right_miracle_card = None
        self._response_label = None
        self._responses_layout = None
        self._responses_scroll = None
        # 배치 재시도 관련
        self._retry_button = None
        self._failed_batch_info = None  # {command, batch_size, failed_images: [{chunk, error, batch_num}]}
        # 응답 카드 페이지네이션
        self._responses_container = None
        self._response_cards = []
        self._response_items_per_page = 10
        self._response_current_page = 1
        self._response_prev_btn = None
        self._response_next_btn = None
        self._response_page_label = None
        self._retry_button_page = None
        self._responses_pagination_layout = None
        self._response_card_meta = {}
        self._pending_response_card_order = []
        self._failed_single_info = None
    
    def initialize_settings(self, app_instance):
        """설정 모듈 초기화 (앱 인스턴스 설정 후 호출)"""
        try:
            if not self.miracle_settings:
                self.miracle_settings = MiracleSettingsModule(app_instance)
                print(f"✨ Miracle Manager: 설정 모듈 초기화 완료 - {len(self.miracle_settings.api_keys)}개 API 키 로드됨")
        except Exception as e:
            print(f"✨ Miracle Manager: 설정 모듈 초기화 오류 - {e}")

    def toggle_miracle_mode(self):
        """미라클 모드 토글"""
        # 비디오 그리드 모드인지 확인하고 이미지 그리드 모드로 전환
        if hasattr(self.app, 'video_filter_btn') and hasattr(self.app, 'image_filter_btn'):
            video_checked = self.app.video_filter_btn.isChecked()
            image_checked = self.app.image_filter_btn.isChecked()
            
            if video_checked and not image_checked:
                print("비디오 그리드 모드 감지 - 이미지 그리드 모드로 전환")
                # 이미지 모드로 전환
                self.app.image_filter_btn.setChecked(True)
                self.app.video_filter_btn.setChecked(False)
                
                # 이미지 그리드로 전환
                try:
                    from search_filter_grid_image_module import switch_to_image_grid
                    switch_to_image_grid(self.app)
                except Exception as e:
                    print(f"이미지 그리드 전환 중 오류: {e}")
                    # 폴백: 직접 그리드 갱신
                    try:
                        from search_module import update_image_grid_unified
                        self.app.active_grid_token += 1
                        update_image_grid_unified(self.app, expected_token=self.app.active_grid_token)
                    except Exception as e2:
                        print(f"그리드 갱신 중 오류: {e2}")
                
                # 미라클 모드가 이미 켜져 있으면 유지하고 종료
                if self.is_miracle_mode:
                    print("미라클 모드가 이미 활성화되어 있음 - 그리드만 전환하고 미라클 모드는 유지")
                    return
        
        # 비디오 모드가 아니거나, 비디오 모드였지만 미라클 모드가 꺼져 있을 때만 토글
        if not self.is_miracle_mode:
            self.activate_miracle_mode()
        else:
            self.deactivate_miracle_mode()

    def activate_miracle_mode(self):
        """미라클 모드 활성화"""
        print("✨ Miracle Manager: 미라클 모드 활성화")
        if hasattr(self.app, 'tag_input_widget') and self.app.tag_input_widget:
            self.app.tag_input_widget.hide()
            self.miracle_tag_input = MiracleTagInput()
            self.miracle_tag_input.app_instance = self.app
            # 설정 모듈 연결
            if self.miracle_settings:
                self.miracle_tag_input.miracle_settings = self.miracle_settings
            if hasattr(self.app, 'tagging_card') and self.app.tagging_card:
                body_layout = self.app.tagging_card.body
                target_index = -1
                for i in range(body_layout.count()):
                    item = body_layout.itemAt(i)
                    if item and item.widget() == self.app.tag_input_widget:
                        target_index = i
                        break
                if target_index >= 0:
                    body_layout.removeWidget(self.app.tag_input_widget)
                    body_layout.insertWidget(target_index, self.miracle_tag_input)
                else:
                    body_layout.insertWidget(0, self.miracle_tag_input)

        # 우측 태그 스타일시트 섹션 숨기고 동일 위치에 미라클 응답 섹션 추가
        try:
            tags_card = None
            if hasattr(self.app, 'tag_statistics_module') and hasattr(self.app.tag_statistics_module, 'tags_card'):
                tags_card = self.app.tag_statistics_module.tags_card
            if tags_card:
                right_panel = tags_card.parent()
                layout = right_panel.layout() if right_panel and hasattr(right_panel, 'layout') else None

                # 미라클 카드 생성(없으면)
                if self.right_miracle_card is None:
                    from tag_statistics_module import SectionCard
                    self.right_miracle_card = SectionCard("MIRACLE RESPONSE")
                    # 누적 레이아웃 컨테이너 (기존 누적 동작 유지)
                    container = QWidget()
                    container.setStyleSheet("background: transparent;")
                    self._responses_layout = QVBoxLayout(container)
                    self._responses_layout.setContentsMargins(0, 0, 0, 0)
                    self._responses_layout.setSpacing(6)
                    self._responses_layout.setAlignment(Qt.AlignTop)
                    self._responses_container = container
                    # 스크롤 영역 추가
                    self._responses_scroll = QScrollArea()
                    self._responses_scroll.setWidgetResizable(True)
                    self._responses_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    self._responses_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget { background: transparent; } QScrollArea QWidget#qt_scrollarea_viewport { background: transparent; }")
                    self._responses_scroll.setFrameShape(QFrame.NoFrame)
                    self._responses_scroll.setWidget(container)
                    # 뷰포트도 투명 강제
                    try:
                        self._responses_scroll.viewport().setStyleSheet("background: transparent;")
                    except Exception:
                        pass
                    self.right_miracle_card.body.addWidget(self._responses_scroll)
                    self._ensure_response_pagination_controls()
                    self._render_response_page()

                if layout is not None:
                    # (1) 기존 카드의 사이즈 정책/폭 한계치를 새 카드에 그대로 승계
                    try:
                        self.right_miracle_card.setSizePolicy(tags_card.sizePolicy())
                        self.right_miracle_card.setMinimumWidth(tags_card.minimumWidth())
                        mw = tags_card.maximumWidth()
                        if mw > 0:
                            self.right_miracle_card.setMaximumWidth(mw)
                    except Exception:
                        pass

                    # (2) 같은 자리에 교체: replaceWidget 우선, 실패 시 인덱스 동일 삽입
                    try:
                        layout.replaceWidget(tags_card, self.right_miracle_card)
                    except Exception:
                        idx = layout.indexOf(tags_card)
                        if idx < 0:
                            layout.addWidget(self.right_miracle_card)
                        else:
                            layout.removeWidget(tags_card)
                            layout.insertWidget(idx, self.right_miracle_card)

                # 마지막으로 가시성 스위치
                tags_card.hide()
                self.right_miracle_card.show()
        except Exception as e:
            print(f"우측 미라클 섹션 활성화 중 오류: {e}")

        self.is_miracle_mode = True
        try:
            self.render_cached_response_cards()
        except Exception as e:
            print(f"미라클 응답 카드 캐시 렌더링 실패: {e}")

    def _ensure_response_pagination_controls(self):
        """응답 카드 페이지 네비게이션 UI를 생성 (단 한 번)"""
        try:
            if self._responses_pagination_layout or not self.right_miracle_card:
                return
            if not hasattr(self.right_miracle_card, 'body') or self.right_miracle_card.body is None:
                return
            controls_layout = QHBoxLayout()
            controls_layout.setContentsMargins(0, 8, 0, 0)
            controls_layout.setSpacing(4)
            controls_layout.addStretch()

            prev_btn = QPushButton("❮")
            prev_btn.setCursor(Qt.PointingHandCursor)
            prev_btn.setStyleSheet("""
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
            prev_btn.clicked.connect(lambda: self._change_response_page(-1))

            page_label = QLabel("0 / 0")
            page_label.setAlignment(Qt.AlignCenter)
            page_label.setStyleSheet("""
                QLabel {
                    color: #F0F2F5;
                    font-size: 12px;
                    padding: 0px 8px;
                }
            """)

            next_btn = QPushButton("❯")
            next_btn.setCursor(Qt.PointingHandCursor)
            next_btn.setStyleSheet("""
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
            next_btn.clicked.connect(lambda: self._change_response_page(1))

            controls_layout.addWidget(prev_btn)
            controls_layout.addWidget(page_label)
            controls_layout.addWidget(next_btn)
            controls_layout.addStretch()

            self.right_miracle_card.body.addLayout(controls_layout)
            self._responses_pagination_layout = controls_layout
            self._response_prev_btn = prev_btn
            self._response_next_btn = next_btn
            self._response_page_label = page_label
            self._update_response_pagination_ui()
        except Exception as e:
            print(f"응답 페이지네이션 UI 생성 중 오류: {e}")

    def _get_total_response_pages(self) -> int:
        try:
            total = len(self._response_cards)
            per_page = max(1, int(self._response_items_per_page or 10))
            if total <= 0:
                return 0
            return (total + per_page - 1) // per_page
        except Exception:
            return 0

    def _change_response_page(self, direction: int):
        try:
            total_pages = self._get_total_response_pages()
            if total_pages == 0:
                return
            current = max(1, int(self._response_current_page or 1))
            new_page = current + direction
            if new_page < 1:
                new_page = 1
            if new_page > total_pages:
                new_page = total_pages
            if new_page != current:
                self._response_current_page = new_page
                self._render_response_page()
        except Exception as e:
            print(f"응답 페이지 변경 중 오류: {e}")

    def _ensure_response_card_in_layout(self, card: QWidget):
        try:
            if not card or self._responses_layout is None:
                return
            if card.parent() is None and self._responses_container is not None:
                card.setParent(self._responses_container)
            if self._responses_layout.indexOf(card) == -1:
                self._responses_layout.addWidget(card)
        except Exception:
            pass

    def _render_response_page(self, scroll_to_end: bool = False):
        try:
            if self._responses_layout is None:
                return

            total_pages = self._get_total_response_pages()
            if total_pages == 0:
                self._response_current_page = 1
            elif self._response_current_page > total_pages:
                self._response_current_page = total_pages
            elif self._response_current_page < 1:
                self._response_current_page = 1

            per_page = max(1, int(self._response_items_per_page or 10))
            if total_pages == 0:
                current_page_cards = []
            else:
                start_idx = (self._response_current_page - 1) * per_page
                end_idx = start_idx + per_page
                current_page_cards = self._response_cards[start_idx:end_idx]

            visible_set = set(current_page_cards)
            for card in self._response_cards:
                self._ensure_response_card_in_layout(card)
                card.setVisible(card in visible_set)

            if self._retry_button:
                target_page = self._retry_button_page
                if target_page is None:
                    target_page = total_pages if total_pages > 0 else 1
                if total_pages > 0 and target_page > total_pages:
                    target_page = total_pages
                    self._retry_button_page = target_page
                if self._responses_layout is not None:
                    self._ensure_response_card_in_layout(self._retry_button)
                if target_page == self._response_current_page:
                    self._retry_button.setVisible(True)
                else:
                    self._retry_button.setVisible(False)

            self._update_response_pagination_ui()

            if scroll_to_end:
                self._scroll_responses_to_bottom()
        except Exception as e:
            print(f"응답 페이지 렌더링 중 오류: {e}")

    def _update_response_pagination_ui(self):
        try:
            if not self._response_page_label or not self._response_prev_btn or not self._response_next_btn:
                return
            total_cards = len(self._response_cards)
            total_pages = self._get_total_response_pages()
            current = self._response_current_page if total_pages > 0 else 0

            if total_pages == 0:
                self._response_page_label.setText("0 / 0")
                self._response_prev_btn.setEnabled(False)
                self._response_next_btn.setEnabled(False)
            else:
                self._response_page_label.setText(f"{current} / {total_pages}")
                self._response_prev_btn.setEnabled(current > 1)
                self._response_next_btn.setEnabled(current < total_pages)
        except Exception as e:
            print(f"응답 페이지네이션 UI 업데이트 중 오류: {e}")

    def _scroll_responses_to_bottom(self):
        try:
            if not self._responses_scroll:
                return
            from PySide6.QtCore import QTimer
            scroll_bar = self._responses_scroll.verticalScrollBar()
            if not scroll_bar:
                return
            QTimer.singleShot(50, lambda: scroll_bar.setValue(scroll_bar.maximum()))
        except Exception:
            pass

    def deactivate_miracle_mode(self):
        """미라클 모드 비활성화"""
        print("✨ Miracle Manager: 미라클 모드 비활성화")
        if self.miracle_tag_input:
            if hasattr(self.app, 'tagging_card') and self.app.tagging_card:
                body_layout = self.app.tagging_card.body
                target_index = -1
                for i in range(body_layout.count()):
                    item = body_layout.itemAt(i)
                    if item and item.widget() == self.miracle_tag_input:
                        target_index = i
                        break
                if target_index >= 0:
                    body_layout.removeWidget(self.miracle_tag_input)
                    body_layout.insertWidget(target_index, self.app.tag_input_widget)
                else:
                    body_layout.insertWidget(0, self.app.tag_input_widget)
            self.miracle_tag_input.hide()
            self.miracle_tag_input.deleteLater()
            self.miracle_tag_input = None
        if hasattr(self.app, 'tag_input_widget') and self.app.tag_input_widget:
            self.app.tag_input_widget.show()

        # 우측 패널 복구: 미라클 카드 숨기고 태그 스타일시트 카드 표시
        try:
            if hasattr(self.app, 'tag_statistics_module') and hasattr(self.app.tag_statistics_module, 'tags_card'):
                tags_card = self.app.tag_statistics_module.tags_card
            else:
                tags_card = None

            parent = None
            layout = None
            if self.right_miracle_card is not None:
                parent = self.right_miracle_card.parent()
                if parent and hasattr(parent, 'layout'):
                    layout = parent.layout()

            # 같은 자리로 원래 카드 되돌리기: replaceWidget 우선
            if layout is not None and tags_card is not None:
                try:
                    layout.replaceWidget(self.right_miracle_card, tags_card)
                except Exception:
                    try:
                        idx = layout.indexOf(self.right_miracle_card)
                        if idx < 0:
                            # 미라클 카드가 레이아웃에 없다면, 태그 카드가 없는 경우에만 추가
                            if layout.indexOf(tags_card) < 0:
                                layout.addWidget(tags_card)
                        else:
                            # 동일 인덱스에 태그 카드 삽입
                            layout.removeWidget(self.right_miracle_card)
                            layout.insertWidget(idx, tags_card)
                    except Exception:
                        pass

            # 가시성 전환
            if self.right_miracle_card is not None:
                self.right_miracle_card.hide()
            if tags_card is not None:
                tags_card.show()
        except Exception as e:
            print(f"우측 패널 복구 중 오류: {e}")

        self.is_miracle_mode = False

    def update_right_response(self, text: str, card_id: str = None, log_to_tm: bool = True, border_color_override: str = None, tm_payload: dict = None, defer_tm_commit: bool = False):
        """우측 미라클 응답 섹션 텍스트 업데이트
        Args:
            text: 표시할 텍스트
            card_id: 외부에서 지정한 카드 ID (redo 시 재사용)
            log_to_tm: 타임머신 로그 기록 여부 (redo 시 False로 설정)
            border_color_override: 윤곽선 색상 강제 지정 (redo 시 사용)
            tm_payload: 타임머신 로그에 추가할 추가 필드(dict)
            defer_tm_commit: True일 경우 타임머신 커밋을 호출자가 직접 수행
        """
        try:
            if not self.is_miracle_mode:
                return card_id
            # 누적 모드: 새 라벨을 만들어 추가
            if self._responses_layout is None:
                return card_id
            clean = text if text else ""
            if clean:
                # 빈 줄 보존: 내용 오른쪽 공백만 제거하고, '::' 줄만 걸러냄
                lines = [ln.rstrip() for ln in str(clean).split('\n') if '::' not in ln]
                clean = '\n'.join(lines)
                # 연속 개행을 최대 2개까지만 허용
                import re
                clean = re.sub(r'\n{3,}', '\n\n', clean)
            # 행간을 넓힌 리치텍스트로 렌더링
            safe = str(clean).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_html = safe.replace("\n", "<br/>")
            html = "<div style='line-height:1.1; white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere;'>" + safe_html + "</div>"
            lbl = QLabel()
            lbl.setTextFormat(Qt.RichText)
            lbl.setText(html)
            # 윤곽선 색상: 배치(초록) / 단일(파랑)
            try:
                border_color = border_color_override or getattr(self, '_current_response_border', None)
                if not border_color:
                    border_color = "#3B82F6"  # blue-500 (단일)
            except Exception:
                border_color = border_color_override or "#3B82F6"
            lbl.setStyleSheet(f"color: #E5E7EB; font-size: 12px; background: rgba(255,255,255,0.03); padding: 8px; border-radius: 6px; border: 2px solid {border_color};")
            lbl.setWordWrap(True)
            try:
                from PySide6.QtWidgets import QSizePolicy
                lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                # heightForWidth 기반 자동 높이 산정에 맡긴다
                lbl.setMinimumHeight(0)
                lbl.setMinimumWidth(1)
                lbl.updateGeometry()
            except Exception:
                pass
            lbl.hide()
            if not hasattr(self, '_response_cards') or self._response_cards is None:
                self._response_cards = []
            self._response_cards.append(lbl)
            try:
                self._ensure_response_card_in_layout(lbl)
            except Exception:
                pass

            final_card_id = card_id
            if not final_card_id:
                try:
                    import uuid
                    final_card_id = f"rc_{uuid.uuid4().hex[:12]}"
                except Exception:
                    final_card_id = None

            if final_card_id:
                try:
                    self._tm_ensure_map()
                    existing_widget = self._response_card_map.get(final_card_id)
                    if existing_widget:
                        try:
                            if hasattr(self, '_responses_layout') and self._responses_layout:
                                self._responses_layout.removeWidget(existing_widget)
                        except Exception:
                            pass
                        try:
                            self._response_cards = [w for w in self._response_cards if w is not existing_widget]
                        except Exception:
                            pass
                        try:
                            existing_widget.setParent(None)
                            existing_widget.deleteLater()
                        except Exception:
                            pass
                        self._response_card_map.pop(final_card_id, None)
                except Exception:
                    pass
                try:
                    lbl.setProperty("tm_card_id", final_card_id)
                except Exception:
                    pass
                try:
                    self._tm_ensure_map()
                    self._response_card_map[final_card_id] = lbl
                except Exception:
                    pass
                try:
                    mode_for_meta = "batch" if border_color == "#22c55e" else "single"
                    meta = {
                        "text": clean,
                        "border": border_color,
                        "mode": mode_for_meta,
                    }
                    if tm_payload:
                        meta["payload"] = tm_payload
                    self._response_card_meta[final_card_id] = meta
                except Exception as meta_e:
                    print(f"응답 카드 메타 저장 실패: {meta_e}")
                try:
                    if final_card_id not in self._pending_response_card_order:
                        self._pending_response_card_order.append(final_card_id)
                except Exception:
                    pass
            else:
                # fallback: ensure map stays consistent
                try:
                    lbl.setProperty("tm_card_id", "")
                except Exception:
                    pass

            # 타임머신 로그 기록 (태그 조작 여부와 관계없이 항상 기록)
            if log_to_tm and final_card_id:
                try:
                    from timemachine_log import TM
                    if TM is not None:
                        mode = "batch" if border_color == "#22c55e" else "single"
                        manual_tx_started = False
                        try:
                            tx_stack = getattr(TM._local, "_tm_tx_stack", [])
                        except Exception:
                            tx_stack = []
                        if not tx_stack:
                            try:
                                title = f"{mode} response"
                                TM.begin(title, context={
                                    "source": f"miracle_{mode}",
                                    "mode": mode,
                                })
                                manual_tx_started = True
                            except Exception as begin_err:
                                print(f"타임머신 임시 트랜잭션 시작 실패: {begin_err}")
                                manual_tx_started = False

                        log_record = {
                            "type": "miracle_response_card",
                            "card_id": final_card_id,
                            "action": "add",
                            "mode": mode,
                            "text": clean
                        }
                        if tm_payload:
                            try:
                                log_record.update(tm_payload)
                            except Exception:
                                pass
                        else:
                            image_path = ""
                            try:
                                if hasattr(self.app, 'current_image') and self.app.current_image:
                                    image_path = str(self.app.current_image)
                            except Exception:
                                pass
                            if image_path:
                                log_record["image"] = image_path
                        TM.log_change(log_record)
                        if manual_tx_started:
                            try:
                                TM.commit()
                            except Exception as manual_commit_err:
                                print(f"타임머신 임시 트랜잭션 커밋 실패: {manual_commit_err}")
                                try:
                                    TM.abort()
                                except Exception:
                                    pass
                        elif not defer_tm_commit:
                            TM.commit()
                except Exception as tm_e:
                    print(f"타임머신 로그 기록 실패: {tm_e}")
            
            target_page = self._get_total_response_pages()
            if target_page <= 0:
                target_page = 1
            scroll_to_end = True
            if target_page != self._response_current_page:
                self._response_current_page = target_page
            self._render_response_page(scroll_to_end=scroll_to_end)
            # 다음 추가를 대비해 기본값으로 되돌림
            try:
                self._current_response_border = None
            except Exception:
                pass

            return final_card_id
        except Exception as e:
            print(f"미라클 응답 업데이트 중 오류: {e}")
            return card_id
    
    def remove_retry_button(self):
        """재시도 버튼 제거"""
        try:
            if self._retry_button:
                if self._responses_layout:
                    try:
                        self._responses_layout.removeWidget(self._retry_button)
                    except Exception:
                        pass
                self._retry_button.hide()
                self._retry_button.deleteLater()
                self._retry_button = None
                self._retry_button_page = None
                self._failed_batch_info = None
                self._failed_single_info = None
                print("재시도 버튼 제거됨")
                self._render_response_page()
        except Exception as e:
            print(f"재시도 버튼 제거 중 오류: {e}")
    
    def add_retry_button_if_needed(self):
        """배치 작업 실패 시 재시도 버튼 추가"""
        try:
            if self._failed_batch_info:
                failed_images_list = self._failed_batch_info.get('failed_images', [])
                if not failed_images_list:
                    return
                
                # 기존 재시도 버튼이 있으면 제거
                self.remove_retry_button()
                
                # 재시도 버튼 생성 (액션 버튼 모듈과 동일한 스타일)
                from PySide6.QtWidgets import QPushButton
                from PySide6.QtCore import Qt
                
                failed_count = sum(len(item.get('chunk', [])) for item in failed_images_list)
                button_text = f"실패한 {failed_count}개 이미지 재시도"
                
                self._retry_button = QPushButton(button_text)
                self._retry_button.setCursor(Qt.PointingHandCursor)
                self._retry_button.setFixedHeight(36)  # 액션 버튼과 동일한 높이
                self._retry_button.setStyleSheet("""
                    QPushButton {
                        background: #4A5568;
                        color: #CBD5E0;
                        border: 1px solid #4A5568;
                        border-radius: 6px;
                        padding: 10px 20px;
                        font-weight: 600;
                        font-size: 12px;
                        min-height: 16px;
                    }
                    QPushButton:hover {
                        background: #718096;
                        border-color: #718096;
                        color: #CBD5E0;
                    }
                    QPushButton:pressed {
                        background: #2D3748;
                        border-color: #2D3748;
                        color: #CBD5E0;
                    }
                """)
                self._retry_button.clicked.connect(self.retry_failed_batch)
                
                # 레이아웃 맨 아래에 추가
                self._retry_button.hide()
                total_pages = self._get_total_response_pages()
                self._retry_button_page = total_pages if total_pages > 0 else 1
                self._render_response_page(scroll_to_end=True)
                
                print(f"재시도 버튼 추가됨: {failed_count}개 이미지")
                return
            
            if self._failed_single_info:
                single_info = dict(self._failed_single_info)
                command_preview = single_info.get('command', '') or ''
                
                # 기존 재시도 버튼이 있으면 제거
                self.remove_retry_button()
                
                from PySide6.QtWidgets import QPushButton
                from PySide6.QtCore import Qt
                
                button_text = f"실패한 {single_info.get('failed_targets', 1)}개 이미지 재시도"
                
                self._failed_single_info = single_info
                
                self._retry_button = QPushButton(button_text)
                self._retry_button.setCursor(Qt.PointingHandCursor)
                self._retry_button.setFixedHeight(36)
                self._retry_button.setStyleSheet("""
                    QPushButton {
                        background: #4A5568;
                        color: #CBD5E0;
                        border: 1px solid #4A5568;
                        border-radius: 6px;
                        padding: 10px 20px;
                        font-weight: 600;
                        font-size: 12px;
                        min-height: 16px;
                    }
                    QPushButton:hover {
                        background: #718096;
                        border-color: #718096;
                        color: #CBD5E0;
                    }
                    QPushButton:pressed {
                        background: #2D3748;
                        border-color: #2D3748;
                        color: #CBD5E0;
                    }
                """)
                if command_preview:
                    try:
                        self._retry_button.setToolTip(command_preview)
                    except Exception:
                        pass
                self._retry_button.clicked.connect(self.retry_failed_single)
                
                self._retry_button.hide()
                total_pages = self._get_total_response_pages()
                self._retry_button_page = total_pages if total_pages > 0 else 1
                self._render_response_page(scroll_to_end=True)
                
                print("재시도 버튼 추가됨: 단일 명령 재시도")
            
        except Exception as e:
            print(f"재시도 버튼 추가 중 오류: {e}")
    
    def retry_failed_single(self):
        """단일 작업 실패 재시도"""
        try:
            info = dict(self._failed_single_info or {})
            command = info.get('command', '')
            if not command:
                print("재시도할 단일 명령어가 없습니다")
                return
            
            miracle_input_widget = getattr(self, 'miracle_tag_input', None)
            if miracle_input_widget is None:
                print("미라클 입력 위젯을 찾을 수 없습니다")
                return
            
            if getattr(miracle_input_widget, '_miracle_busy', False):
                print("이전 작업이 아직 진행 중입니다. 단일 재시도를 건너뜁니다.")
                return
            
            print("✨ Miracle Manager: 단일 명령 재시도 시작")
            
            self.remove_retry_button()
            
            if hasattr(miracle_input_widget, 'miracle_tag_input'):
                try:
                    placeholder_text = "재시도 중... 잠시만 기다려주세요"
                    trimmed = command.strip()
                    if trimmed:
                        preview = trimmed if len(trimmed) <= 40 else trimmed[:40] + "…"
                        placeholder_text = f"재시도 중... 잠시만 기다려주세요 ({preview})"
                    miracle_input_widget.miracle_tag_input.setEnabled(False)
                    miracle_input_widget.miracle_tag_input.setPlaceholderText(placeholder_text)
                    miracle_input_widget.miracle_tag_input.setStyleSheet("""
                        QLineEdit {
                            background-color: #2a2a2a;
                            color: #888888;
                            border: 2px solid #4CAF50;
                            font-size: 12px;
                        }
                    """)
                except Exception as e:
                    print(f"입력창 비활성화 중 오류: {e}")
            
            if hasattr(miracle_input_widget, '_miracle_busy'):
                miracle_input_widget._miracle_busy = True

            if hasattr(miracle_input_widget, 'start_miracle_progress'):
                try:
                    miracle_input_widget.start_miracle_progress(
                        1,
                        prefix="미라클 재시도 중..."
                    )
                except Exception as prog_err:
                    print(f"[MiracleProgress] 단일 재시도 진행 초기화 실패: {prog_err}")
            
            if hasattr(miracle_input_widget, 'show_loading_indicator'):
                miracle_input_widget.show_loading_indicator("재시도 중...")
            
            process_miracle_command_async(miracle_input_widget, command)
        except Exception as e:
            import traceback
            print(f"단일 재시도 중 오류: {e}")
            print(traceback.format_exc())
    
    def retry_failed_batch(self):
        """실패한 배치 이미지들만 재시도"""
        try:
            if not self._failed_batch_info:
                print("재시도할 실패 정보가 없습니다")
                return
            
            command = self._failed_batch_info.get('command', '')
            failed_images_list = self._failed_batch_info.get('failed_images', [])
            
            # 실패한 모든 이미지들을 모음
            failed_images = []
            for item in failed_images_list:
                failed_images.extend(item.get('chunk', []))
            
            if not failed_images:
                print("재시도할 실패한 이미지가 없습니다")
                return
            
            print(f"✨ Miracle Manager: 실패한 {len(failed_images)}개 이미지 재시도 시작")
            
            # 재시도 버튼 제거 및 실패 정보 초기화 (새로운 재시도 결과를 위해)
            self.remove_retry_button()
            # 재시도 시작 전 실패 정보를 None으로 초기화 (새 배치의 결과를 받기 위해)
            self._failed_batch_info = None
            
            # 배치 워커로 재시도
            if hasattr(self.app, 'miracle_manager') and hasattr(self.app.miracle_manager, 'miracle_tag_input'):
                miracle_input_widget = self.app.miracle_manager.miracle_tag_input
                
                # 현재 배치 사이즈 가져오기 (사용자가 변경한 값 반영)
                batch_size = miracle_input_widget.get_batch_size() if hasattr(miracle_input_widget, 'get_batch_size') else 10
                
                # 입력창 비활성화 (일반 작업과 동일하게)
                if hasattr(miracle_input_widget, 'miracle_tag_input'):
                    try:
                        miracle_input_widget.miracle_tag_input.setEnabled(False)
                        # 플레이스홀더에 기존 명령어 표시
                        placeholder_text = f"재시도 중... 잠시만 기다려주세요 ({command})" if command else "재시도 중... 잠시만 기다려주세요"
                        miracle_input_widget.miracle_tag_input.setPlaceholderText(placeholder_text)
                        miracle_input_widget.miracle_tag_input.setStyleSheet("""
                            QLineEdit {
                                background-color: #2a2a2a;
                                color: #888888;
                                border: 2px solid #4CAF50;
                                font-size: 12px;
                            }
                        """)
                    except Exception as e:
                        print(f"입력창 비활성화 중 오류: {e}")
                
                # 중복 실행 방지 플래그 설정
                if hasattr(miracle_input_widget, '_miracle_busy'):
                    miracle_input_widget._miracle_busy = True
                
                # 로딩 인디케이터 표시
                if hasattr(miracle_input_widget, 'show_loading_indicator'):
                    miracle_input_widget.show_loading_indicator("재시도 중...")

                if hasattr(miracle_input_widget, 'start_miracle_progress'):
                    try:
                        miracle_input_widget.start_miracle_progress(
                            max(1, len(failed_images)),
                            prefix="미라클 재시도 중..."
                        )
                    except Exception as prog_err:
                        print(f"[MiracleProgress] 배치 재시도 진행 초기화 실패: {prog_err}")
                
                from PySide6.QtCore import QThread
                miracle_input_widget.batch_thread = QThread()
                miracle_input_widget.batch_worker = BatchWorker(command, failed_images, batch_size, miracle_input_widget)
                miracle_input_widget.batch_worker.moveToThread(miracle_input_widget.batch_thread)
                miracle_input_widget.batch_thread.started.connect(miracle_input_widget.batch_worker.run)
                miracle_input_widget.batch_worker.progress.connect(miracle_input_widget.on_batch_progress)
                miracle_input_widget.batch_worker.finished.connect(miracle_input_widget.on_batch_finished)
                # 정리 연결
                miracle_input_widget.batch_worker.finished.connect(miracle_input_widget.batch_thread.quit)
                miracle_input_widget.batch_thread.finished.connect(miracle_input_widget.batch_thread.deleteLater)
                miracle_input_widget.batch_worker.finished.connect(miracle_input_widget.batch_worker.deleteLater)
                miracle_input_widget.batch_thread.start()
                
                print(f"✨ Miracle Manager: 재시도 배치 워커 시작 - {len(failed_images)}개 이미지, 배치 크기: {batch_size}")
            
        except Exception as e:
            import traceback
            print(f"재시도 중 오류: {e}")
            print(traceback.format_exc())

    def clear_right_response_borders(self):
        """우측 응답 카드들의 윤곽선을 제거 (새 작업 시작 시 호출)"""
        try:
            if not hasattr(self, '_response_cards') or self._response_cards is None:
                return
            import re
            targets = list(self._response_cards)
            if self._retry_button:
                targets.append(self._retry_button)
            for w in targets:
                if not w:
                    continue
                try:
                    style = w.styleSheet() or ""
                    # 기존 border 제거
                    style2 = re.sub(r"border:\s*\d+px\s*solid\s*#[0-9A-Fa-f]{3,6};?", "border: none;", style)
                    if "border:" not in style2:
                        if style2 and not style2.endswith(";"):
                            style2 += ";"
                        style2 += " border: none;"
                    w.setStyleSheet(style2)
                except Exception:
                    pass
        except Exception as e:
            print(f"우측 응답 윤곽선 제거 중 오류: {e}")

    # ── TimeMachine integration: response card mapping (added) ─────────────────
    def _tm_ensure_map(self):
        try:
            getattr(self, '_response_card_map')
        except Exception:
            try:
                self._response_card_map = {}
            except Exception:
                pass

    def tm_mark_last_response_card(self, card_id: str) -> bool:
        """마지막으로 추가된 우측 응답 카드를 card_id로 마킹하고 내부 맵에 저장합니다."""
        try:
            self._tm_ensure_map()
            cards = getattr(self, '_response_cards', None)
            if not cards:
                return False
            w = cards[-1]
            if w is None:
                return False
            try:
                w.setProperty("tm_card_id", card_id)
            except Exception:
                pass
            self._response_card_map[card_id] = w
            return True
        except Exception as e:
            print(f"[MiracleManager] tm_mark_last_response_card error: {e}")
        return False

    def tm_remove_response_card(self, card_id: str) -> None:
        """card_id로 우측 응답 카드를 찾아 제거합니다 (undo)."""
        try:
            layout = getattr(self, '_responses_layout', None)
            w = None
            if hasattr(self, '_response_card_map'):
                w = self._response_card_map.pop(card_id, None)
            if w is None:
                cards = getattr(self, '_response_cards', None) or []
                for ww in cards:
                    if ww is not None and ww.property('tm_card_id') == card_id:
                        w = ww
                        break
            if w is not None:
                try:
                    if layout is not None:
                        try:
                            layout.removeWidget(w)
                        except Exception:
                            pass
                    if hasattr(self, '_response_cards') and self._response_cards:
                        try:
                            self._response_cards = [c for c in self._response_cards if c is not w]
                        except Exception:
                            pass
                    w.setParent(None)
                    w.deleteLater()
                    self._render_response_page()
                except Exception:
                    pass
        except Exception as e:
            print(f"[MiracleManager] tm_remove_response_card error: {e}")

    def tm_recreate_response_card(self, card_id: str, text: str, border_color: str = None) -> None:
        """redo 시 기존 card_id로 카드를 재생성합니다."""
        try:
            if not card_id:
                return
            # 이미 존재하면 중복 생성 방지
            if hasattr(self, '_response_card_map') and card_id in self._response_card_map:
                return
            prev = getattr(self, '_current_response_border', None)
            try:
                if border_color:
                    self._current_response_border = border_color
            except Exception:
                pass
            try:
                # 기존 API 재사용 (타임머신 로그는 이미 기록되어 있으므로 비활성화)
                if hasattr(self, 'update_right_response'):
                    self.update_right_response(text or "", card_id=card_id, log_to_tm=False, border_color_override=border_color)
            finally:
                try:
                    self._current_response_border = prev
                except Exception:
                    pass
        except Exception as e:
            print(f"[MiracleManager] tm_recreate_response_card error: {e}")

    def clear_response_cards(self):
        try:
            if hasattr(self, '_responses_layout') and self._responses_layout:
                while self._responses_layout.count():
                    item = self._responses_layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)
                        widget.deleteLater()
            self._response_cards = []
            if hasattr(self, '_response_card_map'):
                self._response_card_map.clear()
            if hasattr(self, '_response_card_meta'):
                self._response_card_meta.clear()
            if hasattr(self, '_pending_response_card_order'):
                self._pending_response_card_order = []
            if self._retry_button:
                try:
                    self._retry_button.hide()
                    self._retry_button.deleteLater()
                except Exception:
                    pass
                self._retry_button = None
            self._retry_button_page = None
            self._response_current_page = 1
            self._update_response_pagination_ui()
        except Exception as e:
            print(f"[MiracleManager] 응답 카드 초기화 오류: {e}")

    def render_cached_response_cards(self):
        try:
            if not self.is_miracle_mode or self._responses_layout is None:
                return
            if not getattr(self, '_pending_response_card_order', None):
                return
            self._tm_ensure_map()

            for card_id in self._pending_response_card_order:
                if hasattr(self, '_response_card_map') and card_id in self._response_card_map:
                    continue
                meta = self._response_card_meta.get(card_id)
                if not meta:
                    continue
                text = meta.get("text", "")
                border = meta.get("border", "#3B82F6")
                payload = meta.get("payload")
                self.update_right_response(
                    text,
                    card_id=card_id,
                    log_to_tm=False,
                    border_color_override=border,
                    tm_payload=payload,
                    defer_tm_commit=True,
                )
        except Exception as e:
            print(f"[MiracleManager] 응답 카드 캐시 렌더링 오류: {e}")
    