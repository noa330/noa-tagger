# -*- coding: utf-8 -*-
"""
Shortcut Manager Debug Module - 단축키 매니저 디버깅 모듈
키버튼 10번 연속 클릭 시 디버그 창 표시
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class ShortcutDebugDialog(QDialog):
    """단축키 디버그 대화상자"""
    
    def __init__(self, app_instance=None, shortcut_manager=None, parent=None):
        super().__init__(parent)
        self.app_instance = app_instance
        self.shortcut_manager = shortcut_manager
        self.selected_shortcut_handler = None
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("Shortcut Debug - Model Selector")
        self.setModal(False)
        
        # 메인 대화상자 스타일 적용
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 제목 (원본 단축키 매니저와 동일한 스타일)
        title_label = QLabel("Shortcut Debug")
        title_label.setStyleSheet("""
            font-size: 25px;
            font-weight: 700;
            color: #E2E8F0;
            margin-bottom: 8px;
            font-family: 'Segoe UI';
        """)
        layout.addWidget(title_label)
        
        # 단축키 선택 드롭다운
        shortcut_label = QLabel("단축키 선택:")
        shortcut_label.setStyleSheet("""
            QLabel {
                color: #E2E8F0;
                font-size: 12px;
                font-weight: 600;
                margin-top: 4px;
            }
        """)
        layout.addWidget(shortcut_label)
        
        # 단축키 드롭다운 (모델 선택과 동일한 스타일)
        try:
            import sys
            main_module = sys.modules.get('__main__')
            if main_module and hasattr(main_module, 'CustomComboBox'):
                CustomComboBox = main_module.CustomComboBox
            else:
                CustomComboBox = QComboBox
        except:
            CustomComboBox = QComboBox
        
        self.shortcut_combo = CustomComboBox()
        self.shortcut_combo.setStyleSheet("""
            QComboBox {
                background: rgba(26,27,38,0.8);
                color: #F9FAFB;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
                padding: 8px 12px;
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
        
        # 단축키 목록 추가
        if self.shortcut_manager and hasattr(self.shortcut_manager, 'shortcuts'):
            # 중복 제거를 위해 description을 기준으로 정렬
            shortcut_items = []
            seen_descriptions = set()
            
            for key_sequence, shortcut_data in self.shortcut_manager.shortcuts.items():
                description = shortcut_data.get('description', key_sequence)
                handler = shortcut_data.get('handler')
                
                # 같은 description이 여러 개 있을 수 있으므로 key_sequence도 포함
                display_text = f"{description} ({key_sequence})"
                
                # 중복 제거 (같은 description과 key_sequence 조합)
                unique_key = (description, key_sequence)
                if unique_key not in seen_descriptions:
                    shortcut_items.append((display_text, handler, description, key_sequence))
                    seen_descriptions.add(unique_key)
            
            # description으로 정렬
            shortcut_items.sort(key=lambda x: x[2])
            
            for display_text, handler, description, key_sequence in shortcut_items:
                self.shortcut_combo.addItem(display_text, (handler, description, key_sequence))
        
        # 단축키 선택 시 핸들러 저장
        self.shortcut_combo.currentIndexChanged.connect(self.on_shortcut_selected)
        layout.addWidget(self.shortcut_combo)
        
        # 버튼 레이아웃 (적용 버튼과 취소 버튼)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # 적용 버튼 (왼쪽)
        apply_btn = QPushButton("적용")
        apply_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #2563EB;
            }
            QPushButton:pressed {
                background: #1D4ED8;
            }
            QPushButton:disabled {
                background: #6B7280;
                color: #9CA3AF;
            }
        """)
        apply_btn.clicked.connect(self.on_apply_clicked)
        self.apply_btn = apply_btn
        button_layout.addWidget(apply_btn)
        
        # 스트레치로 중간 공간 채우기
        button_layout.addStretch()
        
        # 닫기 버튼 (오른쪽)
        close_btn = QPushButton("닫기")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #6B7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #4B5563;
            }
            QPushButton:pressed {
                background: #374151;
            }
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 초기 상태 설정
        if self.shortcut_combo.count() > 0:
            self.on_shortcut_selected(0)
        else:
            self.apply_btn.setEnabled(False)
        
        # 내용에 맞게 크기 조정
        self.adjustSize()
    
    def on_shortcut_selected(self, index):
        """단축키 선택 시 호출"""
        if index >= 0:
            data = self.shortcut_combo.itemData(index)
            if data:
                handler, description, key_sequence = data
                self.selected_shortcut_handler = handler
                self.selected_description = description
                self.selected_key_sequence = key_sequence
                print(f"[단축키 디버그] 단축키 선택: {description} ({key_sequence})")
                self.apply_btn.setEnabled(True)
            else:
                self.selected_shortcut_handler = None
                self.apply_btn.setEnabled(False)
        else:
            self.selected_shortcut_handler = None
            self.apply_btn.setEnabled(False)
    
    def on_apply_clicked(self):
        """적용 버튼 클릭 시 호출"""
        if self.selected_shortcut_handler:
            try:
                print(f"[단축키 디버그] 단축키 실행: {self.selected_description} ({self.selected_key_sequence})")
                # 핸들러 함수 호출
                self.selected_shortcut_handler()
                print(f"[단축키 디버그] 단축키 실행 완료")
            except Exception as e:
                print(f"[단축키 디버그] 단축키 실행 오류: {e}")
                import traceback
                traceback.print_exc()


class ShortcutDebugManager:
    """단축키 디버그 매니저 - 키버튼 클릭 감지 및 디버그 창 관리"""
    
    def __init__(self, app_instance=None):
        self.app_instance = app_instance
        self.shortcut_manager = None  # shortcut_manager 참조
        self.click_count = {}  # 각 키버튼별 클릭 횟수 추적
        self.last_click_time = {}  # 각 키버튼별 마지막 클릭 시간
        self.click_timeout = 2000  # 2초 내에 클릭해야 연속 클릭으로 인정
        self.debug_dialog = None
    
    def on_key_button_clicked(self, key_button):
        """키버튼 클릭 이벤트 핸들러"""
        # 디버그 프린트
        print(f"[단축키 디버그] 키버튼 클릭: {key_button.text()}")
        
        # 키버튼 고유 ID 생성 (텍스트 + 객체 ID)
        button_id = f"{id(key_button)}"
        
        # 현재 시간
        current_time = QDateTime.currentMSecsSinceEpoch()
        
        # 이전 클릭 시간 확인
        if button_id in self.last_click_time:
            time_diff = current_time - self.last_click_time[button_id]
            
            # 타임아웃 체크 (2초 이상 지나면 리셋)
            if time_diff > self.click_timeout:
                print(f"[단축키 디버그] 타임아웃 - 클릭 카운트 리셋 (경과 시간: {time_diff}ms)")
                self.click_count[button_id] = 0
        
        # 클릭 횟수 증가
        if button_id not in self.click_count:
            self.click_count[button_id] = 0
        
        self.click_count[button_id] += 1
        self.last_click_time[button_id] = current_time
        
        current_count = self.click_count[button_id]
        print(f"[단축키 디버그] 연속 클릭 횟수: {current_count}/10")
        
        # 10번 연속 클릭 확인
        if current_count >= 10:
            print(f"[단축키 디버그] 10번 연속 클릭 달성! 디버그 창 열기")
            self.show_debug_dialog()
            # 클릭 카운트 리셋
            self.click_count[button_id] = 0
    
    def show_debug_dialog(self):
        """디버그 대화상자 표시"""
        if self.debug_dialog is None or not self.debug_dialog.isVisible():
            # shortcut_manager 가져오기 (우선순위: 직접 할당된 것 > app_instance에서 가져오기)
            shortcut_manager = self.shortcut_manager
            if shortcut_manager is None and self.app_instance and hasattr(self.app_instance, 'shortcut_manager'):
                shortcut_manager = self.app_instance.shortcut_manager
            
            self.debug_dialog = ShortcutDebugDialog(
                app_instance=self.app_instance,
                shortcut_manager=shortcut_manager,
                parent=self.app_instance
            )
            self.debug_dialog.show()
            self.debug_dialog.raise_()
            self.debug_dialog.activateWindow()
            print("[단축키 디버그] 디버그 창 표시 완료")
        else:
            # 이미 열려있으면 포커스만 이동
            self.debug_dialog.raise_()
            self.debug_dialog.activateWindow()
            print("[단축키 디버그] 디버그 창 포커스 이동")

