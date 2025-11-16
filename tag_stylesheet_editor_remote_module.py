"""
태그 스타일시트 에디터 리모컨 모듈 - 모던 UI 디자인 (레이아웃 수정)
"""

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, 
                               QComboBox, QLineEdit, QCheckBox, QSizePolicy, 
                               QWidget, QGraphicsDropShadowEffect, QApplication, QLayout, QSpinBox, QDoubleSpinBox, QCompleter)

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
        CustomDoubleSpinBox = QDoubleSpinBox  # noqa: F821
        CustomComboBox = QComboBox
except:
    # 실패 시 기본 클래스 사용
    CustomSpinBox = QSpinBox
    CustomDoubleSpinBox = QDoubleSpinBox  # noqa: F821
    CustomComboBox = QComboBox
from PySide6.QtCore import Qt, QTimer, QStringListModel
from PySide6.QtGui import QColor, QFont, QFontMetrics
from pathlib import Path
import csv


# load_tag_list 함수는 tag_autocomplete_plugin으로 이동됨


class TagStyleSheetEditorRemote(QFrame):
    """태그 스타일시트 에디터 리모컨 팝업 - 모던 UI"""
    
    def __init__(self, app_instance=None, parent=None):
        super().__init__(parent)
        self.app_instance = app_instance
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(320, 600)
        self.setMaximumWidth(16777215)  # 최대 폭 제한 완전 제거
        
        self.setup_ui()
        self.setup_autocomplete()
        self.setup_style()
        
    def setup_ui(self):
        """UI 설정 - 모던 디자인"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(0)
        main_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)  # 최소크기 기반으로 내용에 맞게 확장 허용
        
        # 메인 컨테이너 (카드 스타일)
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: #1A1B26;
                border: 1px solid #4A5568;
                border-radius: 16px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 28, 20, 20)
        container_layout.setSpacing(5)
        container_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)  # 최소크기 기반으로 내용에 맞게 확장 허용
        
        # 타이틀
        title = QLabel("Tag Editor")
        title.setStyleSheet("""
            QLabel {
                color: #E2E8F0;
                font-size: 16px;
                font-weight: 700;
                padding-bottom: 4px;
                background: transparent;
                border: none;
            }
        """)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container_layout.addWidget(title)
        
        # 구분선 1
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("""
            QFrame {
                color: #4A5568;
                background-color: #4A5568;
                border: none;
                height: 1px;
            }
        """)
        container_layout.addWidget(separator1)
        
        # 태그 교체 섹션
        replace_section = QFrame()
        replace_section.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                border-radius: 12px;
            }
        """)
        replace_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        replace_section.setMinimumWidth(150)  # 최소 폭을 낮춤
        
        replace_layout = QVBoxLayout(replace_section)
        replace_layout.setContentsMargins(16, 5, 16, 10)
        replace_layout.setSpacing(12)
        
        # 섹션 타이틀과 체크박스
        replace_header_layout = QHBoxLayout()
        class CustomCheckBox(QCheckBox):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setStyleSheet("""
                    QCheckBox {
                        color: #FFFFFF;
                        font-size: 12px;
                        font-weight: 600;
                        spacing: 8px;
                    }
                    /* locked 상태(무태그 시 클릭만 비활성) - 비활성 색상 적용 (에디터와 통일) */
                    QCheckBox[locked="true"] {
                        color: #6B7280;
                    }
                    QCheckBox::indicator {
                        width: 14px;
                        height: 14px;
                        border-radius: 2px;
                        border: 1px solid rgba(255, 255, 255, 0.8);
                        background: rgba(17, 17, 27, 0.9);
                    }
                    QCheckBox::indicator[locked="true"] {
                        border: 1px solid rgba(75,85,99,0.2);
                        background: rgba(26,27,38,0.4);
                    }
                    QCheckBox::indicator:checked {
                        background: rgba(17, 17, 27, 0.9);
                        border: 1px solid rgba(255, 255, 255, 0.8);
                        image: none;
                    }
                    QCheckBox::indicator:checked[locked="true"] {
                        border: 1px solid rgba(75,85,99,0.2);
                        background: rgba(26,27,38,0.4);
                    }
                    QCheckBox::indicator:hover {
                        border: 1px solid rgba(255, 255, 255, 1.0);
                    }
                    QCheckBox::indicator:hover[locked="true"] {
                        border: 1px solid rgba(75,85,99,0.2);
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
                    from PySide6.QtGui import QPainter, QPen, QFont
                    from PySide6.QtCore import QRect, Qt
                    painter = QPainter(self)
                    painter.setRenderHint(QPainter.Antialiasing)
                    # locked 또는 disabled일 때 체크표시는 비활성 색으로
                    is_locked = bool(self.property("locked"))
                    check_color = QColor("#FFFFFF") if (self.isEnabled() and not is_locked) else QColor("#6B7280")
                    painter.setPen(QPen(check_color, 2))
                    painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
                    rect = self.rect()
                    indicator_rect = QRect(1, (rect.height() - 14) // 2, 14, 14)
                    painter.drawText(indicator_rect, Qt.AlignCenter, "🗸")

        self.replace_checkbox = CustomCheckBox()
        self.replace_checkbox.setChecked(True)
        try:
            self.replace_checkbox.setProperty("locked", False)
        except Exception:
            pass
        
        replace_title = QLabel("태그 교체")
        replace_title.setStyleSheet("""
            QLabel {
                color: #CBD5E0;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        replace_title.setFixedHeight(18)
        
        replace_header_layout.addWidget(self.replace_checkbox)
        replace_header_layout.addWidget(replace_title)
        replace_header_layout.addStretch()
        replace_layout.addLayout(replace_header_layout)
        
        # 기존 태그 라벨과 입력 컨테이너
        old_tag_container = QWidget()
        old_tag_container.setContentsMargins(0, 0, 0, 0)
        old_tag_layout = QVBoxLayout(old_tag_container)
        old_tag_layout.setContentsMargins(0, 4, 0, 0)
        old_tag_layout.setSpacing(8)
        
        old_tag_label = QLabel("기존 태그")
        old_tag_label.setStyleSheet("""
            QLabel {
                color: #A0AEC0;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        old_tag_label.setFixedHeight(15)
        old_tag_layout.addWidget(old_tag_label)
        
        self.old_tag_input = QLineEdit()
        self.old_tag_input.setPlaceholderText("교체할 태그명을 입력하세요")
        self.old_tag_input.setFixedHeight(36)
        self.old_tag_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.old_tag_input.setStyleSheet("""
            QLineEdit {
                background: #1A1B26;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3182CE;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #718096;
            }
        """)
        old_tag_layout.addWidget(self.old_tag_input)
        replace_layout.addWidget(old_tag_container)

        # 작업 선택 드롭다운 (기존 태그 아래, 위치 변경 드롭다운과 동일한 디자인/크기)
        operation_container = QWidget()
        operation_container.setContentsMargins(0, 0, 0, 0)
        operation_layout = QVBoxLayout(operation_container)
        operation_layout.setContentsMargins(0, 4, 0, 0)
        operation_layout.setSpacing(8)
        operation_label = QLabel("작업 선택")
        operation_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        operation_label.setFixedHeight(15)
        operation_layout.addWidget(operation_label)
        self.operation_combo = CustomComboBox()
        self.operation_combo.addItems([
            "태그 교체",
            "기존 태그 뒤에 태그 추가",
            "기존 태그 앞에 태그 추가",
            "태그 삭제",
            "새태그를 맨뒤로 추가",
            "새태그를 맨앞으로 추가",
        ])
        self.operation_combo.setFixedHeight(36)
        self.operation_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.operation_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.operation_combo.setStyleSheet("""
            QComboBox {
                background: #1A1B26;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 12px;
            }
            QComboBox:hover {
                border: 1px solid #718096;
            }
            QComboBox:focus {
                border: 1px solid #3182CE;
            }
            QComboBox::drop-down { border: none; width: 0px; }
            QComboBox::down-arrow { image: none; border: none; background: transparent; width: 0px; height: 0px; }
            QComboBox QAbstractItemView {
                background: #1A1B26;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 3px;
                outline: none;
                selection-background-color: #2D3748;
                min-width: 200px;
            }
            QComboBox QAbstractItemView::item {
                background: transparent;
                color: #E2E8F0;
                padding: 6px 10px;
                min-height: 20px;
                min-width: 180px;
            }
            QComboBox QAbstractItemView::item:hover { background: #2D3748; }
            QComboBox QAbstractItemView::item:selected { background: #2D3748; color: #3182CE; }
        """)
        operation_layout.addWidget(self.operation_combo)
        replace_layout.addWidget(operation_container)
        
        # 새 태그 라벨과 입력 컨테이너
        new_tag_container = QWidget()
        new_tag_container.setContentsMargins(0, 0, 0, 0)
        new_tag_layout = QVBoxLayout(new_tag_container)
        new_tag_layout.setContentsMargins(0, 4, 0, 0)
        new_tag_layout.setSpacing(8)
        
        new_tag_label = QLabel("새 태그")
        new_tag_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        new_tag_label.setFixedHeight(15)
        new_tag_layout.addWidget(new_tag_label)
        
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("새 태그명을 입력하세요")
        self.new_tag_input.setFixedHeight(36)
        self.new_tag_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.new_tag_input.setStyleSheet("""
            QLineEdit {
                background: #1A1B26;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3182CE;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #718096;
            }
        """)
        new_tag_layout.addWidget(self.new_tag_input)
        replace_layout.addWidget(new_tag_container)
        # 이동 칸수(추가 동작에서 재사용)
        self.add_step_container = QWidget()
        self.add_step_container.setContentsMargins(0, 0, 0, 0)
        add_step_layout = QVBoxLayout(self.add_step_container)
        add_step_layout.setContentsMargins(0, 4, 0, 0)
        add_step_layout.setSpacing(8)
        self.add_step_label = QLabel("이동 칸수")
        self.add_step_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        self.add_step_label.setFixedHeight(15)
        add_step_layout.addWidget(self.add_step_label)
        self.add_step_input = CustomSpinBox()
        self.add_step_input.setMinimum(1)
        self.add_step_input.setMaximum(999)
        self.add_step_input.setFixedHeight(36)
        self.add_step_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.add_step_input.setStyleSheet("""
            QSpinBox {
                background: #1A1B26;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 12px;
            }
            QSpinBox:hover {
                border: 1px solid #718096;
            }
            QSpinBox:focus {
                border: 1px solid #3182CE;
                outline: none;
            }
            QSpinBox::up-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::down-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::up-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
        """)
        add_step_layout.addWidget(self.add_step_input)
        replace_layout.addWidget(self.add_step_container)
        
        container_layout.addWidget(replace_section)
        
        # 태그 위치 변경 섹션
        position_section = QFrame()
        position_section.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                border-radius: 12px;
            }
        """)
        position_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        position_section.setMinimumWidth(150)  # 최소 폭을 낮춤
        
        position_layout = QVBoxLayout(position_section)
        position_layout.setContentsMargins(16, 5, 16, 10)
        position_layout.setSpacing(12)
        
        # 섹션 타이틀과 체크박스
        position_header_layout = QHBoxLayout()
        self.position_checkbox = CustomCheckBox()
        self.position_checkbox.setChecked(False)
        
        position_title = QLabel("태그 위치 변경")
        position_title.setStyleSheet("""
            QLabel {
                color: #E5E7EB;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        position_title.setFixedHeight(18)
        
        position_header_layout.addWidget(self.position_checkbox)
        position_header_layout.addWidget(position_title)
        position_header_layout.addStretch()
        position_layout.addLayout(position_header_layout)
        
        # 이동할 태그 컨테이너
        move_tag_container = QWidget()
        move_tag_container.setContentsMargins(0, 0, 0, 0)
        move_tag_layout = QVBoxLayout(move_tag_container)
        move_tag_layout.setContentsMargins(0, 4, 0, 0)
        move_tag_layout.setSpacing(8)
        
        move_tag_label = QLabel("이동할 태그")
        move_tag_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        move_tag_label.setFixedHeight(15)
        move_tag_layout.addWidget(move_tag_label)
        
        self.move_tag_input = QLineEdit()
        self.move_tag_input.setPlaceholderText("이동할 태그명을 입력하세요")
        self.move_tag_input.setFixedHeight(36)
        self.move_tag_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.move_tag_input.setStyleSheet("""
            QLineEdit {
                background: #1A1B26;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3182CE;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #718096;
            }
        """)
        move_tag_layout.addWidget(self.move_tag_input)
        position_layout.addWidget(move_tag_container)
        
        # 이동 위치 컨테이너
        position_type_container = QWidget()
        position_type_container.setContentsMargins(0, 0, 0, 0)
        position_type_layout = QVBoxLayout(position_type_container)
        position_type_layout.setContentsMargins(0, 4, 0, 0)
        position_type_layout.setSpacing(8)
        
        position_type_label = QLabel("이동 위치")
        position_type_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        position_type_label.setFixedHeight(15)
        position_type_layout.addWidget(position_type_label)
        
        self.position_type_combo = CustomComboBox()
        self.position_type_combo.addItems(["맨 앞으로", "맨 뒤로", "특정 태그 앞으로", "특정 태그 뒤로"])
        self.position_type_combo.setFixedHeight(36)
        self.position_type_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.position_type_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)  # 내용에 맞춰 크기 조정
        self.position_type_combo.setStyleSheet("""
            QComboBox {
                background: #1A1B26;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 12px;
            }
            QComboBox:hover {
                border: 1px solid #718096;
            }
            QComboBox:focus {
                border: 1px solid #3182CE;
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
                background: #1A1B26;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 3px;
                outline: none;
                selection-background-color: #2D3748;
                min-width: 200px;
            }
            QComboBox QAbstractItemView::item {
                background: transparent;
                color: #E2E8F0;
                padding: 6px 10px;
                min-height: 20px;
                min-width: 180px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #2D3748;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #2D3748;
                color: #3182CE;
            }
        """)
        position_type_layout.addWidget(self.position_type_combo)
        position_layout.addWidget(position_type_container)
        
        # 기준 태그 컨테이너 (조건부 표시)
        self.reference_container = QWidget()
        self.reference_container.setContentsMargins(0, 0, 0, 0)
        reference_layout = QVBoxLayout(self.reference_container)
        reference_layout.setContentsMargins(0, 4, 0, 0)
        reference_layout.setSpacing(8)
        
        self.reference_tag_label = QLabel("기준 태그")
        self.reference_tag_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        self.reference_tag_label.setFixedHeight(15)
        reference_layout.addWidget(self.reference_tag_label)
        
        self.reference_tag_input = QLineEdit()
        self.reference_tag_input.setPlaceholderText("기준 태그명을 입력하세요")
        self.reference_tag_input.setFixedHeight(36)
        self.reference_tag_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.reference_tag_input.setStyleSheet("""
            QLineEdit {
                background: #1A1B26;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3182CE;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #718096;
            }
        """)
        reference_layout.addWidget(self.reference_tag_input)
        
        # 이동 칸수 설정 컨테이너
        self.step_container = QWidget()
        self.step_container.setContentsMargins(0, 0, 0, 0)
        step_layout = QVBoxLayout(self.step_container)
        step_layout.setContentsMargins(0, 4, 0, 0)
        step_layout.setSpacing(8)
        
        self.step_label = QLabel("이동 칸수")
        self.step_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        self.step_label.setFixedHeight(15)
        step_layout.addWidget(self.step_label)
        
        self.step_input = CustomSpinBox()
        self.step_input.setMinimum(1)
        self.step_input.setMaximum(999)
        self.step_input.setValue(1)  # 기본값
        self.step_input.setFixedHeight(36)
        self.step_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.step_input.setStyleSheet("""
            QSpinBox {
                background: #1A1B26;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0px 10px;
                font-size: 12px;
            }
            QSpinBox:hover {
                border: 1px solid #718096;
            }
            QSpinBox:focus {
                border: 1px solid #3182CE;
                outline: none;
            }
            QSpinBox::up-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::down-button {
                background: transparent;
                border: none;
                width: 20px;
            }
            QSpinBox::up-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
            QSpinBox::down-arrow {
                image: none;
                border: none;
                background: transparent;
                width: 0px;
                height: 0px;
            }
        """)
        step_layout.addWidget(self.step_input)
        
        position_layout.addWidget(self.reference_container)
        position_layout.addWidget(self.step_container)
        container_layout.addWidget(position_section)
        
        # 스페이서 - 남은 공간을 채움
        container_layout.addStretch(1)
        
        # 옵션
        option_container = QWidget()
        option_container.setFixedHeight(36)
        option_layout = QHBoxLayout(option_container)
        option_layout.setContentsMargins(4, 8, 4, 0)
        
        self.preview_checkbox = CustomCheckBox("현재 태그 일괄 사용")
        self.preview_checkbox.setChecked(True)
        try:
            self.preview_checkbox.setProperty("locked", False)
        except Exception:
            pass
        option_layout.addWidget(self.preview_checkbox)
        option_layout.addStretch()
        
        container_layout.addWidget(option_container)
        
        # 버튼 섹션
        button_container = QWidget()
        button_container.setFixedHeight(36)
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(12)
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #4A5568;
                color: #CBD5E0;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #718096;
            }
            QPushButton:pressed {
                background: #2D3748;
            }
        """)
        button_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("적용")
        self.apply_btn.setMinimumWidth(100)
        self.apply_btn.setFixedHeight(36)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #60A5FA;
            }
            QPushButton:pressed {
                background: #1D4ED8;
            }
        """)
        button_layout.addWidget(self.apply_btn)
        
        container_layout.addWidget(button_container)
        
        # 메인 레이아웃에 컨테이너 추가
        main_layout.addWidget(container)
        
        # 이벤트 연결
        self.position_type_combo.currentTextChanged.connect(self.on_position_type_changed)
        self.preview_checkbox.toggled.connect(self.on_bulk_mode_toggled)
        self.replace_checkbox.toggled.connect(self.on_replace_checkbox_toggled)
        self.position_checkbox.toggled.connect(self.on_position_checkbox_toggled)
        self.operation_combo.currentTextChanged.connect(self.on_operation_changed)
        self.cancel_btn.clicked.connect(self.close)
        self.apply_btn.clicked.connect(self.apply_changes)

        # 초기 진입 시: 기본 선택은 '태그 교체', 이동 칸수/기준 필드 숨김
        try:
            self.operation_combo.setCurrentText("태그 교체")
        except Exception:
            pass
        self.on_operation_changed("태그 교체")
        self.on_position_type_changed(self.position_type_combo.currentText())
        # 입력/에디터 변화에 따른 '현재 태그 일괄 사용' 락 상태 갱신
        try:
            self.old_tag_input.textChanged.connect(self._update_preview_checkbox_lock_state)
            self.move_tag_input.textChanged.connect(self._update_preview_checkbox_lock_state)
        except Exception:
            pass
        try:
            if hasattr(self.app_instance, 'tag_stylesheet_editor') and hasattr(self.app_instance.tag_stylesheet_editor, 'tags_changed'):
                self.app_instance.tag_stylesheet_editor.tags_changed.connect(self._update_preview_checkbox_lock_state_from_editor)
        except Exception:
            pass
        
        # 초기 상태
        self.on_position_type_changed("맨 앞으로")
        self.on_bulk_mode_toggled(True)  # 초기에 체크박스가 체크되어 있으므로 비활성화
        QTimer.singleShot(0, self._update_preview_checkbox_lock_state)
    
    def on_position_type_changed(self, position_type):
        """위치 변경 유형에 따라 기준 태그 필드와 이동 칸수 필드 표시/숨김"""
        if position_type in ["특정 태그 앞으로", "특정 태그 뒤로"]:
            self.reference_container.setVisible(True)
            self.step_container.setVisible(True)
        else:
            self.reference_container.setVisible(False)
            self.step_container.setVisible(False)

    def on_operation_changed(self, op_text):
        """작업 선택 드롭다운 변경 시 입력 필드 토글"""
        # 기본: 교체 UI 보이기
        show_old = True
        show_new = True
        show_add_step = False
        if op_text == "태그 교체":
            show_old, show_new = True, True
            show_add_step = False
        elif op_text == "태그 삭제":
            show_old, show_new = True, False
            show_add_step = False
        elif op_text in ("기존 태그 뒤에 태그 추가", "기존 태그 앞에 태그 추가"):
            show_old, show_new = True, True
            show_add_step = True
        elif op_text in ("새태그를 맨뒤로 추가", "새태그를 맨앞으로 추가"):
            show_old, show_new = True, True  # 기존 태그 입력은 선택적이지만 일관성 위해 유지
            show_add_step = False
        try:
            self.old_tag_input.parentWidget().setVisible(show_old)
        except Exception:
            pass
        try:
            self.new_tag_input.parentWidget().setVisible(show_new)
        except Exception:
            pass
        try:
            self.add_step_container.setVisible(show_add_step)
        except Exception:
            pass
        
        # 필드 표시/숨김 후 자동 리사이즈 (약간의 지연 후)
        QTimer.singleShot(50, self.auto_resize_window)
    
    def auto_resize_window(self):
        """내용에 맞게 윈도우 크기를 자동 조정하고 화면 경계 내로 클램프"""
        # 현재 표시된 필드에 따라 적절한 크기 계산
        reference_visible = self.reference_container.isVisible()
        step_visible = self.step_container.isVisible()
        
        print(f"Debug: reference_visible={reference_visible}, step_visible={step_visible}")
        
        if reference_visible and step_visible:
            # 필드가 모두 표시된 경우 - 확장
            print("Debug: 확장 모드")
            self.adjustSize()
        else:
            # 필드가 숨겨진 경우 - 축소
            print("Debug: 축소 모드")
            # 먼저 adjustSize()로 최소 크기로 조정
            self.adjustSize()
            # 그 다음 숨겨진 필드들의 높이만큼 추가로 축소
            current_size = self.size()
            # 숨겨진 필드들의 높이 (라벨 + 입력필드 + 여백) 대략 80px
            new_height = max(self.minimumHeight(), current_size.height() - 80)
            print(f"Debug: current_height={current_size.height()}, new_height={new_height}")
            self.resize(current_size.width(), new_height)
        
        # 화면 경계 내로 클램프
        screen_geometry = self.screen().availableGeometry()
        current_geometry = self.geometry()
        
        # 화면을 벗어나지 않도록 조정
        if current_geometry.right() > screen_geometry.right():
            new_x = screen_geometry.right() - current_geometry.width()
            self.move(new_x, current_geometry.y())
        
        if current_geometry.bottom() > screen_geometry.bottom():
            new_y = screen_geometry.bottom() - current_geometry.height()
            self.move(current_geometry.x(), new_y)
    
    def on_bulk_mode_toggled(self, checked):
        """일괄 모드 토글에 따라 입력 필드 활성화/비활성화"""
        # 기존 태그 입력 필드
        self.old_tag_input.setEnabled(not checked)
        
        # 이동할 태그 입력 필드
        self.move_tag_input.setEnabled(not checked)
        
        # 일괄 모드일 때 에디터의 칩 태그들로 자동 채우기
        if checked and self.app_instance:
            self.fill_fields_with_editor_tags()
        
        # 비활성화 시 스타일 변경
        if checked:
            self.old_tag_input.setStyleSheet("""
                QLineEdit {
                    background: #1A1B26;
                    color: #718096;
                    border: 1px solid #4A5568;
                    border-radius: 6px;
                    padding: 0px 10px;
                    font-size: 12px;
                }
            """)
            self.move_tag_input.setStyleSheet("""
                QLineEdit {
                    background: #1A1B26;
                    color: #718096;
                    border: 1px solid #4A5568;
                    border-radius: 6px;
                    padding: 0px 10px;
                    font-size: 12px;
                }
            """)
        else:
            # 수동 모드로 전환 시 필드는 초기화하지 않음 (현재 태그 유지)
            # self.old_tag_input.clear()  # 현재 태그 유지를 위해 주석 처리
            # self.move_tag_input.clear()  # 현재 태그 유지를 위해 주석 처리
            
            self.old_tag_input.setStyleSheet("""
                QLineEdit {
                    background: #1A1B26;
                    color: #E2E8F0;
                    border: 1px solid #4A5568;
                    border-radius: 6px;
                    padding: 0px 10px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border: 1px solid #3182CE;
                    outline: none;
                }
                QLineEdit::placeholder {
                    color: #718096;
                }
            """)
            self.move_tag_input.setStyleSheet("""
                QLineEdit {
                    background: #1A1B26;
                    color: #E2E8F0;
                    border: 1px solid #4A5568;
                    border-radius: 6px;
                    padding: 0px 10px;
                    font-size: 12px;
                }
                QLineEdit:focus {
                    border: 1px solid #3182CE;
                    outline: none;
                }
                QLineEdit::placeholder {
                    color: #718096;
                }
            """)
        
    def setup_style(self):
        """전체 윈도우 스타일 설정"""
        self.setStyleSheet("""
            TagStyleSheetEditorRemote {
                background: transparent;
                border: none;
            }
        """)
        
        # 윈도우 배경을 투명하게 설정
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # 부드러운 그림자 효과
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)
    
    def setup_autocomplete(self):
        """자동완성 기능 설정 - 지연 로딩 적용 (이미지 태깅 모듈과 동일)"""
        # 초기에는 빈 모델로 설정 (빠른 초기화)
        self.original_tag_list = []
        self.tag_model = QStringListModel([])
        
        # QCompleter 생성 및 설정
        self.completer = QCompleter()
        self.completer.setModel(self.tag_model)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setMaxVisibleItems(4)  # 표시 개수 4개로 제한
        self.completer.setFilterMode(Qt.MatchContains)  # 중간부터 일치하는 것도 포함
        
        # QCompleter의 필터 모델을 커스텀으로 설정
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        
        # 한글 입력 지원을 위한 타이머 설정 (디바운싱)
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(500)  # 500ms 딜레이 (한글 조합 대기)
        self.filter_timer.timeout.connect(self.do_filter_completions)
        
        # 페이징 관련 변수
        self.current_search_results = []  # 전체 검색 결과
        self.current_page_size = 50  # 한 번에 표시할 개수
        self.current_displayed_count = 0  # 현재 표시된 개수
        self.is_loading_more = False  # 추가 로딩 중 플래그
        self.full_tag_list_loaded = False  # 전체 태그 목록 로드 여부
        
        # 커스텀 델리게이트 설정
        from tag_autocomplete_plugin import KRDanbooruCompleterDelegate
        custom_delegate = KRDanbooruCompleterDelegate()
        self.completer.popup().setItemDelegate(custom_delegate)
        
        # 스크롤 이벤트 연결 (무한 스크롤)
        popup = self.completer.popup()
        scrollbar = popup.verticalScrollBar()
        scrollbar.valueChanged.connect(self.on_completer_scroll)
        
        # popup 설정 - 폭 500px 고정, 설명/키워드는 자동 줄바꿈
        from PySide6.QtWidgets import QAbstractItemView
        popup.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        popup.setMaximumHeight(400)  # 높이를 늘려서 여러 줄 표시 가능하도록
        
        # 폭 500px로 고정 (설명/키워드는 델리게이트에서 자동 줄바꿈)
        popup.setMinimumWidth(500)
        popup.setMaximumWidth(500)
        popup.resize(500, 400)
        
        # 자동완성 팝업 스타일 설정 (전역 스크롤바 스타일 포함)
        self.completer.popup().setStyleSheet("""
                QListView {
                    background: rgba(17,17,27,0.95);
                    border: 1px solid rgba(75,85,99,0.3);
                    border-radius: 6px;
                    color: #F9FAFB;
                    font-size: 12px;
                    padding: 4px;
                }
                QListView::item {
                    padding: 6px 8px;
                    border-radius: 4px;
                    margin: 1px;
                }
                QListView::item:selected {
                    background: rgba(59,130,246,0.3);
                    color: #FFFFFF;
                }
                QListView::item:hover {
                    background: rgba(75,85,99,0.2);
                }
                QScrollBar:vertical {
                    background: rgba(26,27,38,0.8);
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(75,85,99,0.6);
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(75,85,99,0.8);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: rgba(26,27,38,1.0);
                }
        """)
        
        # 모든 태그 입력 필드에 자동완성 적용
        self.setup_input_autocomplete(self.old_tag_input)
        self.setup_input_autocomplete(self.new_tag_input)
        self.setup_input_autocomplete(self.move_tag_input)
        self.setup_input_autocomplete(self.reference_tag_input)
        
        # 지연 로딩: 1초 후에 태그 목록 로드
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.load_initial_tags)
        self.load_timer.start(1000)  # 1초 후 로드
        
        print("자동완성 설정 완료 (지연 로딩 적용)")

    def load_initial_tags(self):
        """초기 태그 목록 로드 (지연 로딩)"""
        try:
            from tag_autocomplete_plugin import load_tag_list
            tag_list = load_tag_list()
            
            if tag_list:
                # 원본 태그 목록 저장 (필터링용)
                self.original_tag_list = tag_list.copy()
                
                # 모델 업데이트
                self.tag_model.setStringList(tag_list)
                
                # 모든 입력 필드의 completer 모델 업데이트
                self.setup_input_autocomplete(self.old_tag_input)
                self.setup_input_autocomplete(self.new_tag_input)
                self.setup_input_autocomplete(self.move_tag_input)
                self.setup_input_autocomplete(self.reference_tag_input)
                
                print(f"초기 태그 목록 로드 완료: {len(tag_list)}개 태그")
            else:
                print("태그 목록 로드 실패")
        except Exception as e:
            print(f"초기 태그 로드 오류: {e}")
    
    def load_full_tags_if_needed(self):
        """필요시 전체 태그 목록 로드"""
        if not self.full_tag_list_loaded:
            try:
                from tag_autocomplete_plugin import load_full_tag_list
                full_tag_list = load_full_tag_list()
                
                if full_tag_list:
                    self.original_tag_list = full_tag_list.copy()
                    self.tag_model.setStringList(full_tag_list)
                    self.full_tag_list_loaded = True
                    print(f"전체 태그 목록 로드 완료: {len(full_tag_list)}개 태그")
            except Exception as e:
                print(f"전체 태그 로드 오류: {e}")
    
    def schedule_filter(self, text, input_field):
        """타이머를 사용한 필터링 예약 (한글 입력 지원)"""
        self.pending_filter_text = text
        self.pending_filter_field = input_field
        self.filter_timer.stop()
        self.filter_timer.start()
    
    def do_filter_completions(self):
        """실제 필터링 수행"""
        if hasattr(self, 'pending_filter_text') and hasattr(self, 'pending_filter_field'):
            self.filter_completions(self.pending_filter_text, self.pending_filter_field)
    
    def filter_completions(self, text, input_field):
        """커스텀 필터링으로 우선순위 정렬 (KR_danbooru_tags.csv 기반) - 페이징 지원"""
        try:
            # 검색할 때만 전체 태그 목록 로드
            if not self.full_tag_list_loaded:
                self.load_full_tags_if_needed()
            
            from kr_danbooru_loader import kr_danbooru_loader
            
            print(f"필터링 검색: '{text}'")
            print(f"로더 상태: is_available={kr_danbooru_loader.is_available}, 태그 수={len(kr_danbooru_loader.tags)}")
            
            if not kr_danbooru_loader.is_available:
                print("로더가 사용 불가능합니다.")
                return
            
            # 해당 입력 필드의 completer 가져오기
            field_completer = input_field.completer()
            if not field_completer:
                return
            
            if not text.strip():
                # 텍스트가 비어있으면 모든 태그를 카운트 순으로 표시
                all_tags = kr_danbooru_loader.get_autocomplete_list()
                print(f"빈 검색 - 전체 태그: {len(all_tags)}개")
                
                # 전체 결과 저장 및 첫 페이지만 표시
                self.current_search_results = all_tags
                self.current_displayed_count = min(self.current_page_size, len(all_tags))
                displayed_tags = all_tags[:self.current_displayed_count]
                
                # 더 표시할 결과가 있으면 "더 보기" 항목 추가
                if self.current_displayed_count < len(all_tags):
                    displayed_tags.append(f"--- 더 보기 ({len(all_tags) - self.current_displayed_count}개 더) ---")
                
                # 필드별 모델 생성 및 설정
                field_model = QStringListModel(displayed_tags)
                field_completer.setModel(field_model)
                print(f"표시: {self.current_displayed_count}/{len(all_tags)}개")
                return
            
            # KR_danbooru_loader의 검색 기능 사용
            search_results = kr_danbooru_loader.search_tags(text)
            print(f"검색 결과: {len(search_results)}개")
            
            # 검색 결과를 태그명만 추출
            filtered_tags = [name for name, _, _ in search_results]
            
            # 전체 결과 저장 및 첫 페이지만 표시
            self.current_search_results = filtered_tags
            self.current_displayed_count = min(self.current_page_size, len(filtered_tags))
            displayed_tags = filtered_tags[:self.current_displayed_count]
            
            # 더 표시할 결과가 있으면 "더 보기" 항목 추가
            if self.current_displayed_count < len(filtered_tags):
                displayed_tags.append(f"--- 더 보기 ({len(filtered_tags) - self.current_displayed_count}개 더) ---")
            
            # 필드별 모델 생성 및 설정
            field_model = QStringListModel(displayed_tags)
            field_completer.setModel(field_model)
            field_completer.complete()  # 자동완성 팝업 강제 표시
            
            print(f"표시: {self.current_displayed_count}/{len(filtered_tags)}개")
            
        except Exception as e:
            print(f"필터링 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def on_completer_scroll(self, value):
        """자동완성 팝업 스크롤 이벤트 - 무한 스크롤"""
        try:
            scrollbar = self.sender()  # 스크롤바가 sender
            if not scrollbar:
                return
            
            # 스크롤이 맨 아래에 도달했는지 확인
            if value >= scrollbar.maximum() - 10:  # 여유를 두고 10픽셀 전에 로드
                # 더 표시할 결과가 있는지 확인
                if self.current_displayed_count < len(self.current_search_results):
                    print(f"스크롤 끝 도달 - 다음 페이지 로드")
                    self.load_more_results()
        except Exception as e:
            print(f"스크롤 이벤트 오류: {e}")
    
    def load_more_results(self):
        """다음 페이지 결과 로드"""
        try:
            if self.is_loading_more:
                print("이미 로딩 중")
                return
            
            self.is_loading_more = True
            
            # 다음 페이지의 시작과 끝 인덱스 계산
            start_idx = self.current_displayed_count
            end_idx = min(start_idx + self.current_page_size, len(self.current_search_results))
            
            if start_idx >= len(self.current_search_results):
                print("더 이상 로드할 결과 없음")
                self.is_loading_more = False
                return
            
            # 현재 활성화된 입력 필드의 completer 찾기
            active_field = None
            for field in [self.old_tag_input, self.new_tag_input, self.move_tag_input, self.reference_tag_input]:
                if field.hasFocus():
                    active_field = field
                    break
            
            if not active_field:
                self.is_loading_more = False
                return
            
            field_completer = active_field.completer()
            if not field_completer:
                self.is_loading_more = False
                return
            
            # 현재 모델의 태그 목록 가져오기
            current_model = field_completer.model()
            if current_model:
                current_tags = current_model.stringList()
                
                # 마지막 "더 보기" 항목 제거
                if current_tags and current_tags[-1].startswith("---"):
                    current_tags = current_tags[:-1]
                
                new_tags = self.current_search_results[start_idx:end_idx]
                all_tags = current_tags + new_tags
                
                # 더 표시할 결과가 있으면 "더 보기" 항목 추가
                remaining = len(self.current_search_results) - end_idx
                if remaining > 0:
                    all_tags.append(f"--- 더 보기 ({remaining}개 더) ---")
                
                # 모델 업데이트
                field_model = QStringListModel(all_tags)
                field_completer.setModel(field_model)
                self.current_displayed_count = end_idx
                
                print(f"추가 로드: {len(new_tags)}개 (총 {self.current_displayed_count}/{len(self.current_search_results)})")
            
            self.is_loading_more = False
            
        except Exception as e:
            print(f"추가 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            self.is_loading_more = False
    
    def setup_input_autocomplete(self, input_field):
        """개별 입력 필드에 자동완성 설정 (이미지 태깅 모듈과 동일)"""
        # 각 입력 필드마다 별도의 completer 인스턴스 생성
        field_completer = QCompleter()
        field_completer.setModel(self.tag_model)
        field_completer.setCaseSensitivity(Qt.CaseInsensitive)
        field_completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        field_completer.setMaxVisibleItems(4)
        field_completer.setFilterMode(Qt.MatchContains)
        
        # 커스텀 델리게이트 설정
        from tag_autocomplete_plugin import KRDanbooruCompleterDelegate
        custom_delegate = KRDanbooruCompleterDelegate()
        field_completer.popup().setItemDelegate(custom_delegate)
        
        # 스크롤 이벤트 연결 (무한 스크롤)
        popup = field_completer.popup()
        scrollbar = popup.verticalScrollBar()
        scrollbar.valueChanged.connect(self.on_completer_scroll)
        
        # popup 설정 - 폭 500px 고정, 설명/키워드는 자동 줄바꿈
        from PySide6.QtWidgets import QAbstractItemView
        popup.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        popup.setMaximumHeight(400)  # 높이를 늘려서 여러 줄 표시 가능하도록
        
        # 폭 500px로 고정 (설명/키워드는 델리게이트에서 자동 줄바꿈)
        popup.setMinimumWidth(500)
        popup.setMaximumWidth(500)
        popup.resize(500, 400)
        
        # 한글 입력 지원을 위한 텍스트 변경 이벤트 연결
        def on_text_changed(text):
            # 입력 필드의 전체 텍스트 가져오기 (한글 조합 중인 텍스트 포함)
            full_text = text
            if hasattr(input_field, 'preedit_text'):
                full_text = text + getattr(input_field, 'preedit_text', '')
            self.schedule_filter(full_text, input_field)
        
        input_field.textChanged.connect(on_text_changed)
        
        # 한글 입력 지원을 위한 inputMethodEvent 오버라이드
        original_input_method_event = input_field.inputMethodEvent
        def custom_input_method_event(event):
            original_input_method_event(event)
            # preedit string (조합 중인 텍스트) 저장
            input_field.preedit_text = event.preeditString()
            # 필터링 트리거
            full_text = input_field.text() + input_field.preedit_text
            self.schedule_filter(full_text, input_field)
        
        input_field.inputMethodEvent = custom_input_method_event
        
        # 동일한 스타일 적용 (전역 스크롤바 스타일 포함)
        field_completer.popup().setStyleSheet("""
            QListView {
                background: rgba(17,17,27,0.95);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 6px;
                color: #F9FAFB;
                font-size: 12px;
                padding: 4px;
            }
            QListView::item {
                padding: 6px 8px;
                border-radius: 4px;
                margin: 1px;
            }
            QListView::item:selected {
                background: rgba(59,130,246,0.3);
                color: #FFFFFF;
            }
            QListView::item:hover {
                background: rgba(75,85,99,0.2);
            }
            QScrollBar:vertical {
                background: rgba(26,27,38,0.8);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(75,85,99,0.6);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(75,85,99,0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: rgba(26,27,38,1.0);
            }
        """)
        
        input_field.setCompleter(field_completer)
    
    def show_remote(self):
        """리모컨 표시"""
        # 화면 왼쪽 아래 구석에 위치 설정
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        # 윈도우 크기 고려하여 왼쪽 아래 구석 계산
        x = 20  # 왼쪽에서 20px 여백
        y = screen_geometry.height() - self.height() - 20  # 아래에서 20px 여백
        
        # 하단 기준 고정 좌표 저장
        try:
            self._bottom_margin = 20
        except Exception:
            pass
        self.move(x, y)
        self.show()
        
        # 일괄 모드가 체크되어 있으면 자동으로 필드 채우기
        if self.preview_checkbox.isChecked() and self.app_instance:
            print("리모트 창 열림: 일괄 모드 자동 필드 채우기")
            self.fill_fields_with_editor_tags()
            
        # 에디터의 태그 변경 시그널 연결 (실시간 업데이트)
        if self.app_instance and hasattr(self.app_instance, 'tag_stylesheet_editor'):
            editor = self.app_instance.tag_stylesheet_editor
            editor.tags_changed.connect(self.on_editor_tags_changed)
            print("에디터 태그 변경 시그널 연결 완료")

    def resizeEvent(self, event):
        """리사이즈 시 아래쪽(바닥) 위치를 유지하고 위로 확장"""
        try:
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            bottom_margin = getattr(self, '_bottom_margin', 20)
            x = self.x()
            y = screen_geometry.height() - self.height() - bottom_margin
            super().resizeEvent(event)
            self.move(x, y)
        except Exception:
            try:
                super().resizeEvent(event)
            except Exception:
                pass
    
    def hide_remote(self):
        """리모컨 숨김"""
        # 에디터의 태그 변경 시그널 연결 해제
        if self.app_instance and hasattr(self.app_instance, 'tag_stylesheet_editor'):
            editor = self.app_instance.tag_stylesheet_editor
            try:
                editor.tags_changed.disconnect(self.on_editor_tags_changed)
                print("에디터 태그 변경 시그널 연결 해제 완료")
            except TypeError:
                # 연결이 없었던 경우 무시
                pass
        
        self.hide()
    
    def fill_fields_with_editor_tags(self):
        """에디터의 칩 태그들로 입력 필드 자동 채우기"""
        print("fill_fields_with_editor_tags 호출")
        
        if not self.app_instance or not hasattr(self.app_instance, 'tag_stylesheet_editor'):
            print("❌ app_instance 또는 tag_stylesheet_editor가 없음")
            return
        
        editor = self.app_instance.tag_stylesheet_editor
        if not editor.selected_tags:
            print("❌ 에디터에 선택된 태그가 없음")
            return
        
        # 에디터의 선택된 태그들을 쉼표로 구분하여 문자열로 변환
        tags_text = ", ".join(editor.selected_tags)
        print(f"에디터 선택된 태그들: {tags_text}")
        
        # 다중 태그를 쉼표로 구분하여 설정 (교체용)
        if editor.selected_tags:
            tags_text = ", ".join(editor.selected_tags)
            self.old_tag_input.setText(tags_text)
            print(f"기존 태그 필드에 설정: '{tags_text}'")
        
        # 다중 태그를 쉼표로 구분하여 설정 (위치 변경용)
        if editor.selected_tags:
            tags_text = ", ".join(editor.selected_tags)
            self.move_tag_input.setText(tags_text)
            print(f"이동할 태그 필드에 설정: '{tags_text}'")
        
        print(f"일괄 모드: 에디터 태그들로 필드 채움 완료 - {tags_text}")
    
    def on_editor_tags_changed(self, selected_tags):
        """에디터의 태그가 변경될 때 호출 (실시간 업데이트)"""
        print(f"에디터 태그 변경 감지: {selected_tags}")

        # 입력 필드 자동 채우기는 기존 조건 유지하되, 스킵 로그는 제거
        if (self.preview_checkbox.isChecked() and 
            not self.old_tag_input.isEnabled() and 
            not self.move_tag_input.isEnabled()):
            if selected_tags:
                self.fill_fields_with_editor_tags()
            else:
                self.old_tag_input.clear()
                self.move_tag_input.clear()

        # 카드 태그 라벨은 항상 실시간 갱신 (이미지는 유지)
        try:
            if hasattr(self.app_instance, 'tag_stylesheet_editor') and self.app_instance.tag_stylesheet_editor:
                self.app_instance.tag_stylesheet_editor.refresh_card_tags()
        except Exception:
            pass
    
    def on_replace_checkbox_toggled(self, checked):
        """태그 교체 체크박스 토글"""
        if checked:
            # 태그 교체가 체크되면 태그 위치 변경 체크 해제
            self.position_checkbox.setChecked(False)
            print("태그 교체 선택됨")
        else:
            # 태그 교체가 해제되면 태그 위치 변경을 자동으로 체크 (최소 하나는 선택되어야 함)
            if not self.position_checkbox.isChecked():
                self.position_checkbox.setChecked(True)
                print("태그 교체 해제됨 - 태그 위치 변경 자동 선택")
            else:
                print("태그 교체 해제됨")
    
    def on_position_checkbox_toggled(self, checked):
        """태그 위치 변경 체크박스 토글"""
        if checked:
            # 태그 위치 변경이 체크되면 태그 교체 체크 해제
            self.replace_checkbox.setChecked(False)
            print("태그 위치 변경 선택됨")
        else:
            # 태그 위치 변경이 해제되면 태그 교체를 자동으로 체크 (최소 하나는 선택되어야 함)
            if not self.replace_checkbox.isChecked():
                self.replace_checkbox.setChecked(True)
                print("태그 위치 변경 해제됨 - 태그 교체 자동 선택")
            else:
                print("태그 위치 변경 해제됨")
    
    def apply_changes(self):
        """변경사항 적용"""
        print("변경사항 적용 시작")
        
        # app_instance 확인
        if not self.app_instance:
            print("❌ app_instance가 없습니다 (단독 실행 모드)")
            return
        
        # 에디터 인스턴스 확인
        if not hasattr(self.app_instance, 'tag_stylesheet_editor') or not self.app_instance.tag_stylesheet_editor:
            print("❌ 태그 스타일시트 에디터가 없습니다")
            return
        
        editor = self.app_instance.tag_stylesheet_editor
        
        # 일괄 모드이고 필드가 비어있으면 자동으로 채우기
        if self.preview_checkbox.isChecked():
            old_tag = self.old_tag_input.text().strip()
            move_tag = self.move_tag_input.text().strip()
            if not old_tag or not move_tag:
                print("일괄 모드에서 필드가 비어있어서 자동으로 채움")
                self.fill_fields_with_editor_tags()
        
        # 현재 에디터에서 표시 중인 이미지 목록 가져오기
        target_images = self.get_target_images(editor)
        if not target_images:
            print("❌ 대상 이미지가 없습니다")
            return
        
        print(f"대상 이미지: {len(target_images)}개")
        
        # 일괄 모드인지 확인
        is_bulk_mode = self.preview_checkbox.isChecked()
        print(f"일괄 모드: {is_bulk_mode}")
        
        # 입력 필드 값 확인
        old_tag = self.old_tag_input.text().strip()
        new_tag = self.new_tag_input.text().strip()
        move_tag = self.move_tag_input.text().strip()
        
        print(f"입력 필드 값:")
        print(f"  기존 태그: '{old_tag}'")
        print(f"  새 태그: '{new_tag}'")
        print(f"  이동할 태그: '{move_tag}'")
        
        # 작업 선택값
        op_text = getattr(self, 'operation_combo').currentText() if hasattr(self, 'operation_combo') else "태그 교체"

        # 태그 교체 작업
        if op_text == "태그 교체" and old_tag and new_tag:
            print("태그 교체 작업 수행")
            if is_bulk_mode:
                # 일괄 모드: 에디터의 모든 태그들을 순차적으로 교체
                self.apply_bulk_tag_replace(editor, target_images)
            else:
                # 수동 모드: 입력된 태그만 교체
                self.apply_tag_replace(editor, target_images)
        elif op_text == "태그 교체":
            print("태그 교체 작업 스킵 (입력 필드 비어있음)")
        
        # 태그 삭제 작업
        if op_text == "태그 삭제" and old_tag:
            print("태그 삭제 작업 수행")
            self.apply_tag_delete(editor, target_images)
        elif op_text == "태그 삭제":
            print("태그 삭제 작업 스킵 (입력 필드 비어있음)")
        
        # 태그 위치 변경 작업 (체크박스가 체크된 경우만)
        if self.position_checkbox.isChecked() and move_tag:
            print("태그 위치 변경 작업 수행")
            if is_bulk_mode:
                # 일괄 모드: 에디터의 모든 태그들을 순차적으로 위치 변경
                self.apply_bulk_tag_position_change(editor, target_images)
            else:
                # 수동 모드: 입력된 태그만 위치 변경
                self.apply_tag_position_change(editor, target_images)
        elif self.position_checkbox.isChecked():
            print("태그 위치 변경 작업 스킵 (입력 필드 비어있음)")
        
        # 추가 작업: 기존 태그 기준 앞/뒤 추가
        if op_text in ("기존 태그 뒤에 태그 추가", "기존 태그 앞에 태그 추가") and old_tag and new_tag:
            print(f"태그 추가 작업 수행: {op_text}")
            self.apply_tag_insert_relative(editor, target_images, after=(op_text == "기존 태그 뒤에 태그 추가"))
        elif op_text in ("기존 태그 뒤에 태그 추가", "기존 태그 앞에 태그 추가"):
            print("태그 추가 작업 스킵 (입력 필드 비어있음)")
        
        # 추가 작업: 맨앞/맨뒤 추가
        if op_text in ("새태그를 맨뒤로 추가", "새태그를 맨앞으로 추가") and new_tag:
            print(f"태그 추가 작업 수행: {op_text}")
            self.apply_tag_append_edge(editor, target_images, to_front=(op_text == "새태그를 맨앞으로 추가"))
        elif op_text in ("새태그를 맨뒤로 추가", "새태그를 맨앞으로 추가"):
            print("태그 추가 작업 스킵 (입력 필드 비어있음)")
        
        # UI 업데이트
        self.update_ui_after_changes(editor)
        
        print("✅ 변경사항 적용 완료")
    
    def get_target_images(self, editor):
        """에디터에서 현재 표시 중인 이미지 목록 반환"""
        if not hasattr(self.app_instance, 'all_tags'):
            return []
        # 카드(체크박스) 선택이 있으면 그 이미지들만 대상
        if hasattr(editor, 'selected_cards') and editor.selected_cards:
            return list(editor.selected_cards)
        # 선택 카드가 없으면,
        if not getattr(editor, 'selected_tags', None):
            # 선택 태그가 0개인 경우에도 현재 그리드 기준으로 대상 결정
            # 1) current_grid_images가 있으면 그 목록 사용
            if hasattr(self.app_instance, 'current_grid_images') and self.app_instance.current_grid_images:
                return list(self.app_instance.current_grid_images)
            # 2) fallback: 현재 이미지 파일 목록
            if hasattr(self.app_instance, 'image_files') and self.app_instance.image_files:
                return list(self.app_instance.image_files)
            return []
        
        # 이미지 그리드 필터링이 활성화된 경우 현재 이미지 그리드에 있는 이미지들만 대상으로 검색
        search_target_images = None
        if hasattr(editor, 'grid_filter_enabled') and editor.grid_filter_enabled and hasattr(self.app_instance, 'image_list') and self.app_instance.image_list:
            search_target_images = set(self.app_instance.image_list)
            print(f"리모트 모듈: 검색 결과 연동 활성화 - {len(search_target_images)} 개 이미지 대상으로 검색")
        else:
            print("리모트 모듈: 검색 결과 연동 비활성화 - 모든 이미지 대상으로 검색")
        
        tagged_images = set()
        for image_path, tags in self.app_instance.all_tags.items():
            # 그리드 필터링이 활성화된 경우 현재 그리드에 있는 이미지만 검색
            if search_target_images and image_path not in search_target_images:
                continue
                
            if editor.search_mode == "OR":
                # OR 조건: 선택된 태그 중 하나라도 있으면 포함
                if any(tag in tags for tag in editor.selected_tags):
                    tagged_images.add(image_path)
            else:  # AND 모드
                # AND 조건: 선택된 태그가 모두 있어야 포함
                if all(tag in tags for tag in editor.selected_tags):
                    tagged_images.add(image_path)
        
        return list(tagged_images)
    
    def apply_tag_replace(self, editor, target_images):
        """태그 교체 적용 (다중 태그 지원)"""
        old_tags_text = self.old_tag_input.text().strip()
        new_tag = self.new_tag_input.text().strip()
        
        if not old_tags_text or not new_tag:
            return
        
        # 쉼표로 구분된 태그들을 파싱
        old_tags = [tag.strip() for tag in old_tags_text.split(',') if tag.strip()]
        
        # 타임머신 로깅을 위한 변경 전 상태 저장
        from timemachine_log import TM
        before_all_tags = {k: v.copy() for k, v in self.app_instance.all_tags.items()}
        before_manual_tag_info = self.app_instance.manual_tag_info.copy() if hasattr(self.app_instance, 'manual_tag_info') else {}
        
        # 선택적 와일드카드 확장 (모듈이 있을 때만) - 대상 이미지의 태그만 기준으로 확장
        try:
            import wildcard_plugin as _wc
        except Exception:
            _wc = None
        if _wc and target_images:
            scoped_tags = []
            for image_path in target_images:
                key = str(image_path)
                if key in self.app_instance.all_tags:
                    scoped_tags.extend(self.app_instance.all_tags[key])
            all_known = sorted(set(scoped_tags))
            # 고급 확장: 따옴표/앵커 지원
            if hasattr(_wc, 'expand_tag_patterns_advanced'):
                old_tags = _wc.expand_tag_patterns_advanced(old_tags, all_known)
            else:
                old_tags = _wc.expand_tag_patterns(old_tags, all_known)
        
        print(f"다중 태그 교체: {old_tags} -> '{new_tag}'")
        
        # manual_tag_info 키 이관 (Trigger/Used 분류 유지)
        for old_tag in old_tags:
            if (hasattr(self.app_instance, 'manual_tag_info') and 
                old_tag in self.app_instance.manual_tag_info):
                # 기존 분류 정보를 새 태그로 이관
                is_trigger = self.app_instance.manual_tag_info[old_tag]
                self.app_instance.manual_tag_info[new_tag] = is_trigger
                if not any(old_tag in tags for tags in self.app_instance.all_tags.values()):

                    del self.app_instance.manual_tag_info[old_tag]
                print(f"  🔄 manual_tag_info 이관: '{old_tag}' -> '{new_tag}' ({'trigger' if is_trigger else 'used'})")
            else:
                # 기계로 태깅한 태그는 기본적으로 "used"로 분류
                if not hasattr(self.app_instance, 'manual_tag_info'):
                    self.app_instance.manual_tag_info = {}
                self.app_instance.manual_tag_info[new_tag] = False  # False = used
                print(f"  🤖 기계 태그 수정: '{old_tag}' -> '{new_tag}' (used로 분류)")
        
        modified_count = 0
        for image_path in target_images:
            key = str(image_path)
            if key in self.app_instance.all_tags:
                current_tags = self.app_instance.all_tags[key]
                new_tags = current_tags.copy()
                
                # 각 기존 태그를 새 태그로 교체
                for old_tag in old_tags:
                    if old_tag in new_tags:
                        # 모든 인스턴스를 새 태그로 교체
                        new_tags = [new_tag if tag == old_tag else tag for tag in new_tags]
                        print(f"  ✅ {image_path}: '{old_tag}' -> '{new_tag}'")
                
                # 중복 태그 제거 (새 태그가 여러 번 나타나는 경우)
                new_tags = self.remove_duplicate_tags(new_tags)
                
                # 변경사항이 있으면 저장 - all_tags 관리 플러그인 사용
                if new_tags != current_tags:
                    from all_tags_manager import set_tags_for_image
                    set_tags_for_image(self.app_instance, key, new_tags)
                    modified_count += 1
                    print(f"  📝 {image_path}: 중복 제거 후 {len(new_tags)}개 태그")
        
        print(f"다중 태그 교체 완료: {modified_count}개 이미지")
        
        # 타임머신에 태그 교체 기록
        try:
            print(f"[DEBUG] 타임머신 로그 기록 시도: tag_replace - {old_tags} -> {new_tag}")
            TM.log_change({
                "type": "tag_replace",
                "old_tags": old_tags,
                "new_tag": new_tag,
                "modified_count": modified_count,
                "target_images": target_images,  # 개별 이미지 정보 포함
                "image": getattr(self.app_instance, 'current_image', None),  # 현재 이미지 정보
                "before_all_tags": before_all_tags,
                "after_all_tags": {k: v.copy() for k, v in self.app_instance.all_tags.items()},
                "before_manual_tag_info": before_manual_tag_info,
                "after_manual_tag_info": self.app_instance.manual_tag_info.copy() if hasattr(self.app_instance, 'manual_tag_info') else {}
            })
            print(f"[DEBUG] 타임머신 로그 기록 완료")
        except Exception as e:
            print(f"[ERROR] 타임머신 로그 기록 실패: {e}")
            import traceback
            traceback.print_exc()

    def apply_tag_delete(self, editor, target_images):
        """태그 삭제 적용 (기존 태그만 필요)"""
        old_tag = self.old_tag_input.text().strip()
        if not old_tag:
            return
        before_all_tags = {k: v.copy() for k, v in self.app_instance.all_tags.items()} if hasattr(self.app_instance, 'all_tags') else {}
        modified_count = 0
        for image_path in target_images:
            key = str(image_path)
            current_tags = self.app_instance.all_tags.get(key, [])
            if old_tag in current_tags:
                new_tags = [t for t in current_tags if t != old_tag]
                if new_tags != current_tags:
                    from all_tags_manager import set_tags_for_image
                    set_tags_for_image(self.app_instance, key, new_tags)
                    modified_count += 1
        print(f"태그 삭제 완료: {modified_count}개 이미지")
        try:
            from timemachine_log import TM
            TM.log_change({
                "type": "tag_delete",
                "old_tag": old_tag,
                "modified_count": modified_count,
                "target_images": target_images,  # 개별 이미지 정보 포함
                "image": getattr(self.app_instance, 'current_image', None),  # 현재 이미지 정보
                "before_all_tags": before_all_tags,
                "after_all_tags": {k: v.copy() for k, v in self.app_instance.all_tags.items()}
            })
        except Exception:
            pass

    def apply_tag_insert_relative(self, editor, target_images, after=True):
        """기존 태그 기준 앞/뒤로 새 태그 추가 (이동칸수 재사용)"""
        old_tag = self.old_tag_input.text().strip()
        new_tag = self.new_tag_input.text().strip()
        if not old_tag or not new_tag:
            return
        step = self.add_step_input.value() if hasattr(self, 'add_step_input') else 1
        before_all_tags = {k: v.copy() for k, v in self.app_instance.all_tags.items()} if hasattr(self.app_instance, 'all_tags') else {}
        modified_count = 0
        # 새 태그를 기본 used(False)로 분류 (교체와 일관)
        try:
            if not hasattr(self.app_instance, 'manual_tag_info'):
                self.app_instance.manual_tag_info = {}
            if new_tag not in self.app_instance.manual_tag_info:
                self.app_instance.manual_tag_info[new_tag] = False
        except Exception:
            pass
        for image_path in target_images:
            key = str(image_path)
            current_tags = self.app_instance.all_tags.get(key, [])
            if old_tag in current_tags:
                base_index = current_tags.index(old_tag)
                insert_index = base_index + (1 + step if after else -step)
                insert_index = max(0, min(len(current_tags), insert_index))
                new_tags = current_tags.copy()
                # 중복 방지: 기존에 있으면 먼저 제거
                new_tags = [t for t in new_tags if t != new_tag]
                new_tags.insert(insert_index, new_tag)
                if new_tags != current_tags:
                    from all_tags_manager import set_tags_for_image
                    set_tags_for_image(self.app_instance, key, new_tags)
                    modified_count += 1
        print(f"태그 상대 추가 완료: {modified_count}개 이미지")
        try:
            from timemachine_log import TM
            TM.log_change({
                "type": "tag_insert_relative",
                "old_tag": old_tag,
                "new_tag": new_tag,
                "after": after,
                "step": step,
                "modified_count": modified_count,
                "target_images": target_images,  # 개별 이미지 정보 포함
                "image": getattr(self.app_instance, 'current_image', None),  # 현재 이미지 정보
                "before_all_tags": before_all_tags,
                "after_all_tags": {k: v.copy() for k, v in self.app_instance.all_tags.items()}
            })
        except Exception:
            pass

    def apply_tag_append_edge(self, editor, target_images, to_front=False):
        """새 태그를 맨앞/맨뒤로 추가"""
        new_tag = self.new_tag_input.text().strip()
        if not new_tag:
            return
        before_all_tags = {k: v.copy() for k, v in self.app_instance.all_tags.items()} if hasattr(self.app_instance, 'all_tags') else {}
        modified_count = 0
        # 새 태그를 기본 used(False)로 분류 (교체와 일관)
        try:
            if not hasattr(self.app_instance, 'manual_tag_info'):
                self.app_instance.manual_tag_info = {}
            if new_tag not in self.app_instance.manual_tag_info:
                self.app_instance.manual_tag_info[new_tag] = False
        except Exception:
            pass
        for image_path in target_images:
            key = str(image_path)
            current_tags = self.app_instance.all_tags.get(key, [])
            new_tags = [t for t in current_tags if t != new_tag]
            if to_front:
                new_tags = [new_tag] + new_tags
            else:
                new_tags = new_tags + [new_tag]
            if new_tags != current_tags:
                from all_tags_manager import set_tags_for_image
                set_tags_for_image(self.app_instance, key, new_tags)
                modified_count += 1
        print(f"새 태그 가장자리 추가 완료: {modified_count}개 이미지")
        try:
            from timemachine_log import TM
            TM.log_change({
                "type": "tag_append_edge",
                "new_tag": new_tag,
                "to_front": to_front,
                "modified_count": modified_count,
                "target_images": target_images,  # 개별 이미지 정보 포함
                "image": getattr(self.app_instance, 'current_image', None),  # 현재 이미지 정보
                "before_all_tags": before_all_tags,
                "after_all_tags": {k: v.copy() for k, v in self.app_instance.all_tags.items()}
            })
        except Exception:
            pass
    
    def apply_bulk_tag_replace(self, editor, target_images):
        """일괄 태그 교체 적용 (다중 태그 지원)"""
        old_tags_text = self.old_tag_input.text().strip()
        new_tag = self.new_tag_input.text().strip()
        
        if not old_tags_text or not new_tag:
            return
        
        # 쉼표로 구분된 태그들을 파싱
        old_tags = [tag.strip() for tag in old_tags_text.split(',') if tag.strip()]
        
        # 타임머신 로깅을 위한 변경 전 상태 저장
        from timemachine_log import TM
        before_all_tags = {k: v.copy() for k, v in self.app_instance.all_tags.items()}
        before_manual_tag_info = self.app_instance.manual_tag_info.copy() if hasattr(self.app_instance, 'manual_tag_info') else {}
        
        print(f"일괄 태그 교체: {old_tags} -> '{new_tag}' (에디터 태그들 순차 처리)")
        
        # manual_tag_info 키 이관 (Trigger/Used 분류 유지)
        for old_tag in old_tags:
            if (hasattr(self.app_instance, 'manual_tag_info') and 
                old_tag in self.app_instance.manual_tag_info):
                # 기존 분류 정보를 새 태그로 이관
                is_trigger = self.app_instance.manual_tag_info[old_tag]
                self.app_instance.manual_tag_info[new_tag] = is_trigger
                if not any(old_tag in tags for tags in self.app_instance.all_tags.values()):

                    del self.app_instance.manual_tag_info[old_tag]
                print(f"  🔄 manual_tag_info 이관: '{old_tag}' -> '{new_tag}' ({'trigger' if is_trigger else 'used'})")
            else:
                # 기계로 태깅한 태그는 기본적으로 "used"로 분류
                if not hasattr(self.app_instance, 'manual_tag_info'):
                    self.app_instance.manual_tag_info = {}
                self.app_instance.manual_tag_info[new_tag] = False  # False = used
                print(f"  🤖 기계 태그 수정: '{old_tag}' -> '{new_tag}' (used로 분류)")
        
        modified_count = 0
        for image_path in target_images:
            key = str(image_path)
            if key in self.app_instance.all_tags:
                current_tags = self.app_instance.all_tags[key]
                new_tags = current_tags.copy()
                
                # 각 기존 태그를 새 태그로 교체
                for old_tag in old_tags:
                    if old_tag in new_tags:
                        # 모든 인스턴스를 새 태그로 교체
                        new_tags = [new_tag if tag == old_tag else tag for tag in new_tags]
                        print(f"  ✅ {image_path}: '{old_tag}' -> '{new_tag}'")
                
                # 중복 태그 제거 (새 태그가 여러 번 나타나는 경우)
                new_tags = self.remove_duplicate_tags(new_tags)
                
                # 변경사항이 있으면 저장 - all_tags 관리 플러그인 사용
                if new_tags != current_tags:
                    from all_tags_manager import set_tags_for_image
                    set_tags_for_image(self.app_instance, key, new_tags)
                    modified_count += 1
                    print(f"  📝 {image_path}: 중복 제거 후 {len(new_tags)}개 태그")
        
        print(f"일괄 태그 교체 완료: {modified_count}개 이미지")
        
        # 타임머신에 일괄 태그 교체 기록
        try:
            print(f"[DEBUG] 타임머신 로그 기록 시도: bulk_tag_replace - {old_tags} -> {new_tag}")
            TM.log_change({
                "type": "bulk_tag_replace",
                "old_tags": old_tags,
                "new_tag": new_tag,
                "modified_count": modified_count,
                "target_images": target_images,  # 개별 이미지 정보 포함
                "image": getattr(self.app_instance, 'current_image', None),  # 현재 이미지 정보
                "before_all_tags": before_all_tags,
                "after_all_tags": {k: v.copy() for k, v in self.app_instance.all_tags.items()},
                "before_manual_tag_info": before_manual_tag_info,
                "after_manual_tag_info": self.app_instance.manual_tag_info.copy() if hasattr(self.app_instance, 'manual_tag_info') else {}
            })
            print(f"[DEBUG] 타임머신 로그 기록 완료")
        except Exception as e:
            print(f"[ERROR] 타임머신 로그 기록 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def apply_tag_position_change(self, editor, target_images):
        """태그 위치 변경 적용 (다중 태그 지원)"""
        move_tags_text = self.move_tag_input.text().strip()
        position_type = self.position_type_combo.currentText()
        
        if not move_tags_text:
            return
        
        # 쉼표로 구분된 태그들을 파싱
        move_tags = [tag.strip() for tag in move_tags_text.split(',') if tag.strip()]
        
        # 타임머신 로깅을 위한 변경 전 상태 저장
        from timemachine_log import TM
        before_all_tags = {k: v.copy() for k, v in self.app_instance.all_tags.items()}
        
        # 선택적 와일드카드 확장 (모듈이 있을 때만) - 대상 이미지의 태그만 기준으로 확장
        try:
            import wildcard_plugin as _wc
        except Exception:
            _wc = None
        if _wc and target_images:
            scoped_tags = []
            for image_path in target_images:
                key = str(image_path)
                if key in self.app_instance.all_tags:
                    scoped_tags.extend(self.app_instance.all_tags[key])
            all_known = sorted(set(scoped_tags))
            if hasattr(_wc, 'expand_tag_patterns_advanced'):
                move_tags = _wc.expand_tag_patterns_advanced(move_tags, all_known)
            else:
                move_tags = _wc.expand_tag_patterns(move_tags, all_known)
        
        print(f"다중 태그 위치 변경: {move_tags} -> '{position_type}'")
        
        modified_count = 0
        for image_path in target_images:
            key = str(image_path)
            if key in self.app_instance.all_tags:
                current_tags = self.app_instance.all_tags[key]
                new_tags = current_tags.copy()
                
                # 각 이동할 태그를 순차적으로 처리
                for move_tag in move_tags:
                    if move_tag in new_tags:
                        new_tags = self.reorder_tags(new_tags, move_tag, position_type)
                        print(f"  ✅ {image_path}: '{move_tag}' 위치 변경")
                
                # 변경사항이 있으면 저장 - all_tags 관리 플러그인 사용
                if new_tags != current_tags:
                    from all_tags_manager import set_tags_for_image
                    set_tags_for_image(self.app_instance, key, new_tags)
                    modified_count += 1
        
        print(f"다중 태그 위치 변경 완료: {modified_count}개 이미지")
        
        # 타임머신에 태그 위치 변경 기록
        try:
            print(f"[DEBUG] 타임머신 로그 기록 시도: tag_position_change - {move_tags} -> {position_type}")
            TM.log_change({
                "type": "tag_position_change",
                "move_tags": move_tags,
                "position_type": position_type,
                "modified_count": modified_count,
                "target_images": target_images,  # 개별 이미지 정보 포함
                "image": getattr(self.app_instance, 'current_image', None),  # 현재 이미지 정보
                "before_all_tags": before_all_tags,
                "after_all_tags": {k: v.copy() for k, v in self.app_instance.all_tags.items()}
            })
            print(f"[DEBUG] 타임머신 로그 기록 완료")
        except Exception as e:
            print(f"[ERROR] 타임머신 로그 기록 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def apply_bulk_tag_position_change(self, editor, target_images):
        """일괄 태그 위치 변경 적용 (다중 태그 지원)"""
        move_tags_text = self.move_tag_input.text().strip()
        position_type = self.position_type_combo.currentText()
        
        if not move_tags_text:
            return
        
        # 쉼표로 구분된 태그들을 파싱
        move_tags = [tag.strip() for tag in move_tags_text.split(',') if tag.strip()]
        
        # 타임머신 로깅을 위한 변경 전 상태 저장
        from timemachine_log import TM
        before_all_tags = {k: v.copy() for k, v in self.app_instance.all_tags.items()}
        
        # 선택적 와일드카드 확장 (모듈이 있을 때만) - 대상 이미지의 태그만 기준으로 확장
        try:
            import wildcard_plugin as _wc
        except Exception:
            _wc = None
        if _wc and target_images:
            scoped_tags = []
            for image_path in target_images:
                key = str(image_path)
                if key in self.app_instance.all_tags:
                    scoped_tags.extend(self.app_instance.all_tags[key])
            all_known = sorted(set(scoped_tags))
            if hasattr(_wc, 'expand_tag_patterns_advanced'):
                move_tags = _wc.expand_tag_patterns_advanced(move_tags, all_known)
            else:
                move_tags = _wc.expand_tag_patterns(move_tags, all_known)
        
        print(f"일괄 태그 위치 변경: {move_tags} -> '{position_type}' (에디터 태그들 순차 처리)")
        
        modified_count = 0
        for image_path in target_images:
            key = str(image_path)
            if key in self.app_instance.all_tags:
                current_tags = self.app_instance.all_tags[key]
                new_tags = current_tags.copy()
                
                # 각 이동할 태그를 순차적으로 처리
                for move_tag in move_tags:
                    if move_tag in new_tags:
                        new_tags = self.reorder_bulk_tags(new_tags, move_tag, position_type, editor.selected_tags)
                        print(f"  ✅ {image_path}: '{move_tag}' 위치 변경")
                
                # 변경사항이 있으면 저장 - all_tags 관리 플러그인 사용
                if new_tags != current_tags:
                    from all_tags_manager import set_tags_for_image
                    set_tags_for_image(self.app_instance, key, new_tags)
                    modified_count += 1
        
        print(f"일괄 태그 위치 변경 완료: {modified_count}개 이미지")
        
        # 타임머신에 일괄 태그 위치 변경 기록
        try:
            print(f"[DEBUG] 타임머신 로그 기록 시도: bulk_tag_position_change - {move_tags} -> {position_type}")
            TM.log_change({
                "type": "bulk_tag_position_change",
                "move_tags": move_tags,
                "position_type": position_type,
                "modified_count": modified_count,
                "target_images": target_images,  # 개별 이미지 정보 포함
                "image": getattr(self.app_instance, 'current_image', None),  # 현재 이미지 정보
                "before_all_tags": before_all_tags,
                "after_all_tags": {k: v.copy() for k, v in self.app_instance.all_tags.items()}
            })
            print(f"[DEBUG] 타임머신 로그 기록 완료")
        except Exception as e:
            print(f"[ERROR] 타임머신 로그 기록 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def reorder_tags(self, current_tags, move_tag, position_type):
        """태그 순서 재정렬"""
        # 이동할 태그들을 찾아서 제거
        tags_to_move = [tag for tag in current_tags if tag == move_tag]
        remaining_tags = [tag for tag in current_tags if tag != move_tag]
        
        if not tags_to_move:
            return current_tags
        
        # 위치에 따라 삽입
        if position_type == "맨 앞으로":
            new_tags = tags_to_move + remaining_tags
        elif position_type == "맨 뒤로":
            new_tags = remaining_tags + tags_to_move
        elif position_type in ["특정 태그 앞으로", "특정 태그 뒤로"]:
            reference_tag = self.reference_tag_input.text().strip()
            if not reference_tag or reference_tag not in remaining_tags:
                # 기준 태그가 없으면 맨 뒤로
                new_tags = remaining_tags + tags_to_move
            else:
                # 기준 태그 위치 찾기
                ref_index = remaining_tags.index(reference_tag)
                step = self.step_input.value()
                
                if position_type == "특정 태그 앞으로":
                    # 기준 태그 앞으로 step만큼 이동
                    insert_index = max(0, ref_index - step)
                else:  # 특정 태그 뒤로
                    # 기준 태그 뒤로 step만큼 이동
                    insert_index = min(len(remaining_tags), ref_index + step + 1)
                
                # 태그 삽입
                new_tags = remaining_tags[:insert_index] + tags_to_move + remaining_tags[insert_index:]
        else:
            new_tags = current_tags
        
        return new_tags
    
    def reorder_bulk_tags(self, current_tags, move_tag, position_type, editor_tags):
        """일괄 태그 순서 재정렬 (에디터 태그들만 처리)"""
        # 에디터에 있는 태그들 중에서 이동할 태그들을 찾아서 제거
        tags_to_move = [tag for tag in current_tags if tag == move_tag and tag in editor_tags]
        remaining_tags = [tag for tag in current_tags if not (tag == move_tag and tag in editor_tags)]
        
        if not tags_to_move:
            return current_tags
        
        # 위치에 따라 삽입
        if position_type == "맨 앞으로":
            new_tags = tags_to_move + remaining_tags
        elif position_type == "맨 뒤로":
            new_tags = remaining_tags + tags_to_move
        elif position_type in ["특정 태그 앞으로", "특정 태그 뒤로"]:
            reference_tag = self.reference_tag_input.text().strip()
            if not reference_tag or reference_tag not in remaining_tags:
                # 기준 태그가 없으면 맨 뒤로
                new_tags = remaining_tags + tags_to_move
            else:
                # 기준 태그 위치 찾기
                ref_index = remaining_tags.index(reference_tag)
                step = self.step_input.value()
                
                if position_type == "특정 태그 앞으로":
                    # 기준 태그 앞으로 step만큼 이동
                    insert_index = max(0, ref_index - step)
                else:  # 특정 태그 뒤로
                    # 기준 태그 뒤로 step만큼 이동
                    insert_index = min(len(remaining_tags), ref_index + step + 1)
                
                # 태그 삽입
                new_tags = remaining_tags[:insert_index] + tags_to_move + remaining_tags[insert_index:]
        else:
            new_tags = current_tags
        
        return new_tags
    
    def _normalize_image_path(self, image_path):
        if isinstance(image_path, Path):
            return str(image_path)
        if isinstance(image_path, str):
            return image_path
        try:
            return str(image_path)
        except Exception:
            return ""
    
    def _get_current_filtered_images(self, editor):
        """현재 UI 상태(선택된 태그, AND/OR, 검색 결과 연동)에 맞는 이미지 집합을 계산한다.
        선택된 태그가 없으면 빈 집합을 반환한다(기존 동작과 일관).
        """
        # 태그가 하나도 없으면 아무것도 표시하지 않는 기존 규칙 유지
        if not editor.selected_tags:
            return set()
        
        tagged_images = set()
        grid_images = None
        if hasattr(editor, 'grid_filter_enabled') and editor.grid_filter_enabled:
            if hasattr(self.app_instance, 'image_filtered_list') and self.app_instance.image_filtered_list:
                grid_images = {
                    self._normalize_image_path(p) for p in self.app_instance.image_filtered_list
                    if self._normalize_image_path(p)
                }
                print(f"검색 결과 연동(전체 목록) 적용: {len(grid_images)}개")
            elif hasattr(self.app_instance, 'image_list') and self.app_instance.image_list:
                grid_images = {
                    self._normalize_image_path(p) for p in self.app_instance.image_list
                    if self._normalize_image_path(p)
                }
                print(f"검색 결과 연동(현재 페이지) 적용: {len(grid_images)}개")
            else:
                grid_images = set()
                print("검색 결과 연동: 대상 이미지가 없음")
        
        if hasattr(self.app_instance, 'all_tags'):
            for image_path, tags in self.app_instance.all_tags.items():
                if not tags:  # 태그가 없는 이미지는 건너뛰기
                    continue
                
                normalized_path = self._normalize_image_path(image_path)
                if grid_images is not None and normalized_path not in grid_images:
                    continue
                
                # AND/OR 조건 확인
                if editor.search_mode == "AND":
                    # AND 모드: 선택된 모든 태그가 있어야 함
                    if all(tag in tags for tag in editor.selected_tags):
                        tagged_images.add(normalized_path)
                else:
                    # OR 모드: 선택된 태그 중 하나라도 있으면 됨
                    if any(tag in tags for tag in editor.selected_tags):
                        tagged_images.add(normalized_path)
        
        return tagged_images
    
    def update_ui_after_changes(self, editor):
        """변경사항 적용 후 UI 업데이트"""
        print("🔄 UI 업데이트 시작")
        
        # 태그 변경 후 selected_cards 필터링 (새로운 태그 기준으로 매칭되는 이미지만 유지)
        if hasattr(editor, 'selected_cards') and editor.selected_cards:
            print(f"태그 변경 전 selected_cards: {len(editor.selected_cards)}개")
            
            # 현재 선택된 태그들로 필터링된 이미지 집합 계산
            filtered_images = self._get_current_filtered_images(editor)
            
            # selected_cards에서 새로운 태그 기준으로 매칭되지 않는 이미지들 제거
            original_selected_count = len(editor.selected_cards)
            editor.selected_cards = editor.selected_cards.intersection(filtered_images)
            
            print(f"태그 변경 후 selected_cards: {original_selected_count}개 -> {len(editor.selected_cards)}개")
            
            # 매칭 결과가 0이면 selected_cards 완전 정리
            if not filtered_images:
                print("⚠️ 태그 변경 후 매칭 결과가 0개이므로 selected_cards 정리")
                editor.selected_cards.clear()
        
        # 에디터 이미지 그리드 업데이트 (요구사항 변경: 카드만 갱신)
        try:
            if hasattr(self.app_instance, 'tag_stylesheet_editor') and self.app_instance.tag_stylesheet_editor:
                # 카드 UI만 즉시 새로고침
                self.app_instance.tag_stylesheet_editor.refresh_editor_content()
        except Exception:
            pass
        
        # 카드 전용 갱신: 태그 텍스트만 업데이트
        try:
            if hasattr(self.app_instance, 'tag_stylesheet_editor') and self.app_instance.tag_stylesheet_editor:
                # target_images는 바로 위에서 get_target_images로 계산됨
                imgs = self.get_target_images(editor)
                self.app_instance.tag_stylesheet_editor.refresh_card_tags(image_paths=imgs)
        except Exception:
            pass
        
        # 에디터의 selected_tags는 태그 교체/이동 후에도 그대로 유지
        # (검색 조건을 유지하기 위해)
        print(f"에디터 selected_tags 유지: {editor.selected_tags}")
        
        # 현재 이미지의 태그 순서를 all_tags에서 가져와서 current_tags 업데이트
        if hasattr(self.app_instance, 'current_image') and self.app_instance.current_image:
            current_image_path = self.app_instance.current_image
            if current_image_path in self.app_instance.all_tags:
                # all_tags에서 변경된 순서를 current_tags에 반영
                updated_tags = self.app_instance.all_tags[current_image_path]
                self.app_instance.current_tags = updated_tags
                print(f"current_tags 업데이트: {updated_tags}")
                
                # removed_tags에서 현재 이미지에 존재하는 태그들 제거 (색상 업데이트를 위해)
                if hasattr(self.app_instance, 'removed_tags'):
                    original_removed_count = len(self.app_instance.removed_tags)
                    self.app_instance.removed_tags = [
                        tag for tag in self.app_instance.removed_tags 
                        if tag not in updated_tags
                    ]
                    if len(self.app_instance.removed_tags) != original_removed_count:
                        print(f"removed_tags 업데이트: {original_removed_count}개 -> {len(self.app_instance.removed_tags)}개")
                        print(f"현재 removed_tags: {self.app_instance.removed_tags}")
        
        # 1. 중앙 하단 태깅 패널 업데이트
        if hasattr(self.app_instance, 'current_image') and self.app_instance.current_image:
            from image_tagging_module import update_current_tags_display
            update_current_tags_display(self.app_instance)
            print("✅ 중앙 하단 태깅 패널 업데이트 완료")
        
        # 태그 통계 재계산은 tag_statistics_module.py에서 담당
        
        # 카테고리 캐시 무효화 (manual_tag_info 변경 반영을 위해)
        if hasattr(self.app_instance, 'tag_statistics_module') and self.app_instance.tag_statistics_module:
            if hasattr(self.app_instance.tag_statistics_module, '_cached_categories'):
                self.app_instance.tag_statistics_module._cached_categories.clear()
                print("✅ 카테고리 캐시 무효화 완료")
        
        # 메인 애플리케이션의 올바른 업데이트 메서드 호출
        if hasattr(self.app_instance, 'update_global_tag_stats'):
            self.app_instance.update_global_tag_stats()
            print("✅ 태그 통계 업데이트 완료")
        
        # 3. 태그 트리 강제 업데이트 (올바른 경로 사용)
        if hasattr(self.app_instance, 'update_tag_tree'):
            self.app_instance.update_tag_tree()
            print("✅ 태그 트리 업데이트 완료")
        
        # 4. 입력 필드 초기화 및 다시 로딩 (갱신 타이밍 문제 해결)
        self.clear_and_reload_input_fields(editor)
        
        print("🔄 UI 업데이트 완료")
    
    def clear_and_reload_input_fields(self, editor):
        """입력 필드 초기화 및 다시 로딩 (갱신 타이밍 문제 해결)"""
        print("🔄 입력 필드 초기화 및 다시 로딩")
        
        # 입력 필드들을 빈칸으로 초기화
        self.old_tag_input.clear()
        self.new_tag_input.clear()
        self.move_tag_input.clear()
        self.reference_tag_input.clear()
        
        # 일괄 모드가 활성화된 경우에만 에디터 태그들로 다시 채움
        if self.preview_checkbox.isChecked():
            # 약간의 지연 후 다시 로딩 (UI 업데이트 완료 대기)
            QTimer.singleShot(100, lambda: self.fill_fields_with_editor_tags())
            print("일괄 모드: 입력 필드 초기화 후 다시 로딩 예약")
        else:
            print("개별 모드: 입력 필드만 초기화")
    
    # 전역 태그 통계 재계산은 tag_statistics_module.py에서 담당
    
    def remove_duplicate_tags(self, tags_list):
        """태그 리스트에서 중복 제거 (순서 유지)"""
        seen = set()
        result = []
        
        for tag in tags_list:
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
        
        # 중복이 제거되었는지 확인
        if len(result) != len(tags_list):
            print(f"  🔄 중복 태그 제거: {len(tags_list)}개 -> {len(result)}개")
            print(f"  📋 제거 전: {tags_list}")
            print(f"  📋 제거 후: {result}")
        
        return result
    
    # 전역 태그 통계 재계산은 tag_statistics_module.py에서 담당
    
    def mousePressEvent(self, event):
        """드래그를 위한 마우스 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """드래그 이동"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def _update_preview_checkbox_lock_state_from_editor(self, selected_tags):
        """에디터 태그 변경 시 미리보기 체크박스 락 상태 갱신"""
        self._update_preview_checkbox_lock_state()

    def _update_preview_checkbox_lock_state(self):
        """현재 입력/에디터 상태를 보고 '현재 태그 일괄 사용' 체크박스를 해제 후 비활성화(lock) 또는 활성화"""
        try:
            editor = getattr(self.app_instance, 'tag_stylesheet_editor', None)
            has_selected_tags = bool(getattr(editor, 'selected_tags', []) or [])
        except Exception:
            editor = None
            has_selected_tags = False

        old_text = (self.old_tag_input.text().strip() if hasattr(self, 'old_tag_input') else '')
        move_text = (self.move_tag_input.text().strip() if hasattr(self, 'move_tag_input') else '')
        has_any_input = bool(old_text or move_text)

        # 요구사항: 무태그일 때만 비활성화. 태그칩이 있으면 기본 체크 + 활성화
        should_lock = (not has_selected_tags)

        if should_lock:
            try:
                # 체크 해제 후 클릭 비활성 + 시각적 비활성(locked)
                if self.preview_checkbox.isChecked():
                    self.preview_checkbox.setChecked(False)
                self.preview_checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self.preview_checkbox.setProperty("locked", True)
                self.preview_checkbox.style().unpolish(self.preview_checkbox)
                self.preview_checkbox.style().polish(self.preview_checkbox)
                self.preview_checkbox.update()
            except Exception:
                pass
        else:
            try:
                self.preview_checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
                self.preview_checkbox.setProperty("locked", False)
                self.preview_checkbox.style().unpolish(self.preview_checkbox)
                self.preview_checkbox.style().polish(self.preview_checkbox)
                self.preview_checkbox.update()
            except Exception:
                pass


def create_tag_stylesheet_editor_remote(app_instance):
    """태그 스타일시트 에디터 리모컨 생성"""
    remote = TagStyleSheetEditorRemote(app_instance)
    return remote


# 단독 실행을 위한 테스트 코드
if __name__ == "__main__":
    try:
        import sys
        from PySide6.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        
        # 앱 스타일 설정
        app.setStyle("Windows")
        
        remote = TagStyleSheetEditorRemote(None)  # 단독 실행시 app_instance는 None
        remote.show_remote()
        
        # 중앙에 위치
        screen_geometry = app.primaryScreen().geometry()
        x = (screen_geometry.width() - remote.width()) // 2
        y = (screen_geometry.height() - remote.height()) // 2
        remote.move(x, y)
        
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"PySide6가 설치되어 있지 않습니다: {e}")
        print("pip install PySide6 명령으로 설치해주세요.")
    except Exception as e:
        print(f"실행 오류: {e}")
        import traceback
        traceback.print_exc()