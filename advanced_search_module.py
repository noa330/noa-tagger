"""
고급 검색 모듈
검색창에 포커스가 있을 때 중앙 탭 위에 오버레이로 표시되는 고급 검색 기능
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QCheckBox, 
                               QScrollArea, QFrame, QSizePolicy, QSpacerItem, QApplication,
                               QGridLayout, QSpinBox, QDoubleSpinBox)

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
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont


class AdvancedSearchWidget(QWidget):
    """고급 검색 위젯"""
    
    def __init__(self, parent=None, app_instance=None):
        super().__init__(parent)
        self.app_instance = app_instance
        self.filter_groups = []
        self.setup_ui()
        
    def setup_ui(self):
        """UI 설정"""
        # 위젯 스타일
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #F0F2F5;
                font-size: 13px;
            }
            QComboBox, QLineEdit {
                background: rgba(17,17,27,1);
                border: 1px solid rgba(75,85,99,0.3);
                font-size: 13px;
                color: #F9FAFB;
            }
            QComboBox:hover, QLineEdit:hover {
                border-color: rgba(75,85,99,0.5);
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: rgba(75,85,99,0.7);
                outline: none;
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
                background: rgba(17,17,27,0.95);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 6px;
                color: #F9FAFB;
                selection-background-color: #3B82F6;
                selection-color: white;
            }
            QPushButton {
                background: rgba(17,17,27,1);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                color: #F0F2F5;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(17,17,27,1);
                border-color: rgba(75,85,99,0.5);
            }
            QPushButton#searchBtn {
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 500;
            }
            QPushButton#searchBtn:hover {
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
            }
            QPushButton#addGroupBtn {
                border: none;
                color: #F0F2F5;
                text-align: left;
                padding: 8px 0;
                font-weight: 500;
            }
            QPushButton#addGroupBtn:hover {
                color: #F0F2F5;
                background: transparent;
            }
            QPushButton#addFilterBtn, QPushButton#removeFilterBtn {
                width: 35px;
                height: 35px;
                padding: 0;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton#addFilterBtn {
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 6px;
            }
            QPushButton#addFilterBtn:hover {
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
            }
            QPushButton#removeFilterBtn {
                background: rgba(17,17,27,1);
                border: 1px solid rgba(75,85,99,0.3);
                color: #F0F2F5;
            }
            QPushButton#removeFilterBtn:hover {
                background: rgba(17,17,27,1);
                border-color: rgba(75,85,99,0.5);
            }
            QPushButton#deleteGroupBtn {
                width: 35px;
                height: 35px;
                background: #4A5568;
                color: #CBD5E0;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 0;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#deleteGroupBtn:hover {
                background: #718096;
                border-color: #718096;
                color: #CBD5E0;
            }
            QFrame#filterGroupFrame {
                background: rgba(17,17,27,1);
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
            }
        """)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        # 메인 컨텐츠 레이아웃
        main_content_layout = QVBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(16)
        
        # 상단 필터 섹션
        top_filters = QHBoxLayout()
        top_filters.setSpacing(16)
        
        # Query Type
        query_layout = QVBoxLayout()
        query_label = QLabel("Query Type")
        query_label.setStyleSheet("font-size: 12px; color: #9CA3AF; margin-bottom: 4px;")
        query_combo = CustomComboBox()
        query_combo.addItems(["All", "Specific", "Custom"])
        query_combo.setMinimumWidth(200)
        query_layout.addWidget(query_label)
        query_layout.addWidget(query_combo)
        top_filters.addLayout(query_layout)
        
        # Form Category
        category_layout = QVBoxLayout()
        category_label = QLabel("Form Category")
        category_label.setStyleSheet("font-size: 12px; color: #9CA3AF; margin-bottom: 4px;")
        category_combo = CustomComboBox()
        category_combo.addItems(["All", "Active", "Inactive", "Archived"])
        category_combo.setMinimumWidth(200)
        category_layout.addWidget(category_label)
        category_layout.addWidget(category_combo)
        top_filters.addLayout(category_layout)
        
        top_filters.addStretch()
        main_content_layout.addLayout(top_filters)
        
        # 필터 그룹들을 담을 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # 스크롤바를 호버할 때만 보이게 설정
        scroll_area.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                background: transparent;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background: rgba(156, 163, 175, 0.3);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(156, 163, 175, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        # scroll_area.setMaximumHeight(3000)  # 최대 높이 제한 제거
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(156,163,175,0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(156,163,175,0.5);
            }
        """)
        
        # 통합 필터 그룹 컨테이너
        self.filter_container = QFrame()
        self.filter_container.setObjectName("filterContainer")
        self.filter_container.setStyleSheet("""
            QFrame#filterContainer {
                background: transparent;
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 8px;
            }
        """)
        
        self.filter_container_layout = QVBoxLayout(self.filter_container)
        self.filter_container_layout.setContentsMargins(16, 16, 16, 16)
        self.filter_container_layout.setSpacing(16)
        
        # 초기에는 빈 상태로 시작 - 사용자가 필요에 따라 필터 그룹 추가
        
        # 스크롤 컨텐츠 위젯
        scroll_content = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        scroll_content_layout.setSpacing(16)
        scroll_content_layout.addWidget(self.filter_container)
        scroll_content_layout.addStretch()
        
        # 스크롤 영역에 컨텐츠 설정
        scroll_area.setWidget(scroll_content)
        main_content_layout.addWidget(scroll_area, 1)
        
        # Add Filter Group 버튼
        add_group_btn = QPushButton("+ Add Filter Group")
        add_group_btn.setObjectName("addGroupBtn")
        add_group_btn.setCursor(Qt.PointingHandCursor)
        add_group_btn.clicked.connect(self.add_filter_group)
        main_content_layout.addWidget(add_group_btn)
        
        main_layout.addLayout(main_content_layout, 1)
        
        # 하단 버튼들 (스크롤 영역 외부)
        bottom_buttons = QHBoxLayout()
        
        # 닫기 버튼 (맨 왼쪽) - 고급 검색에 어울리는 차분한 색상
        close_btn = QPushButton("Close Search")
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(17,17,27,1);
                border: 1px solid rgba(75,85,99,0.3);
                color: #F0F2F5;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(17,17,27,1);
                border-color: rgba(75,85,99,0.5);
                color: #F9FAFB;
            }
            QPushButton:pressed {
                background: rgba(17,17,27,1);
                border-color: rgba(75,85,99,0.7);
            }
        """)
        close_btn.setFixedHeight(36)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close_advanced_search)
        bottom_buttons.addWidget(close_btn)
        
        bottom_buttons.addStretch()
        
        reset_btn = QPushButton("Reset")
        reset_btn.setMinimumWidth(100)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self.reset_search)
        bottom_buttons.addWidget(reset_btn)
        
        search_btn = QPushButton("Search")
        search_btn.setObjectName("searchBtn")
        search_btn.setMinimumWidth(100)
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.clicked.connect(self.execute_search)
        bottom_buttons.addWidget(search_btn)
        
        main_layout.addLayout(bottom_buttons)
        
        # 기본 그룹 추가 (첫 번째 그룹)
        self.add_default_filter_group()
    
    def add_default_filter_group(self):
        """기본 필터 그룹 추가 (앱 시작 시 자동 생성)"""
        try:
            print("기본 필터 그룹 추가 중...")
            
            # 직접 참조로 필터 컨테이너 사용
            if hasattr(self, 'filter_container') and self.filter_container:
                # 현재 그룹 개수 계산
                group_count = self._count_existing_groups()
                group_count += 1  # 새 그룹 번호
                
                # 첫 번째 그룹이므로 Group Connector 비활성화
                show_and_or = False
                
                # 기본 그룹 추가 (첫 번째 그룹이므로 구분선 없음)
                self.create_filter_group(
                    self.filter_container_layout, 
                    f"Filter Group {group_count}", 
                    [{"field": "Tags", "operator": "=", "value": ""}],
                    show_and_or=show_and_or,
                    is_last_group=True  # 첫 번째 그룹이므로 마지막 그룹
                )
                print(f"기본 필터 그룹 추가 완료! (Group {group_count})")
            else:
                print("❌ filter_container 속성을 찾을 수 없습니다!")
                
        except Exception as e:
            print(f"❌ 기본 필터 그룹 추가 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def _count_existing_groups(self):
        """기존 그룹 개수 계산 (새로운 구조: QHBoxLayout 안의 QLabel 또는 직접 QLabel)"""
        try:
            if not hasattr(self, 'filter_container_layout'):
                return 0
                
            group_count = 0
            for i in range(self.filter_container_layout.count()):
                item = self.filter_container_layout.itemAt(i)
                if item and item.layout():  # QHBoxLayout인 경우
                    layout = item.layout()
                    for j in range(layout.count()):
                        layout_item = layout.itemAt(j)
                        if layout_item and layout_item.widget():
                            widget = layout_item.widget()
                            if isinstance(widget, QLabel):
                                group_count += 1
                                break
                elif item and item.widget():  # 직접 QLabel인 경우
                    widget = item.widget()
                    if isinstance(widget, QLabel):
                        group_count += 1
            
            print(f"기존 그룹 개수: {group_count}")
            return group_count
            
        except Exception as e:
            print(f"그룹 개수 계산 중 오류: {e}")
            return 0
    
    def _is_filter_row_layout(self, layout):
        """필터 행 레이아웃인지 확인"""
        try:
            if not layout:
                return False
            
            # 필터 행은 QComboBox나 QLineEdit이 있어야 함
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item:
                    if item.layout():
                        # 하위 레이아웃에서 위젯 찾기
                        sub_layout = item.layout()
                        for j in range(sub_layout.count()):
                            sub_item = sub_layout.itemAt(j)
                            if sub_item and sub_item.widget():
                                widget = sub_item.widget()
                                if isinstance(widget, (QComboBox, QLineEdit)):
                                    return True
                    elif item.widget():
                        widget = item.widget()
                        if isinstance(widget, (QComboBox, QLineEdit)):
                            return True
            
            return False
            
        except Exception as e:
            print(f"필터 행 레이아웃 확인 중 오류: {e}")
            return False
    
    def create_filter_group(self, parent_layout, group_name, filters, show_and_or=False, is_last_group=False):
        """필터 그룹 생성"""
        # 그룹 제목과 그룹 간 연결 방식 선택기
        group_header_layout = QHBoxLayout()
        
        # 그룹 제목
        group_title = QLabel(group_name)
        group_title.setStyleSheet("font-weight: 600; color: #F0F2F5; margin-bottom: 8px;")
        group_header_layout.addWidget(group_title)
        
        group_header_layout.addStretch()  # 오른쪽 정렬을 위한 스트레치
        parent_layout.addLayout(group_header_layout)
        
        # 필터 행들
        for i, filter_data in enumerate(filters):
            self.create_filter_row(parent_layout, group_name, filter_data, -1, i == 0 and show_and_or, i == 0)
        
        # 이전 그룹의 구분선 제거 (있다면)
        if parent_layout.count() > 0:
            last_item = parent_layout.itemAt(parent_layout.count() - 1)
            if last_item and last_item.widget() and isinstance(last_item.widget(), QFrame):
                # 마지막 아이템이 구분선이면 제거
                widget = last_item.widget()
                parent_layout.removeWidget(widget)
                widget.deleteLater()
        
        # 마지막 그룹이 아닌 경우에만 구분선 추가
        if not is_last_group:
            separator = QFrame()
            separator.setFixedHeight(1)
            separator.setStyleSheet("""
                QFrame {
                    background-color: rgba(75,85,99,0.3);
                    border: none;
                    margin: 10px 20px;
                }
            """)
            parent_layout.addWidget(separator)
    
    
    def create_filter_row(self, parent_layout, group_name, filter_data, insert_index=-1, show_and_or=False, is_first_row=False):
        """필터 행 생성"""
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        
        # AND/OR 연결자 (첫 번째 행이면 그룹 간 연결, 아니면 그룹 내 연결)
        andor_layout = QVBoxLayout()
        row_uid = str(id(filter_row))
        if is_first_row:
            # 첫 번째 행: 그룹 간 연결용
            andor_label = QLabel("Group Connector")
            andor_label.setStyleSheet("font-size: 11px; color: #9CA3AF; margin-bottom: 2px;")
            andor_combo = CustomComboBox()
            if show_and_or:  # 첫 번째 그룹이 아닌 경우에만 활성화
                andor_combo.addItems(["And", "Or", "Not And", "Not Or"])
                andor_combo.setCurrentText("Or")  # 기본값: OR
                andor_combo.setObjectName(f"andor_combo_{row_uid}")
            else:  # 첫 번째 그룹인 경우 비활성화
                andor_combo.addItems(["-"])
                andor_combo.setCurrentText("-")
                andor_combo.setEnabled(False)  # 드롭다운 비활성화
                andor_combo.setObjectName(f"andor_disabled_{row_uid}")
        else:
            # 나머지 행: 그룹 내 연결용
            andor_label = QLabel("And / Or")
            andor_label.setStyleSheet("font-size: 11px; color: #9CA3AF; margin-bottom: 2px;")
            andor_combo = CustomComboBox()
            andor_combo.addItems(["And", "Or", "Not And", "Not Or"])
            andor_combo.setObjectName(f"andor_combo_{row_uid}")
        
        andor_combo.setMinimumWidth(100)
        andor_layout.addWidget(andor_label)
        andor_layout.addWidget(andor_combo)
        filter_row.addLayout(andor_layout)
        
        # Field
        field_layout = QVBoxLayout()
        field_label = QLabel("Field")
        field_label.setStyleSheet("font-size: 11px; color: #9CA3AF; margin-bottom: 2px;")
        field_combo = CustomComboBox()
        field_combo.setObjectName(f"field_combo_{row_uid}")
        field_combo.addItems(["Tags", "File Name", "Date Created", "File Size"])
        if "field" in filter_data:
            field_combo.setCurrentText(filter_data["field"])
        else:
            field_combo.setCurrentText("Tags")
        field_combo.setMinimumWidth(100)
        field_layout.addWidget(field_label)
        field_layout.addWidget(field_combo)
        filter_row.addLayout(field_layout)
        
        # Operator
        op_layout = QVBoxLayout()
        op_label = QLabel("Operator")
        op_label.setStyleSheet("font-size: 11px; color: #9CA3AF; margin-bottom: 2px;")
        op_combo = CustomComboBox()
        op_combo.setObjectName(f"op_combo_{row_uid}")
        
        # 필드별 연산자 목록 정의
        self._update_operator_list(op_combo, field_combo.currentText())
        
        if "operator" in filter_data:
            op_combo.setCurrentText(filter_data["operator"])
        else:
            op_combo.setCurrentText("=")
        op_combo.setMinimumWidth(100)
        op_layout.addWidget(op_label)
        op_layout.addWidget(op_combo)
        filter_row.addLayout(op_layout)
        
        # 필드 변경 시 연산자 목록 업데이트
        field_combo.currentTextChanged.connect(lambda text: self._update_operator_list(op_combo, text))
        
        # Value
        value_layout = QVBoxLayout()
        value_label = QLabel("Value")
        value_label.setStyleSheet("font-size: 11px; color: #9CA3AF; margin-bottom: 2px;")
        value_input = QLineEdit()
        value_input.setObjectName(f"value_input_{row_uid}")
        value_input.setPlaceholderText("Enter value")
        if "value" in filter_data:
            value_input.setText(filter_data["value"])
        else:
            value_input.setText("")
        value_input.setFixedWidth(130)    # 최소 길이 감소 (130px)
        value_input.setMaxLength(2000)    # 최대 길이 유지 (2000자)
        value_layout.addWidget(value_label)
        value_layout.addWidget(value_input)
        filter_row.addLayout(value_layout)
        
        # 버튼들 (다른 칼럼과 높이 맞추기 위해 더미 라벨 추가)
        btn_layout = QVBoxLayout()
        btn_layout.setAlignment(Qt.AlignVCenter)  # 세로 가운데 정렬
        btn_layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        
        # 더미 라벨 (다른 칼럼의 라벨 높이와 맞추기 위해)
        dummy_label = QLabel("")
        dummy_label.setStyleSheet("font-size: 11px; color: transparent; margin-bottom: 2px;")
        dummy_label.setFixedHeight(20)  # 다른 라벨과 동일한 높이
        btn_layout.addWidget(dummy_label)
        
        btn_container = QHBoxLayout()
        
        add_btn = QPushButton("+")
        add_btn.setObjectName("addFilterBtn")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(lambda: self.add_filter_row(parent_layout, group_name))
        btn_container.addWidget(add_btn)
        
        remove_btn = QPushButton("-")
        remove_btn.setObjectName("removeFilterBtn")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.remove_filter_row(parent_layout, filter_row, group_name))
        btn_container.addWidget(remove_btn)
        
        # 첫 번째 행에만 X 버튼 (그룹 삭제)
        if is_first_row:
            delete_btn = QPushButton("×")
            delete_btn.setObjectName("deleteGroupBtn")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda: self.remove_filter_group(parent_layout, group_name))
            btn_container.addWidget(delete_btn)
        
        btn_layout.addLayout(btn_container)
        filter_row.addLayout(btn_layout)
        
        filter_row.addStretch()
        
        # 조건 해석을 위한 별도 행 추가 (필터 행 바로 밑에)
        interpretation_row = QHBoxLayout()
        interpretation_row.setSpacing(0)
        interpretation_row.setContentsMargins(0, 0, 0, 0)
        
        # 조건 해석 라벨 (왼쪽에 딱 붙여서)
        interpretation_label = QLabel()
        interpretation_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 12px;
                margin-top: 8px;
                margin-bottom: 2px;
                padding: 4px 0px;
            }
        """)
        interpretation_label.setWordWrap(False)
        interpretation_label.setObjectName(f"interpretation_label_{id(filter_row)}")
        interpretation_row.addWidget(interpretation_label)
        
        # 나머지 공간 채우기
        interpretation_row.addStretch()
        
        # 필터 행과 해석 행을 하나의 컨테이너로 묶기
        filter_container = QVBoxLayout()
        filter_container.setSpacing(0)
        filter_container.setContentsMargins(0, 0, 0, 0)
        filter_container.addLayout(filter_row)
        filter_container.addLayout(interpretation_row)
        
        # 특정 인덱스에 삽입하거나 마지막에 추가
        if insert_index >= 0:
            parent_layout.insertLayout(insert_index, filter_container)
        else:
            parent_layout.addLayout(filter_container)
        
        # 초기 조건 해석 설정
        self._update_condition_interpretation(interpretation_label, field_combo.currentText(), op_combo.currentText(), value_input.text(), andor_combo.currentText(), is_first_row)
        
        # 필드, 연산자, 값, AND/OR 연결자 변경 시 조건 해석 업데이트
        field_combo.currentTextChanged.connect(lambda text: self._update_condition_interpretation(interpretation_label, text, op_combo.currentText(), value_input.text(), andor_combo.currentText(), is_first_row))
        op_combo.currentTextChanged.connect(lambda text: self._update_condition_interpretation(interpretation_label, field_combo.currentText(), text, value_input.text(), andor_combo.currentText(), is_first_row))
        value_input.textChanged.connect(lambda text: self._update_condition_interpretation(interpretation_label, field_combo.currentText(), op_combo.currentText(), text, andor_combo.currentText(), is_first_row))
        andor_combo.currentTextChanged.connect(lambda text: self._update_condition_interpretation(interpretation_label, field_combo.currentText(), op_combo.currentText(), value_input.text(), text, is_first_row))
    
    def add_filter_group(self):
        """새 필터 그룹 추가"""
        try:
            print("🔧 Add Filter Group 버튼 클릭됨")
            
            # 직접 참조로 필터 컨테이너 사용
            if hasattr(self, 'filter_container') and self.filter_container:
                # 현재 그룹 개수 계산
                group_count = self._count_existing_groups()
                group_count += 1  # 새 그룹 번호
                print(f"새 그룹 번호: {group_count}")
                
                # 기존 마지막 그룹에 구분선 추가 (기본 그룹이 이미 있으므로 항상 추가)
                print(f"그룹 {group_count}개 - 이전 마지막 그룹에 구분선 추가 시도")
                self._add_separator_to_previous_last_group()
                
                # 새로 추가되는 그룹은 항상 마지막 그룹
                is_last_group = True
                
                # 첫 번째 그룹이 아닌 경우에만 Group Connector 활성화
                show_and_or = group_count > 1
                
                # 새 필터 그룹 추가
                print("필터 그룹 생성 시작...")
                self.create_filter_group(
                    self.filter_container_layout, 
                    f"Filter Group {group_count}", 
                    [{"field": "Tags", "operator": "=", "value": ""}],
                    show_and_or=show_and_or,
                    is_last_group=is_last_group
                )
                print("필터 그룹 생성 완료!")
            else:
                print("❌ filter_container 속성을 찾을 수 없습니다!")
                
        except Exception as e:
            print(f"❌ 필터 그룹 추가 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def remove_filter_row(self, parent_layout, filter_row, group_name):
        """개별 필터 행 삭제 - 안전한 지연 삭제"""
        try:
            print(f"필터 행 삭제 시작: {filter_row}")
            
            # 이미 삭제 중이면 무시
            if hasattr(self, '_deleting_row') and self._deleting_row:
                print("이미 삭제 중입니다. 무시합니다.")
                return
            
            self._deleting_row = True
            
            if not parent_layout:
                print("❌ parent_layout이 None입니다!")
                self._deleting_row = False
                return
            
            # 레이아웃에서 해당 행의 인덱스 찾기
            row_index = -1
            
            for i in range(parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item and item.layout():
                    container_layout = item.layout()
                    if container_layout.count() > 0:
                        first_item = container_layout.itemAt(0)
                        if first_item and first_item.layout() == filter_row:
                            row_index = i
                            break
            
            if row_index == -1:
                print("해당 필터 행을 찾을 수 없습니다.")
                self._deleting_row = False
                return
            
            # 전체 그룹 수 확인
            total_groups = self._count_filter_groups(parent_layout)
            
            # 해당 그룹의 행 개수 확인
            group_row_count = 0
            group_start_index = -1
            
            for i in range(row_index-1, -1, -1):
                item = parent_layout.itemAt(i)
                if item:
                    if item.widget() and isinstance(item.widget(), QLabel):
                        label = item.widget()
                        if not label.objectName().startswith("interpretation_label_"):
                            group_start_index = i
                            break
                    elif item.layout():
                        layout = item.layout()
                        for j in range(layout.count()):
                            layout_item = layout.itemAt(j)
                            if layout_item and layout_item.widget() and isinstance(layout_item.widget(), QLabel):
                                group_start_index = i
                                break
                        if group_start_index != -1:
                            break
            
            if group_start_index != -1:
                for i in range(group_start_index + 1, parent_layout.count()):
                    item = parent_layout.itemAt(i)
                    if item:
                        if item.widget() and isinstance(item.widget(), QLabel):
                            label = item.widget()
                            if not label.objectName().startswith("interpretation_label_"):
                                break
                        elif item.layout():
                            layout = item.layout()
                            is_next_group = False
                            for j in range(layout.count()):
                                layout_item = layout.itemAt(j)
                                if layout_item and layout_item.widget():
                                    widget = layout_item.widget()
                                    if isinstance(widget, QLabel):
                                        if not widget.objectName().startswith("interpretation_label_"):
                                            is_next_group = True
                                            break
                            if is_next_group:
                                break
                            else:
                                group_row_count += 1
            
            print(f"그룹 '{group_name}'의 행 개수: {group_row_count}")
            
            # 현재 행이 그룹의 첫 번째 행인지 확인
            is_first_row_in_group = (row_index == group_start_index + 1)
            
            # 그룹이 1개이고 행도 1개일 때만 삭제 방지
            if total_groups <= 1 and group_row_count <= 1:
                print("⚠️ 그룹이 1개만 남았고, 행도 1개입니다. 삭제할 수 없습니다.")
                self._deleting_row = False
                return
            
            # 행이 하나만 있으면 그룹 전체 삭제 (단, 그룹이 2개 이상일 때만)
            if group_row_count <= 1 and total_groups > 1:
                print(f"그룹에 행이 하나만 있으므로 그룹 전체 삭제")
                self._deleting_row = False
                self.remove_filter_group(parent_layout, group_name)
                return
            
            # 위젯 수집
            item = parent_layout.itemAt(row_index)
            if not item or not item.layout():
                self._deleting_row = False
                return
            
            widgets_to_delete = []
            self._collect_widgets_from_layout(item.layout(), widgets_to_delete)
            layout_to_delete = item.layout()
            
            # 지연 삭제
            def do_delete():
                try:
                    parent_layout.removeItem(item)
                    for widget in widgets_to_delete:
                        widget.setParent(None)
                        widget.deleteLater()
                    layout_to_delete.deleteLater()
                    print("필터 행 삭제 완료")
                    
                    # 첫 번째 행을 삭제했다면, 새로운 첫 번째 행을 업데이트
                    if is_first_row_in_group and group_row_count > 1:
                        print("첫 번째 행 삭제 - 두 번째 행을 새로운 첫 번째 행으로 전환")
                        QTimer.singleShot(10, lambda: self._promote_second_row_to_first(parent_layout, group_start_index, group_name, total_groups))
                        
                finally:
                    self._deleting_row = False
            
            QTimer.singleShot(0, do_delete)
            
        except Exception as e:
            print(f"필터 행 삭제 중 오류: {e}")
            import traceback
            traceback.print_exc()
            self._deleting_row = False
    
    def _promote_second_row_to_first(self, parent_layout, group_start_index, group_name, total_groups):
        """두 번째 행을 첫 번째 행으로 승격 (And/Or를 그룹간 연결로 변경, X 버튼 추가)"""
        try:
            from PySide6.QtWidgets import QPushButton
            from PySide6.QtCore import Qt
            
            print(f"두 번째 행을 첫 번째 행으로 승격 시작 (그룹: {group_name})")
            
            # 그룹 제목 다음의 첫 번째 필터 행 찾기
            new_first_row_index = -1
            for i in range(group_start_index + 1, parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item and item.layout():
                    # 필터 행인지 확인 (interpretation 라벨이 아닌 경우)
                    container_layout = item.layout()
                    if container_layout.count() > 0:
                        first_item = container_layout.itemAt(0)
                        if first_item and first_item.layout():
                            new_first_row_index = i
                            filter_row = first_item.layout()
                            break
            
            if new_first_row_index == -1:
                print("새로운 첫 번째 행을 찾을 수 없습니다.")
                return
            
            print(f"새로운 첫 번째 행 인덱스: {new_first_row_index}")
            
            # 필터 행의 위젯들을 찾아서 수정
            # 0: And/Or 영역, 1: 필터 필드들, 2: 버튼 영역
            if filter_row.count() >= 3:
                # And/Or 영역 수정
                andor_area_item = filter_row.itemAt(0)
                if andor_area_item and andor_area_item.layout():
                    andor_layout = andor_area_item.layout()
                    # 첫 번째는 라벨, 두 번째는 콤보박스
                    if andor_layout.count() >= 2:
                        label_item = andor_layout.itemAt(0)
                        combo_item = andor_layout.itemAt(1)
                        
                        if label_item and label_item.widget():
                            label = label_item.widget()
                            label.setText("Group Connector")
                            print("And/Or 라벨을 'Group Connector'로 변경")
                        
                        if combo_item and combo_item.widget():
                            combo = combo_item.widget()
                            # 그룹이 1개면 비활성화, 2개 이상이면 활성화
                            combo.clear()
                            if total_groups > 1:
                                combo.addItems(["And", "Or", "Not And", "Not Or"])
                                combo.setCurrentText("Or")
                                combo.setEnabled(True)
                                print("And/Or 콤보박스를 그룹간 연결용으로 변경 (활성화)")
                            else:
                                combo.addItems(["-"])
                                combo.setEnabled(False)
                                print("And/Or 콤보박스를 비활성화 (첫 번째 그룹)")
                
                # 버튼 영역에 X 버튼 추가
                print(f"필터 행 아이템 개수: {filter_row.count()}")
                
                # 필터 행의 마지막에서 두 번째 영역이 버튼 영역 (마지막은 stretch)
                btn_area_index = -1
                for i in range(filter_row.count()):
                    item = filter_row.itemAt(i)
                    if item and item.layout():
                        # QVBoxLayout이고 버튼들을 포함하는 영역 찾기
                        layout = item.layout()
                        # 더미 라벨과 버튼 컨테이너가 있는지 확인
                        for j in range(layout.count()):
                            sub_item = layout.itemAt(j)
                            if sub_item and sub_item.layout():
                                # HBoxLayout인지 확인 (btn_container)
                                sub_layout = sub_item.layout()
                                for k in range(sub_layout.count()):
                                    widget_item = sub_layout.itemAt(k)
                                    if widget_item and widget_item.widget():
                                        widget = widget_item.widget()
                                        if isinstance(widget, QPushButton) and widget.text() in ["+", "−"]:
                                            btn_area_index = i
                                            print(f"버튼 영역 찾음: 인덱스 {i}")
                                            break
                                if btn_area_index != -1:
                                    break
                        if btn_area_index != -1:
                            break
                
                if btn_area_index != -1:
                    btn_layout = filter_row.itemAt(btn_area_index).layout()
                    # btn_container 찾기 (HBoxLayout)
                    btn_container = None
                    for i in range(btn_layout.count()):
                        item = btn_layout.itemAt(i)
                        if item and item.layout():
                            btn_container = item.layout()
                            break
                    
                    if btn_container:
                        # X 버튼이 이미 있는지 확인
                        has_delete_btn = False
                        for i in range(btn_container.count()):
                            widget_item = btn_container.itemAt(i)
                            if widget_item and widget_item.widget():
                                widget = widget_item.widget()
                                if isinstance(widget, QPushButton) and widget.objectName() == "deleteGroupBtn":
                                    has_delete_btn = True
                                    print("X 버튼이 이미 존재합니다.")
                                    break
                        
                        if not has_delete_btn:
                            # X 버튼 추가
                            delete_btn = QPushButton("×")
                            delete_btn.setObjectName("deleteGroupBtn")
                            delete_btn.setCursor(Qt.PointingHandCursor)
                            delete_btn.clicked.connect(lambda checked=False, pl=parent_layout, gn=group_name: self.remove_filter_group(pl, gn))
                            btn_container.addWidget(delete_btn)
                            print("✅ X 버튼(그룹 삭제) 추가 완료")
                        else:
                            print("X 버튼이 이미 있으므로 추가하지 않습니다.")
                    else:
                        print("⚠️ btn_container를 찾을 수 없습니다.")
                else:
                    print("⚠️ 버튼 영역을 찾을 수 없습니다.")
            
            print("두 번째 행을 첫 번째 행으로 승격 완료")
            
        except Exception as e:
            print(f"두 번째 행 승격 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def _cleanup_layout_recursively(self, layout):
        """레이아웃을 재귀적으로 정리"""
        try:
            # 모든 아이템을 역순으로 처리
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item:
                    if item.widget():
                        # 위젯인 경우
                        widget = item.widget()
                        widget.setParent(None)
                        widget.deleteLater()
                    elif item.layout():
                        # 레이아웃인 경우 재귀적으로 정리
                        self._cleanup_layout_recursively(item.layout())
                        item.layout().deleteLater()
                    
                    # 아이템 제거
                    layout.removeItem(item)
        except Exception as e:
            print(f"레이아웃 정리 중 오류: {e}")
    
    def add_filter_row(self, parent_layout, group_name):
        """특정 필터 그룹에 새로운 행 추가"""
        try:
            print(f"필터 그룹 '{group_name}'에 새 행 추가")
            
            # 그룹 제목의 인덱스 찾기 (새로운 구조: QHBoxLayout 안의 QLabel)
            group_title_index = -1
            for i in range(parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item and item.layout():  # QHBoxLayout인 경우
                    layout = item.layout()
                    for j in range(layout.count()):
                        layout_item = layout.itemAt(j)
                        if layout_item and layout_item.widget():
                            widget = layout_item.widget()
                            if isinstance(widget, QLabel) and widget.text() == group_name:
                                group_title_index = i
                                break
                    if group_title_index != -1:
                        break
                elif item and item.widget():  # 기존 구조: 직접 QLabel인 경우
                    widget = item.widget()
                    if isinstance(widget, QLabel) and widget.text() == group_name:
                        group_title_index = i
                        break
            
            if group_title_index == -1:
                print(f"그룹 '{group_name}'을 찾을 수 없습니다.")
                return
            
            # 그룹의 마지막 필터 행 찾기
            last_row_index = group_title_index
            insert_index = group_title_index + 1  # 기본값 설정
            
            for i in range(group_title_index + 1, parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item:
                    # QHBoxLayout이면 다음 그룹의 시작인지 확인
                    if item.layout():
                        # 다음 그룹의 헤더인지 확인 (QLabel이 있는지)
                        layout = item.layout()
                        is_next_group = False
                        
                        for j in range(layout.count()):
                            layout_item = layout.itemAt(j)
                            if layout_item and layout_item.widget():
                                widget = layout_item.widget()
                                if isinstance(widget, QLabel):
                                    # 그룹 제목인지 확인 (해석 라벨이 아닌 경우)
                                    if not widget.objectName().startswith("interpretation_label_"):
                                        is_next_group = True
                                        break
                        
                        if is_next_group:
                            break
                        else:
                            # 필터 컨테이너인 경우 (필터 행 + 해석 행)
                            last_row_index = i
                            insert_index = i + 1  # 마지막 컨테이너 다음에 추가
                    # QLabel이면 다음 그룹의 시작이므로 중단
                    elif item.widget() and isinstance(item.widget(), QLabel):
                        break
                    # QFrame(구분선)이면 그 앞에 추가
                    elif item.widget() and isinstance(item.widget(), QFrame):
                        insert_index = i
                        break
            
            # 새 필터 행 생성
            new_filter_data = {"field": "Tags", "operator": "=", "value": ""}
            self.create_filter_row(parent_layout, group_name, new_filter_data, insert_index)
            
            print(f"필터 그룹 '{group_name}'에 새 행 추가 완료")
            
        except Exception as e:
            print(f"필터 행 추가 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def _count_filter_groups(self, parent_layout):
        """전체 필터 그룹 개수 세기"""
        group_count = 0
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            if item and item.layout():
                layout = item.layout()
                for j in range(layout.count()):
                    layout_item = layout.itemAt(j)
                    if layout_item and layout_item.widget():
                        widget = layout_item.widget()
                        if isinstance(widget, QLabel) and widget.text().startswith("Filter Group"):
                            group_count += 1
                            break
        print(f"전체 그룹 개수: {group_count}")
        return group_count
    
    def remove_filter_group(self, parent_layout, group_name):
        """필터 그룹 전체 삭제 - 안전한 지연 삭제"""
        try:
            print(f"필터 그룹 삭제 시작: {group_name}")
            
            # 전체 그룹 수 확인 - 그룹이 1개만 남았으면 삭제 불가
            total_groups = self._count_filter_groups(parent_layout)
            if total_groups <= 1:
                print("⚠️ 그룹이 1개만 남았습니다. 삭제할 수 없습니다.")
                return
            
            # 이미 삭제 중이면 무시
            if hasattr(self, '_deleting_group') and self._deleting_group:
                print("이미 삭제 중입니다. 무시합니다.")
                return
            
            self._deleting_group = True
            
            # 삭제할 위젯들을 먼저 수집
            widgets_to_delete = []
            layouts_to_delete = []
            items_to_remove = []
            group_title_index = -1
            
            # 1단계: 그룹 제목 찾기
            for i in range(parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    for j in range(layout.count()):
                        layout_item = layout.itemAt(j)
                        if layout_item and layout_item.widget():
                            widget = layout_item.widget()
                            if isinstance(widget, QLabel) and widget.text() == group_name:
                                group_title_index = i
                                items_to_remove.append((i, item))
                                break
                    if group_title_index != -1:
                        break
                elif item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, QLabel) and widget.text() == group_name:
                        group_title_index = i
                        items_to_remove.append((i, item))
                        break
            
            if group_title_index == -1:
                print(f"그룹 '{group_name}'을 찾을 수 없습니다.")
                self._deleting_group = False
                return
            
            # 2단계: 그룹에 속한 모든 항목 수집
            for i in range(group_title_index + 1, parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item:
                    if item.layout():
                        layout = item.layout()
                        is_next_group = False
                        
                        for j in range(layout.count()):
                            layout_item = layout.itemAt(j)
                            if layout_item and layout_item.widget():
                                widget = layout_item.widget()
                                if isinstance(widget, QLabel):
                                    if not widget.objectName().startswith("interpretation_label_"):
                                        is_next_group = True
                                        break
                        
                        if is_next_group:
                            break
                        else:
                            items_to_remove.append((i, item))
                    elif item.widget() and isinstance(item.widget(), QLabel):
                        break
                    elif item.widget() and isinstance(item.widget(), QFrame):
                        items_to_remove.append((i, item))
                        break
            
            # 3단계: 모든 위젯 수집 및 시그널 차단
            for idx, item in items_to_remove:
                if item.widget():
                    widget = item.widget()
                    widget.blockSignals(True)
                    widgets_to_delete.append(widget)
                elif item.layout():
                    self._collect_widgets_from_layout(item.layout(), widgets_to_delete)
                    layouts_to_delete.append(item.layout())
            
            # 4단계: 지연 삭제 (이벤트 루프가 끝난 후 실행)
            def do_delete():
                try:
                    # 레이아웃에서 제거
                    for idx, item in reversed(items_to_remove):
                        parent_layout.removeItem(item)
                    
                    # 위젯 삭제
                    for widget in widgets_to_delete:
                        widget.setParent(None)
                        widget.deleteLater()
                    
                    # 레이아웃 삭제
                    for layout in layouts_to_delete:
                        layout.deleteLater()
                    
                    print(f"필터 그룹 '{group_name}' 삭제 완료")
                    
                    # 마지막 그룹 구분선 제거
                    QTimer.singleShot(10, lambda: self._remove_last_group_separator(parent_layout))
                    
                    # 그룹 번호 재정렬
                    QTimer.singleShot(20, lambda: self._renumber_filter_groups(parent_layout))
                    
                finally:
                    self._deleting_group = False
            
            QTimer.singleShot(0, do_delete)
            
        except Exception as e:
            print(f"필터 그룹 삭제 중 오류: {e}")
            import traceback
            traceback.print_exc()
            self._deleting_group = False
    
    def _collect_widgets_from_layout(self, layout, widget_list):
        """레이아웃에서 모든 위젯 수집 및 시그널 차단"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item:
                if item.widget():
                    widget = item.widget()
                    widget.blockSignals(True)
                    widget_list.append(widget)
                elif item.layout():
                    self._collect_widgets_from_layout(item.layout(), widget_list)
    
    def _add_separator_to_previous_last_group(self):
        """이전 마지막 그룹에 구분선 추가"""
        try:
            print("_add_separator_to_previous_last_group 함수 호출됨")
            
            if not hasattr(self, 'filter_container_layout'):
                print("filter_container_layout 속성이 없음")
                return
                
            print(f"현재 레이아웃 아이템 개수: {self.filter_container_layout.count()}")
            
            # 마지막 그룹의 마지막 필터 행 뒤에 구분선 추가
            if self.filter_container_layout.count() > 0:
                # 마지막 아이템이 구분선이 아닌 경우에만 구분선 추가
                last_item = self.filter_container_layout.itemAt(self.filter_container_layout.count() - 1)
                # 마지막 아이템이 위젯인지 레이아웃인지 확인
                is_separator = False
                if last_item and last_item.widget():
                    is_separator = isinstance(last_item.widget(), QFrame)
                elif last_item and last_item.layout():
                    is_separator = False  # 레이아웃은 구분선이 아님
                
                if not is_separator:
                    # 구분선 추가
                    separator = QFrame()
                    separator.setFixedHeight(1)
                    separator.setStyleSheet("""
                        QFrame {
                            background-color: rgba(75,85,99,0.3);
                            border: none;
                            margin: 10px 20px;
                        }
                    """)
                    self.filter_container_layout.addWidget(separator)
        except Exception as e:
            print(f"이전 마지막 그룹 구분선 추가 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def _remove_last_group_separator(self, parent_layout):
        """마지막 그룹의 구분선 제거"""
        try:
            # 레이아웃의 마지막 아이템이 구분선인지 확인
            if parent_layout.count() > 0:
                last_item = parent_layout.itemAt(parent_layout.count() - 1)
                if last_item and last_item.widget() and isinstance(last_item.widget(), QFrame):
                    # 마지막 아이템이 구분선이면 제거
                    widget = last_item.widget()
                    parent_layout.removeWidget(widget)
                    widget.deleteLater()
        except Exception as e:
            print(f"마지막 그룹 구분선 제거 중 오류: {e}")
    
    def _renumber_filter_groups(self, parent_layout):
        """필터 그룹 번호 재정렬"""
        try:
            print("그룹 번호 재정렬 시작")
            group_number = 1
            
            for i in range(parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    for j in range(layout.count()):
                        layout_item = layout.itemAt(j)
                        if layout_item and layout_item.widget():
                            widget = layout_item.widget()
                            if isinstance(widget, QLabel) and widget.text().startswith("Filter Group"):
                                # 그룹 번호 업데이트
                                old_name = widget.text()
                                new_name = f"Filter Group {group_number}"
                                widget.setText(new_name)
                                print(f"그룹 이름 변경: {old_name} → {new_name}")
                                group_number += 1
                                break
            
            print(f"그룹 번호 재정렬 완료: 총 {group_number - 1}개 그룹")
        except Exception as e:
            print(f"그룹 번호 재정렬 중 오류: {e}")
            import traceback
            traceback.print_exc()

    def execute_search(self):
        """고급 검색 실행"""
        try:
            # print("🔍 고급 검색 시작...")
            
            # 비디오 프레임 자동 표시 방지 플래그 설정 (포커스 아웃 방지)
            self.app_instance._skip_video_frame_auto_show = True
            
            # 그룹별 검색 조건 수집
            filter_groups = self.collect_filter_groups()
            
            if not filter_groups:
                # print("검색 조건이 없습니다. 빈 결과를 반환합니다.")
                # 검색 조건이 없으면 빈 결과 반환
                results = []
            else:
                # 그룹별 검색 실행
                results = self.perform_grouped_search(filter_groups)
            
            # print(f"검색 결과: {len(results)}개 이미지")
            
            # 검색 결과를 app_instance에 저장 (search_module에서 처리)
            self.app_instance.advanced_search_results = results
            print(f"고급 검색 결과 저장: {len(results)}개")
            
            # 통합된 그리드 업데이트 함수 호출
            try:
                from search_module import update_image_grid_unified
                update_image_grid_unified(self.app_instance)
                print("이미지 그리드 업데이트 완료")
                
                # 추가 안전장치: 잠시 후 한 번 더 업데이트 (UI 반영 보장)
                from PySide6.QtCore import QTimer
                def delayed_update():
                    try:
                        update_image_grid_unified(self.app_instance)
                        print("지연된 그리드 업데이트 완료")
                    except Exception as e:
                        print(f"지연된 그리드 업데이트 중 오류: {e}")
                
                QTimer.singleShot(100, delayed_update)  # 100ms 후 한 번 더 업데이트
                
                # 플래그 해제 (약간의 딜레이 후)
                QTimer.singleShot(500, lambda: setattr(self.app_instance, '_skip_video_frame_auto_show', False))
                
            except Exception as e:
                print(f"이미지 그리드 업데이트 중 오류: {e}")
                # 오류 발생 시에도 플래그 해제
                from PySide6.QtCore import QTimer
                QTimer.singleShot(500, lambda: setattr(self.app_instance, '_skip_video_frame_auto_show', False))
            
        except Exception as e:
            print(f"검색 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류 발생 시에도 플래그 해제
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, lambda: setattr(self.app_instance, '_skip_video_frame_auto_show', False))
    
    def collect_filter_groups(self):
        """그룹별로 검색 조건을 수집"""
        try:
            print("🔍 고급 검색 조건 수집 시작...")
            filter_groups = []
            
            # 필터 컨테이너 찾기
            filter_container = None
            if hasattr(self, 'filter_container') and self.filter_container:
                filter_container = self.filter_container
                print("✅ filter_container 속성에서 컨테이너 찾음")
            else:
                print("⚠️ filter_container 속성이 없음, children에서 검색...")
                for child in self.children():
                    if isinstance(child, QScrollArea):
                        scroll_widget = child.widget()
                        if scroll_widget:
                            for scroll_child in scroll_widget.children():
                                if hasattr(scroll_child, 'objectName') and scroll_child.objectName() == "filterContainer":
                                    filter_container = scroll_child
                                    print("✅ ScrollArea에서 filterContainer 찾음")
                                    break
                        break
            
            if not filter_container:
                print("❌ 필터 컨테이너를 찾을 수 없습니다.")
                return filter_groups
            
            layout = filter_container.layout()
            if not layout:
                print("❌ 필터 컨테이너에 레이아웃이 없습니다.")
                return filter_groups
            
            print(f"📋 레이아웃 아이템 수: {layout.count()}")
            current_group = []
            current_group_name = None
            current_group_connector = "Or"  # 기본값
            
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if not item:
                    continue
                
                print(f"🔍 아이템 {i} 처리 중...")
                
                if item.widget():
                    widget = item.widget()
                    print(f"  위젯: {type(widget).__name__}")
                    
                    # 그룹 제목 (QLabel)
                    if isinstance(widget, QLabel):
                        print(f"  그룹 제목 발견: {widget.text()}")
                        # 이전 그룹이 있으면 저장
                        if current_group:
                            filter_groups.append({
                                'name': current_group_name,
                                'conditions': current_group,
                                'group_connector': current_group_connector
                            })
                            print(f"📁 그룹 저장: {current_group_name} ({len(current_group)}개 조건)")
                        
                        # 새 그룹 시작
                        current_group_name = widget.text()
                        current_group = []
                        current_group_connector = "Or"  # 기본값
                        print(f"📁 새 그룹 시작: {current_group_name}")
                    
                    # 구분선 (QFrame) - 그룹 끝 표시
                    elif isinstance(widget, QFrame):
                        print(f"  구분선 발견")
                        if current_group:
                            filter_groups.append({
                                'name': current_group_name,
                                'conditions': current_group,
                                'group_connector': current_group_connector
                            })
                            print(f"📁 그룹 완료: {current_group_name} ({len(current_group)}개 조건)")
                            current_group = []
                            current_group_name = None
                
                elif item.layout():
                    layout_obj = item.layout()
                    print(f"  레이아웃: {type(layout_obj).__name__}")
                    
                    # 그룹 헤더인지 확인 (QLabel이 있는지)
                    is_group_header = False
                    for j in range(layout_obj.count()):
                        layout_item = layout_obj.itemAt(j)
                        if layout_item and layout_item.widget():
                            layout_widget = layout_item.widget()
                            if isinstance(layout_widget, QLabel):
                                is_group_header = True
                                print(f"    그룹 헤더의 QLabel 발견: {layout_widget.text()}")
                                break
                    
                    if is_group_header:
                        print(f"  그룹 헤더로 인식 - 건너뜀")
                        # 그룹 헤더는 이미 위에서 처리됨
                    else:
                        print(f"  필터 행으로 인식")
                        # 필터 행인 경우
                        condition = self.extract_condition_from_row(layout_obj)
                        if condition:
                            # 첫 번째 조건이면 그룹 간 연결 방식으로 사용
                            if len(current_group) == 0 and 'and_or' in condition:
                                current_group_connector = condition['and_or']
                                print(f"📁 그룹 간 연결 방식 (첫 번째 행에서): {current_group_connector}")
                            
                            current_group.append(condition)
                            print(f"  📝 조건 추가: {condition}")
                        else:
                            print(f"  ❌ 조건 추출 실패")
            
            # 마지막 그룹 처리
            if current_group:
                filter_groups.append({
                    'name': current_group_name,
                    'conditions': current_group,
                    'group_connector': current_group_connector
                })
                print(f"📁 마지막 그룹 완료: {current_group_name} ({len(current_group)}개 조건)")
            
            print(f"🔍 총 {len(filter_groups)}개 그룹 수집 완료")
            return filter_groups
            
        except Exception as e:
            print(f"그룹 수집 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def perform_grouped_search(self, filter_groups):
        """그룹별 검색 수행"""
        try:
            print(f"🔍 그룹별 검색 시작: {len(filter_groups)}개 그룹")
            
            group_results = []
            
            for group_idx, group in enumerate(filter_groups):
                group_name = group.get('name', f'Group {group_idx + 1}')
                conditions = group.get('conditions', [])
                
                print(f"📁 그룹 '{group_name}' 검색: {len(conditions)}개 조건")
                
                # 그룹 내 조건들 처리
                group_result = self.process_group_conditions(conditions)
                group_results.append(group_result)
                
                print(f"📁 그룹 '{group_name}' 결과: {len(group_result)}개 파일")
            
            # 그룹 간 AND/OR/Not And/Not Or 연산 처리
            final_results = []
            for group_idx, (group, group_result) in enumerate(zip(filter_groups, group_results)):
                if group_idx == 0:
                    # 첫 번째 그룹은 그대로 추가
                    final_results = group_result
                else:
                    # 그룹 간 연결 방식 확인
                    group_connector = group.get('group_connector', 'Or')
                    print(f"🔗 그룹 간 연결: {group_connector}")
                    
                    if group_connector == "And":
                        final_results = [img for img in final_results if img in group_result]
                        print(f"🔗 AND 연산 결과: {len(final_results)}개 파일")
                    elif group_connector == "Or":
                        final_results.extend(group_result)
                        print(f"🔗 OR 연산 결과: {len(final_results)}개 파일")
                    elif group_connector == "Not And":
                        # A NOT AND B := A ∧ ¬B (기존 결과에서 이번 그룹 결과를 제외)
                        final_results = [img for img in final_results if img not in group_result]
                        print(f"🔗 NOT AND 연산 결과: {len(final_results)}개 파일")
                    elif group_connector == "Not Or":
                        # A NOT OR B := (U\B) ∪ A. 여기서는 전체 우주 U를 현재 검색 대상에서 얻는다
                        universe = []
                        if hasattr(self.app_instance, 'search_results') and self.app_instance.search_results:
                            universe = self.app_instance.search_results
                        else:
                            # 이미지와 동영상을 모두 포함
                            image_list = getattr(self.app_instance, 'original_image_files', getattr(self.app_instance, 'image_files', []))
                            video_list = getattr(self.app_instance, 'original_video_files', getattr(self.app_instance, 'video_files', []))
                            universe = list(image_list) + list(video_list)
                        if not universe:
                            universe = final_results + group_result
                        not_b = [img for img in universe if img not in group_result]
                        final_results = list(set(final_results + not_b))
                        print(f"🔗 NOT OR 연산 결과: {len(final_results)}개 파일")
            
            # 중복 제거 (OR 연산 시 필요)
            final_results = list(set(final_results))
            
            print(f"🔍 최종 검색 결과: {len(final_results)}개 파일")
            return final_results
            
        except Exception as e:
            print(f"그룹별 검색 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def process_group_conditions(self, conditions):
        """그룹 내 조건들을 처리 (AND/OR/Not And/Not Or 로직 적용)"""
        try:
            if not conditions:
                return []
            
            results = []
            
            for condition in conditions:
                field = condition.get('field', '')
                operator = condition.get('operator', '=')
                value = condition.get('value', '')
                and_or = condition.get('and_or', 'And')
                
                if not field or not value:
                    continue
                
                # 필드별 검색 수행
                matches = []
                
                if field == "Tags":
                    matches = self.search_by_tags(operator, value)
                elif field == "File Name":
                    matches = self.search_by_filename(operator, value)
                elif field == "Date Created":
                    matches = self.search_by_date(operator, value)
                elif field == "File Size":
                    matches = self.search_by_size(operator, value)
                else:
                    matches = self.search_by_filename(operator, value)
                
                # 결과 조합 (그룹 내 AND/OR/Not And/Not Or 로직)
                if not results:
                    results = matches
                else:
                    if and_or == "And":
                        results = [img for img in results if img in matches]
                    elif and_or == "Or":
                        results = list(set(results + matches))
                    elif and_or == "Not And":
                        # A NOT AND B := A ∧ ¬B (기존 결과에서 이번 조건 결과 제외)
                        results = [img for img in results if img not in matches]
                    elif and_or == "Not Or":
                        # A NOT OR B := (U\B) ∪ A. 우주는 현재 검색 대상에서 추출
                        universe = []
                        if hasattr(self.app_instance, 'search_results') and self.app_instance.search_results:
                            universe = self.app_instance.search_results
                        else:
                            # 이미지와 동영상을 모두 포함
                            image_list = getattr(self.app_instance, 'original_image_files', getattr(self.app_instance, 'image_files', []))
                            video_list = getattr(self.app_instance, 'original_video_files', getattr(self.app_instance, 'video_files', []))
                            universe = list(image_list) + list(video_list)
                        if not universe:
                            universe = results + matches
                        not_b = [img for img in universe if img not in matches]
                        results = list(set(results + not_b))
            
            return results
            
        except Exception as e:
            print(f"그룹 조건 처리 중 오류: {e}")
            return []

    def extract_condition_from_row(self, row_layout):
        """필터 행에서 검색 조건 추출"""
        try:
            print(f"🔍 조건 추출 시작: {row_layout}")
            condition = {}
            
            # 재귀적으로 레이아웃을 순회하여 모든 위젯 수집
            def collect_widgets_from_layout(layout):
                collected = []
                try:
                    cnt = layout.count()
                except Exception:
                    return collected
                print(f"    ▶ 레이아웃 탐색: item 수={cnt}")
                for idx in range(cnt):
                    item = layout.itemAt(idx)
                    if not item:
                        continue
                    child_widget = item.widget()
                    child_layout = item.layout()
                    if child_widget is not None:
                        print(f"      • 위젯 발견: {type(child_widget).__name__} name='{getattr(child_widget,'objectName',lambda:'' )()}' -> {child_widget}")
                        collected.append(child_widget)
                    if child_layout is not None:
                        print(f"      ▷ 하위 레이아웃 진입")
                        collected.extend(collect_widgets_from_layout(child_layout))
                return collected

            widgets = collect_widgets_from_layout(row_layout)
            
            print(f"📋 추출된 위젯 수: {len(widgets)}")
            
            # 위젯들에서 값 추출 (objectName 우선)
            andor_combo = None
            field_combo = None
            op_combo = None
            value_input = None

            for i, widget in enumerate(widgets):
                print(f"위젯 {i}: {type(widget).__name__} - {widget}")
                name = widget.objectName() if hasattr(widget, 'objectName') else ""
                if isinstance(widget, QComboBox):
                    if name.startswith("andor_combo_"):
                        andor_combo = widget
                    elif name.startswith("field_combo_"):
                        field_combo = widget
                    elif name.startswith("op_combo_"):
                        op_combo = widget
                elif isinstance(widget, QLineEdit) and name.startswith("value_input_"):
                    value_input = widget

            # 폴백: 순회 중 직접 판별 (기존 로직)
            for widget in widgets:
                if andor_combo is None and isinstance(widget, QComboBox) and widget.currentText() in ["And", "Or", "Not And", "Not Or", "-"]:
                    andor_combo = widget
                if field_combo is None and isinstance(widget, QComboBox) and widget.currentText() in ["Tags", "File Name", "Date Created", "File Size"]:
                    field_combo = widget
                if op_combo is None and isinstance(widget, QComboBox) and widget.currentText() in ["=", "!=", ">", "<", ">=", "<=", "Contains", "Starts with", "First tag", "Last tag", "Tag position"]:
                    op_combo = widget
                if value_input is None and isinstance(widget, QLineEdit):
                    value_input = widget

            # 값 설정
            if field_combo is not None:
                condition['field'] = field_combo.currentText()
                print(f"    → field 설정: {condition['field']}")
            if op_combo is not None:
                condition['operator'] = op_combo.currentText()
                print(f"    → operator 설정: {condition['operator']}")
            if andor_combo is not None and andor_combo.currentText() != "-":
                condition['and_or'] = andor_combo.currentText()
                print(f"    → and_or 설정: {condition['and_or']}")
            if value_input is not None:
                text = value_input.text().strip()
                print(f"  LineEdit 텍스트: '{text}'")
                if text:
                    condition['value'] = text
                    print(f"    → value 설정: {text}")
            
            print(f"📝 추출된 조건: {condition}")
            
            # 최소한 field, operator, value가 있어야 유효한 조건
            if 'field' in condition and 'operator' in condition and 'value' in condition and condition['value']:
                print(f"✅ 유효한 조건: {condition}")
                return condition
            else:
                print(f"❌ 조건이 불완전합니다: {condition}")
                return None
            
        except Exception as e:
            print(f"조건 추출 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def perform_advanced_search(self, conditions):
        """실제 검색 수행"""
        try:
            # 일반 검색 결과가 있으면 그것을 기반으로, 없으면 전체 이미지에서 검색
            if hasattr(self.app_instance, 'search_results') and self.app_instance.search_results is not None:
                if self.app_instance.search_results:  # 일반 검색 결과가 있는 경우
                    search_target = self.app_instance.search_results
                    print(f"일반 검색 결과 기반으로 고급 검색: {len(search_target)}개")
                else:  # 일반 검색 결과가 빈 리스트인 경우 (매칭되는 파일이 없음)
                    print("일반 검색 결과가 없으므로 고급 검색 결과도 없음")
                    return []
            else:  # 일반 검색이 없는 경우 전체 이미지에서 검색
                if hasattr(self.app_instance, 'original_image_files') and self.app_instance.original_image_files:
                    search_target = self.app_instance.original_image_files
                    print(f"전체 이미지 목록에서 고급 검색: {len(search_target)}개")
                elif hasattr(self.app_instance, 'image_files') and self.app_instance.image_files:
                    search_target = self.app_instance.image_files
                    print(f"현재 이미지 목록에서 고급 검색: {len(search_target)}개")
                else:
                    print("검색할 이미지 목록이 없습니다.")
                    return []
            
            results = []
            
            for condition in conditions:
                field = condition.get('field', '')
                operator = condition.get('operator', '=')
                value = condition.get('value', '')
                and_or = condition.get('and_or', 'And')
                
                if not field or not value:
                    continue
                
                # 필드별 검색 수행
                matches = []
                
                if field == "Tags":
                    matches = self.search_by_tags(operator, value)
                elif field == "File Name":
                    matches = self.search_by_filename(operator, value)
                elif field == "Date Created":
                    matches = self.search_by_date(operator, value)
                elif field == "File Size":
                    matches = self.search_by_size(operator, value)
                else:
                    # 기본적으로 파일명으로 검색
                    matches = self.search_by_filename(operator, value)
                
                # 결과 조합
                if not results:
                    results = matches
                else:
                    if and_or == "And":
                        results = [img for img in results if img in matches]
                    else:  # Or
                        results = list(set(results + matches))
            
            return results
            
        except Exception as e:
            print(f"검색 수행 중 오류: {e}")
            return []
    
    def reset_search(self):
        """검색 초기화 - 원본 이미지 목록으로 복원"""
        try:
            print("🔄 고급 검색 초기화 중...")
            
            # 비디오 프레임 자동 표시 방지 플래그 설정
            self.app_instance._skip_video_frame_auto_show = True
            
            # 통합된 검색 초기화 함수 호출
            from search_module import reset_all_searches
            reset_all_searches(self.app_instance)
            
            # 플래그 해제 (약간의 딜레이 후)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, lambda: setattr(self.app_instance, '_skip_video_frame_auto_show', False))
            
            print("✅ 고급 검색 초기화 완료")
        except Exception as e:
            print(f"❌ 고급 검색 초기화 중 오류: {e}")
    
    def close_advanced_search(self):
        """고급 검색 닫기 - 오버레이 플러그인 방식으로 통일"""
        # 오버레이 플러그인 사용
        from center_panel_overlay_plugin import CenterPanelOverlayPlugin
        overlay_plugin = CenterPanelOverlayPlugin(self.app_instance)
        overlay_plugin.hide_overlay_card("advanced_search")
    
    # reset_to_original_images 함수는 search_module의 reset_all_searches로 대체됨
    
    def search_by_tags(self, operator, value):
        """태그로 검색"""
        matches = []
        try:
            # 원본 이미지 목록 사용
            search_target = getattr(self.app_instance, 'original_image_files', self.app_instance.image_files)
            for image_path in search_target:
                if hasattr(self.app_instance, 'get_image_tags'):
                    tags = self.app_instance.get_image_tags(image_path)
                else:
                    # 기본 태그 검색 (Autocomplete_tags.csv 기반)
                    tags = self.get_tags_from_csv(image_path)
                
                if operator == "=":
                    if value in tags:
                        matches.append(image_path)
                elif operator == "!=":
                    if value not in tags:
                        matches.append(image_path)
                elif operator == "Contains":
                    if any(value.lower() in tag.lower() for tag in tags):
                        matches.append(image_path)
                elif operator == "Starts with":
                    if any(tag.lower().startswith(value.lower()) for tag in tags):
                        matches.append(image_path)
                elif operator == "First tag":
                    # 첫 번째 태그 검색
                    if tags and value.lower() in tags[0].lower():
                        matches.append(image_path)
                elif operator == "Last tag":
                    # 마지막 태그 검색
                    if tags and value.lower() in tags[-1].lower():
                        matches.append(image_path)
                elif operator == "Tag position":
                    # 태그 위치 검색 (예: "1:solo" 또는 "solo:pokemon")
                    if self._search_by_tag_position(tags, value.lower()):
                        matches.append(image_path)
        
        except Exception as e:
            print(f"태그 검색 중 오류: {e}")
        
        return matches
    
    def _search_by_tag_position(self, tags, search_text):
        """태그 순서 기반 검색"""
        if not tags or not search_text:
            return False
        
        # "1:solo" 형태의 검색 (N번째 태그)
        if ':' in search_text:
            try:
                position_str, tag_name = search_text.split(':', 1)
                position = int(position_str.strip()) - 1  # 1-based to 0-based
                tag_name = tag_name.strip().lower()
                
                if 0 <= position < len(tags):
                    return tag_name in tags[position].lower()
            except (ValueError, IndexError):
                pass
        
        # "solo:pokemon" 형태의 검색 (태그 A가 태그 B보다 앞에 있는지)
        if ':' in search_text:
            try:
                tag_a, tag_b = search_text.split(':', 1)
                tag_a = tag_a.strip().lower()
                tag_b = tag_b.strip().lower()
                
                # 두 태그 모두 존재하는지 확인
                if tag_a in [tag.lower() for tag in tags] and tag_b in [tag.lower() for tag in tags]:
                    # 태그 A의 위치가 태그 B보다 앞에 있는지 확인
                    pos_a = next(i for i, tag in enumerate(tags) if tag.lower() == tag_a)
                    pos_b = next(i for i, tag in enumerate(tags) if tag.lower() == tag_b)
                    return pos_a < pos_b
            except (ValueError, StopIteration):
                pass
        
        return False
    
    def search_by_filename(self, operator, value):
        """파일명으로 검색 (이미지 + 동영상)"""
        matches = []
        try:
            import os
            # 원본 이미지 목록 사용
            image_target = getattr(self.app_instance, 'original_image_files', getattr(self.app_instance, 'image_files', []))
            # 원본 동영상 목록 사용
            video_target = getattr(self.app_instance, 'original_video_files', getattr(self.app_instance, 'video_files', []))
            # 이미지와 동영상을 모두 검색 대상에 포함
            search_target = list(image_target) + list(video_target)
            
            for file_path in search_target:
                filename = os.path.basename(file_path)
                
                if operator == "=":
                    if filename == value:
                        matches.append(file_path)
                elif operator == "!=":
                    if filename != value:
                        matches.append(file_path)
                elif operator == "Contains":
                    if value.lower() in filename.lower():
                        matches.append(file_path)
                elif operator == "Starts with":
                    if filename.lower().startswith(value.lower()):
                        matches.append(file_path)
        
        except Exception as e:
            print(f"파일명 검색 중 오류: {e}")
        
        return matches
    
    def search_by_date(self, operator, value):
        """날짜로 검색 (이미지 + 동영상)"""
        matches = []
        try:
            import os
            from datetime import datetime
            import re
            
            # 원본 이미지 목록 사용
            image_target = getattr(self.app_instance, 'original_image_files', getattr(self.app_instance, 'image_files', []))
            # 원본 동영상 목록 사용
            video_target = getattr(self.app_instance, 'original_video_files', getattr(self.app_instance, 'video_files', []))
            # 이미지와 동영상을 모두 검색 대상에 포함
            search_target = list(image_target) + list(video_target)
            
            # 검색 날짜 파싱 (여러 형식 지원)
            search_date = self._parse_date(value)
            if not search_date:
                print(f"날짜 파싱 실패: {value}")
                return matches
            
            for file_path in search_target:
                try:
                    file_time = os.path.getctime(file_path)
                    file_date = datetime.fromtimestamp(file_time)
                    
                    # 날짜 비교
                    if operator == "=":
                        if file_date.date() == search_date.date():
                            matches.append(file_path)
                    elif operator == "!=":
                        if file_date.date() != search_date.date():
                            matches.append(file_path)
                    elif operator == ">":
                        if file_date.date() > search_date.date():
                            matches.append(file_path)
                    elif operator == "<":
                        if file_date.date() < search_date.date():
                            matches.append(file_path)
                    elif operator == ">=":
                        if file_date.date() >= search_date.date():
                            matches.append(file_path)
                    elif operator == "<=":
                        if file_date.date() <= search_date.date():
                            matches.append(file_path)
                
                except Exception as e:
                    print(f"파일 날짜 처리 중 오류 ({file_path}): {e}")
                    continue
        
        except Exception as e:
            print(f"날짜 검색 중 오류: {e}")
        
        return matches
    
    def _parse_date(self, date_str):
        """다양한 날짜 형식 파싱"""
        try:
            from datetime import datetime
            import re
            
            if not date_str or not date_str.strip():
                return None
            
            date_str = date_str.strip()
            
            # 지원하는 날짜 형식들
            date_formats = [
                "%Y-%m-%d",      # 2024-01-15
                "%Y/%m/%d",      # 2024/01/15
                "%Y.%m.%d",      # 2024.01.15
                "%m/%d/%Y",      # 01/15/2024
                "%m-%d-%Y",      # 01-15-2024
                "%d/%m/%Y",      # 15/01/2024
                "%d-%m-%Y",      # 15-01-2024
                "%Y-%m-%d %H:%M:%S",  # 2024-01-15 14:30:00
                "%Y/%m/%d %H:%M:%S",  # 2024/01/15 14:30:00
            ]
            
            # 각 형식으로 시도
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # 상대적 날짜 처리 (예: "7일 전", "1주일 전", "1개월 전")
            relative_match = re.match(r'(\d+)\s*(일|주|개월|년)\s*전', date_str)
            if relative_match:
                from datetime import datetime, timedelta
                import calendar
                
                amount = int(relative_match.group(1))
                unit = relative_match.group(2)
                
                now = datetime.now()
                
                if unit == "일":
                    return now - timedelta(days=amount)
                elif unit == "주":
                    return now - timedelta(weeks=amount)
                elif unit == "개월":
                    # 월 단위는 대략적으로 처리
                    year = now.year
                    month = now.month - amount
                    while month <= 0:
                        month += 12
                        year -= 1
                    return datetime(year, month, now.day)
                elif unit == "년":
                    return datetime(now.year - amount, now.month, now.day)
            
            print(f"지원하지 않는 날짜 형식: {date_str}")
            return None
            
        except Exception as e:
            print(f"날짜 파싱 중 오류: {e}")
            return None
    
    def search_by_size(self, operator, value):
        """파일 크기로 검색 (이미지 + 동영상)"""
        matches = []
        try:
            import os
            import re
            
            # 원본 이미지 목록 사용
            image_target = getattr(self.app_instance, 'original_image_files', getattr(self.app_instance, 'image_files', []))
            # 원본 동영상 목록 사용
            video_target = getattr(self.app_instance, 'original_video_files', getattr(self.app_instance, 'video_files', []))
            # 이미지와 동영상을 모두 검색 대상에 포함
            search_target = list(image_target) + list(video_target)
            
            # 크기 파싱 (다양한 단위 지원)
            size_bytes = self._parse_size(value)
            if size_bytes is None:
                print(f"크기 파싱 실패: {value}")
                return matches
            
            for file_path in search_target:
                try:
                    file_size = os.path.getsize(file_path)
                    
                    if operator == "=":
                        # 정확한 크기 비교 (5% 오차 허용)
                        tolerance = size_bytes * 0.05
                        if abs(file_size - size_bytes) <= tolerance:
                            matches.append(file_path)
                    elif operator == "!=":
                        # 정확한 크기 비교 (5% 오차 허용)
                        tolerance = size_bytes * 0.05
                        if abs(file_size - size_bytes) > tolerance:
                            matches.append(file_path)
                    elif operator == ">":
                        if file_size > size_bytes:
                            matches.append(file_path)
                    elif operator == "<":
                        if file_size < size_bytes:
                            matches.append(file_path)
                    elif operator == ">=":
                        if file_size >= size_bytes:
                            matches.append(file_path)
                    elif operator == "<=":
                        if file_size <= size_bytes:
                            matches.append(file_path)
                
                except Exception as e:
                    print(f"파일 크기 처리 중 오류 ({file_path}): {e}")
                    continue
        
        except Exception as e:
            print(f"파일 크기 검색 중 오류: {e}")
        
        return matches
    
    def _parse_size(self, size_str):
        """다양한 크기 단위 파싱"""
        try:
            import re
            
            if not size_str or not size_str.strip():
                return None
            
            size_str = size_str.strip().lower()
            
            # 숫자와 단위 분리
            # 패턴: 숫자 + 선택적 공백 + 단위
            pattern = r'^(\d+(?:\.\d+)?)\s*(kb|mb|gb|tb|b|k|m|g|t)?$'
            match = re.match(pattern, size_str)
            
            if not match:
                # 단위 없이 숫자만 있는 경우 (기본값: MB)
                try:
                    size_value = float(size_str)
                    return size_value * 1024 * 1024  # MB로 가정
                except ValueError:
                    return None
            
            size_value = float(match.group(1))
            unit = match.group(2) or 'mb'  # 기본값: MB
            
            # 단위별 바이트 변환
            unit_multipliers = {
                'b': 1,
                'k': 1024,
                'kb': 1024,
                'm': 1024 * 1024,
                'mb': 1024 * 1024,
                'g': 1024 * 1024 * 1024,
                'gb': 1024 * 1024 * 1024,
                't': 1024 * 1024 * 1024 * 1024,
                'tb': 1024 * 1024 * 1024 * 1024,
            }
            
            if unit in unit_multipliers:
                return size_value * unit_multipliers[unit]
            else:
                print(f"지원하지 않는 크기 단위: {unit}")
                return None
            
        except Exception as e:
            print(f"크기 파싱 중 오류: {e}")
            return None
    
    def _update_operator_list(self, op_combo, field):
        """필드에 따라 연산자 목록을 동적으로 업데이트"""
        try:
            # 현재 선택된 연산자 저장
            current_operator = op_combo.currentText()
            
            # 필드별 연산자 목록 정의
            if field == "Tags":
                operators = ["=", "!=", "Contains", "Starts with", "First tag", "Last tag", "Tag position"]
            elif field == "File Name":
                operators = ["=", "!=", "Contains", "Starts with"]
            elif field == "Date Created":
                operators = ["=", "!=", ">", "<", ">=", "<="]
            elif field == "File Size":
                operators = ["=", "!=", ">", "<", ">=", "<="]
            else:
                operators = ["=", "!=", "Contains", "Starts with"]
            
            # 연산자 목록 업데이트
            op_combo.clear()
            op_combo.addItems(operators)
            
            # 이전에 선택된 연산자가 새 목록에 있으면 유지, 없으면 첫 번째 연산자로 설정
            if current_operator in operators:
                op_combo.setCurrentText(current_operator)
            else:
                op_combo.setCurrentText(operators[0])
                
        except Exception as e:
            print(f"연산자 목록 업데이트 중 오류: {e}")
    
    def _update_condition_interpretation(self, interpretation_label, field, operator, value, and_or_connector=None, is_first_row=False):
        """현재 입력된 조건을 자연어로 해석해서 별도 라벨에 표시"""
        try:
            interpretation_text = self._get_condition_interpretation(field, operator, value, and_or_connector, is_first_row)
            interpretation_label.setText(f"→ {interpretation_text}")
        except Exception as e:
            print(f"조건 해석 업데이트 중 오류: {e}")
            interpretation_label.setText("→ 조건을 입력하세요")
    
    def _get_condition_interpretation(self, field, operator, value, and_or_connector=None, is_first_row=False):
        """현재 조건을 자연어로 해석"""
        if not value or not value.strip():
            return "값을 입력하세요"
        
        value = value.strip()
        
        # AND/OR 연결자 해석 추가 (그룹 간 vs 그룹 내 구분)
        connector_text = ""
        if and_or_connector and and_or_connector != "-":
            if is_first_row:
                # 첫 번째 행: 그룹 간 연결
                if and_or_connector == "And":
                    connector_text = "이전 그룹의 조건과 동시에 "
                elif and_or_connector == "Or":
                    connector_text = "이전 그룹의 조건이거나 "
            else:
                # 나머지 행: 그룹 내 연결
                if and_or_connector == "And":
                    connector_text = "이전 행의 조건과 동시에 "
                elif and_or_connector == "Or":
                    connector_text = "이전 행의 조건이거나 "
        
        if field == "Tags":
            if operator == "=":
                return f"{connector_text}'{value}' 태그가 정확히 있는 이미지를 검색합니다"
            elif operator == "!=":
                return f"{connector_text}'{value}' 태그가 없는 이미지를 검색합니다"
            elif operator == "Contains":
                return f"{connector_text}태그에 '{value}'가 포함된 이미지를 검색합니다"
            elif operator == "Starts with":
                return f"{connector_text}태그가 '{value}'로 시작하는 이미지를 검색합니다"
            elif operator == "First tag":
                return f"{connector_text}첫 번째 태그에 '{value}'가 포함된 이미지를 검색합니다"
            elif operator == "Last tag":
                return f"{connector_text}마지막 태그에 '{value}'가 포함된 이미지를 검색합니다"
            elif operator == "Tag position":
                return f"{connector_text}태그 위치 조건 '{value}'에 맞는 이미지를 검색합니다"
            else:
                return f"{connector_text}태그 조건 '{value}'에 맞는 이미지를 검색합니다"
        
        elif field == "File Name":
            if operator == "=":
                return f"{connector_text}파일명이 '{value}'인 파일을 검색합니다"
            elif operator == "!=":
                return f"{connector_text}파일명이 '{value}'가 아닌 파일을 검색합니다"
            elif operator == "Contains":
                return f"{connector_text}파일명에 '{value}'가 포함된 파일을 검색합니다"
            elif operator == "Starts with":
                return f"{connector_text}파일명이 '{value}'로 시작하는 파일을 검색합니다"
            else:
                return f"{connector_text}파일명 조건 '{value}'에 맞는 파일을 검색합니다"
        
        elif field == "Date Created":
            if operator == "=":
                return f"{connector_text}'{value}'에 생성된 파일을 검색합니다"
            elif operator == "!=":
                return f"{connector_text}'{value}'가 아닌 날짜에 생성된 파일을 검색합니다"
            elif operator == ">":
                return f"{connector_text}'{value}' 이후에 생성된 파일을 검색합니다"
            elif operator == "<":
                return f"{connector_text}'{value}' 이전에 생성된 파일을 검색합니다"
            elif operator == ">=":
                return f"{connector_text}'{value}' 이후 또는 같은 날짜에 생성된 파일을 검색합니다"
            elif operator == "<=":
                return f"{connector_text}'{value}' 이전 또는 같은 날짜에 생성된 파일을 검색합니다"
            else:
                return f"{connector_text}생성 날짜 조건 '{value}'에 맞는 파일을 검색합니다"
        
        elif field == "File Size":
            if operator == "=":
                return f"{connector_text}크기가 '{value}'인 파일을 검색합니다 (5% 오차 허용)"
            elif operator == "!=":
                return f"{connector_text}크기가 '{value}'가 아닌 파일을 검색합니다"
            elif operator == ">":
                return f"{connector_text}크기가 '{value}'보다 큰 파일을 검색합니다"
            elif operator == "<":
                return f"{connector_text}크기가 '{value}'보다 작은 파일을 검색합니다"
            elif operator == ">=":
                return f"{connector_text}크기가 '{value}' 이상인 파일을 검색합니다"
            elif operator == "<=":
                return f"{connector_text}크기가 '{value}' 이하인 파일을 검색합니다"
            else:
                return f"{connector_text}파일 크기 조건 '{value}'에 맞는 파일을 검색합니다"
        
        else:
            return f"{connector_text}조건 '{value}'에 맞는 파일을 검색합니다"
    
    def get_tags_from_csv(self, image_path):
        """CSV에서 이미지 태그 가져오기"""
        try:
            import os
            import csv
            
            filename = os.path.basename(image_path)
            tags = []
            
            # Autocomplete_tags.csv에서 해당 이미지의 태그 찾기
            csv_path = "Autocomplete_tags.csv"
            if os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2 and row[0] == filename:
                            tags = row[1].split(',') if row[1] else []
                            break
        
        except Exception as e:
            print(f"CSV 태그 로드 중 오류: {e}")
        
        return tags


def create_advanced_search_widget(app_instance):
    """고급 검색 위젯 생성"""
    widget = AdvancedSearchWidget(app_instance=app_instance)
    return widget


def add_advanced_search_checkbox(app_instance, filter_dropdown):
    """전체 이미지 드롭박스 밑에 고급 검색 체크박스 추가"""
    # 고급 검색 체크박스 생성 (action_buttons_module 스타일 적용)
    class CustomCheckBox(QCheckBox):
        def __init__(self, text, parent=None):
            super().__init__(text, parent)
            self.setStyleSheet("""
                QCheckBox {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: 600;
                    spacing: 6px;
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
            """)
        
        def paintEvent(self, event):
            super().paintEvent(event)
            
            if self.isChecked():
                from PySide6.QtGui import QPainter, QPen, QColor, QFont
                from PySide6.QtCore import QRect, Qt
                
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
    
    app_instance.advanced_search_checkbox = CustomCheckBox("고급 검색")
    app_instance.advanced_search_checkbox.setChecked(True)  # 기본값을 체크 상태로
    
    # 체크박스 토글 이벤트 연결
    def on_checkbox_toggled(checked):
        app_instance.advanced_search_enabled = checked
        print(f"고급 검색: {'활성화' if checked else '비활성화'}")
    
    app_instance.advanced_search_checkbox.toggled.connect(on_checkbox_toggled)
    app_instance.advanced_search_enabled = True  # 초기값을 체크 상태로
    
    # 체크박스를 search_filter_card.body에 직접 추가
    try:
        # filter_dropdown의 부모를 따라가면서 search_filter_card 찾기
        current_widget = filter_dropdown
        search_filter_card = None
        
        while current_widget.parent():
            current_widget = current_widget.parent()
            if hasattr(current_widget, 'body') and hasattr(current_widget.body, 'addWidget'):
                search_filter_card = current_widget
                break
        
        if search_filter_card:
            search_filter_card.body.addWidget(app_instance.advanced_search_checkbox)
            print("고급 검색 체크박스가 search_filter_card에 추가되었습니다.")
        else:
            print("search_filter_card를 찾을 수 없습니다.")
    except Exception as e:
        print(f"체크박스 추가 중 오류: {e}")
    
    return app_instance.advanced_search_checkbox


def setup_search_focus_events(app_instance, search_input, advanced_search_card, preview_card, tag_tree_card):
    """검색창 포커스 이벤트 설정"""
    print("검색 포커스 이벤트 설정 시작")
    
    # 딜레이 타이머
    hide_timer = QTimer()
    hide_timer.setSingleShot(True)
    hide_timer.timeout.connect(lambda: hide_advanced_search())
    
    def hide_advanced_search():
        """고급 검색 섹션 숨김 - 오버레이 플러그인 방식으로 통일"""
        # 오버레이 플러그인 사용
        from center_panel_overlay_plugin import CenterPanelOverlayPlugin
        overlay_plugin = CenterPanelOverlayPlugin(app_instance)
        overlay_plugin.hide_overlay_card("advanced_search")
    
    def show_advanced_search():
        """고급 검색 섹션 표시 - 오버레이 플러그인 방식으로 통일"""
        print("고급 검색 섹션 표시")
        
        # 고급 검색 체크박스가 체크되지 않았으면 고급 검색을 열지 않음
        if hasattr(app_instance, 'advanced_search_checkbox'):
            if not app_instance.advanced_search_checkbox.isChecked():
                print("고급 검색이 비활성화되어 있어 고급 검색을 열지 않습니다.")
                return
        
        hide_timer.stop()  # 기존 타이머 취소
        
        # 오버레이 플러그인 사용
        from center_panel_overlay_plugin import CenterPanelOverlayPlugin
        overlay_plugin = CenterPanelOverlayPlugin(app_instance)
        overlay_plugin.show_overlay_card(advanced_search_card, "advanced_search")
    
    # 검색창 포커스 인 이벤트
    def on_focus_in(event):
        print("검색창 포커스 인")
        show_advanced_search()
        QLineEdit.focusInEvent(search_input, event)
    
    search_input.focusInEvent = on_focus_in
    
    # 검색창 포커스 아웃 이벤트 (딜레이 적용)
    def on_focus_out(event):
        print("검색창 포커스 아웃 - 닫기 여부 판단")
        try:
            # 포커스가 이동할 위젯이 고급 검색 카드 내부면 닫지 않음
            focus_widget = QApplication.focusWidget()
            if focus_widget is not None and advanced_search_card.isAncestorOf(focus_widget):
                print("포커스가 고급 검색 내부로 이동 - 닫기 취소")
                hide_timer.stop()
            else:
                print("포커스가 외부로 이동 - 80ms 후 닫기")
                hide_timer.start(80)
        except Exception as e:
            print(f"검색창 포커스 아웃 처리 오류: {e}")
            hide_timer.start(80)
        QLineEdit.focusOutEvent(search_input, event)
    
    search_input.focusOutEvent = on_focus_out
    
    # 고급 검색 섹션 내부 위젯들의 포커스 이벤트 처리
    def setup_widget_focus_events(widget):
        """위젯과 그 자식들의 포커스 이벤트 설정"""
        if hasattr(widget, 'focusInEvent'):
            original_focus_in = widget.focusInEvent
            
            def custom_focus_in(event):
                print(f"고급 검색 위젯 포커스 인: {widget.__class__.__name__}")
                hide_timer.stop()  # 숨김 타이머 취소
                original_focus_in(event)
            
            widget.focusInEvent = custom_focus_in
        
        # 포커스 아웃 이벤트도 처리 (고급 검색 내부 요소 간 이동 시 닫기 방지)
        if hasattr(widget, 'focusOutEvent'):
            original_focus_out = widget.focusOutEvent
            
            def custom_focus_out(event):
                print(f"고급 검색 위젯 포커스 아웃: {widget.__class__.__name__}")
                
                # ComboBox(드롭다운)의 경우 예외 처리
                if isinstance(widget, QComboBox):
                    # 드롭다운이 열려있는지 확인
                    if widget.view().isVisible():
                        print("드롭다운이 열려있음 - 닫기 취소")
                        original_focus_out(event)
                        return
                
                # 포커스가 이동할 위젯 확인
                focus_widget = QApplication.focusWidget()
                
                # 포커스가 None이면 그리드 갱신 중 - 닫지 않음
                if focus_widget is None:
                    print("포커스 None - 그리드 갱신 중, 닫기 취소")
                    original_focus_out(event)
                    return
                
                # 포커스가 고급 검색 내부로 이동 - 닫지 않음
                if advanced_search_card.isAncestorOf(focus_widget):
                    print("고급 검색 내부로 포커스 이동 - 닫기 취소")
                    original_focus_out(event)
                    return
                
                # 고급 검색 외부로 명시적 포커스 이동 시에만 닫기
                print("고급 검색 외부로 포커스 아웃 - 즉시 닫기")
                hide_timer.stop()
                hide_advanced_search()
                original_focus_out(event)
            
            widget.focusOutEvent = custom_focus_out
        
        # 자식 위젯들도 재귀적으로 처리
        for child in widget.findChildren(QWidget):
            if child != widget:
                setup_widget_focus_events(child)
    
    # 고급 검색 섹션 내부 위젯들의 포커스 이벤트 설정
    setup_widget_focus_events(advanced_search_card)
    
    print("검색 포커스 이벤트 설정 완료")


# 테스트용 독립 실행 코드
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    # 메인 윈도우
    window = QWidget()
    window.setWindowTitle("Advanced Search Widget")
    window.resize(900, 700)
    window.setStyleSheet("background: white;")
    
    # 레이아웃
    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Advanced Search Widget 추가
    search_widget = AdvancedSearchWidget()
    layout.addWidget(search_widget)
    
    window.show()
    sys.exit(app.exec())
