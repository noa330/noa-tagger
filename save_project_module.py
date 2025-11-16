"""
세이브 프로젝트 모듈
프로젝트 저장 팝업창과 저장 로직을 담당
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QMessageBox, QScrollArea, QWidget, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from pathlib import Path
import shutil
import json


class SaveProjectDialog(QDialog):
    """프로젝트 저장 대화상자"""
    
    def __init__(self, app_instance, parent=None):
        super().__init__(parent)
        self.app_instance = app_instance
        self.save_success = False
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Save Project")
        self.setModal(True)
        self.resize(600, 400)
        
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
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title_label = QLabel("Save Project")
        title_label.setStyleSheet("""
            font-size: 25px;
            font-weight: 700;
            color: #E2E8F0;
            margin-bottom: 8px;
            font-family: 'Segoe UI';
        """)
        layout.addWidget(title_label)
        
        # 설명
        desc_label = QLabel("현재 작업 중인 프로젝트를 저장합니다.")
        desc_label.setStyleSheet("color: #9CA3AF; font-size: 11px; margin-top: 8px;")
        layout.addWidget(desc_label)
        
        # 현재 프로젝트 섹션
        current_project_label = QLabel("현재 프로젝트:")
        current_project_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 6px;
            padding: 6px 0px;
            border-bottom: 1px solid rgba(75,85,99,0.3);
        """)
        layout.addWidget(current_project_label)
        
        # 현재 프로젝트 슬롯 (장정보 스타일)
        current_project_name = getattr(self.app_instance, 'current_project_name', None)
        current_project_slot = QFrame()
        current_project_slot.setObjectName("CurrentProjectSlot")
        current_project_slot.setStyleSheet("""
            QFrame#CurrentProjectSlot {
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
            }
        """)
        current_project_slot_layout = QHBoxLayout(current_project_slot)
        current_project_slot_layout.setContentsMargins(8, 8, 8, 8)
        current_project_slot_layout.setSpacing(8)
        
        # 프로젝트명 입력 필드 (편집 가능)
        self.project_name_input = QLineEdit()
        if current_project_name:
            self.project_name_input.setText(current_project_name)
        else:
            self.project_name_input.setPlaceholderText("새 프로젝트명 입력 (선택사항)")
        self.project_name_input.setStyleSheet("""
            QLineEdit {
                color: #CBD5E0;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 0px;
            }
            QLineEdit:focus {
                border: none;
                background: transparent;
            }
        """)
        
        current_project_slot_layout.addWidget(self.project_name_input)
        current_project_slot_layout.addStretch()
        layout.addWidget(current_project_slot)
        
        # 프로젝트 정보 섹션
        info_label = QLabel("저장 정보:")
        info_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #E2E8F0;
            margin-bottom: 6px;
            padding: 6px 0px;
            border-bottom: 1px solid rgba(75,85,99,0.3);
        """)
        layout.addWidget(info_label)
        
        # 정보 표시 영역
        info_slot = QFrame()
        info_slot.setObjectName("InfoSlot")
        info_slot.setStyleSheet("""
            QFrame#InfoSlot {
                background: rgba(26,27,38,0.8);
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 4px;
            }
        """)
        
        info_layout = QVBoxLayout(info_slot)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(4)
        
        # 저장할 정보 표시
        self.info_labels = {}
        
        # 이미지 개수
        image_count = len(getattr(self.app_instance, 'image_files', []))
        image_label = QLabel(f"이미지: {image_count}개")
        image_label.setStyleSheet("color: #CBD5E0; font-size: 11px;")
        info_layout.addWidget(image_label)
        self.info_labels['image'] = image_label
        
        # 동영상 개수
        video_count = len(getattr(self.app_instance, 'video_files', []))
        video_label = QLabel(f"동영상: {video_count}개")
        video_label.setStyleSheet("color: #CBD5E0; font-size: 11px;")
        info_layout.addWidget(video_label)
        self.info_labels['video'] = video_label
        
        # 태그 개수
        all_tags = getattr(self.app_instance, 'all_tags', {})
        total_tags = sum(len(tags) for tags in all_tags.values())
        tag_label = QLabel(f"총 태그: {total_tags}개")
        tag_label.setStyleSheet("color: #CBD5E0; font-size: 11px;")
        info_layout.addWidget(tag_label)
        self.info_labels['tag'] = tag_label
        
        # 태그가 있는 이미지 개수
        tagged_images = len([tags for tags in all_tags.values() if tags])
        tagged_label = QLabel(f"태그된 이미지: {tagged_images}개")
        tagged_label.setStyleSheet("color: #CBD5E0; font-size: 11px;")
        info_layout.addWidget(tagged_label)
        self.info_labels['tagged'] = tagged_label
        
        info_layout.addStretch()
        layout.addWidget(info_slot)
        
        # 프로젝트 덮어쓰기 체크박스 (버튼 위 영역)
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setContentsMargins(0, 8, 0, 8)
        
        # 커스텀 체크박스 클래스 정의 (데이터베이스 텍스트 불러오기와 동일 디자인)
        class CustomCheckBox(QCheckBox):
            def __init__(self, text, parent=None):
                super().__init__(text, parent)
                self.setStyleSheet("""
                    QCheckBox {
                        color: #FFFFFF;
                        font-size: 12px;
                        font-weight: 600;
                        spacing: 6px;
                        background: transparent;
                        border: none;
                        padding: 0px;
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
        
        self.overwrite_checkbox = CustomCheckBox("프로젝트 덮어쓰기")
        self.overwrite_checkbox.setChecked(True)  # 기본값: 체크됨
        # 현재 프로젝트가 없으면 체크박스 비활성화
        if not current_project_name:
            self.overwrite_checkbox.setEnabled(False)
        checkbox_layout.addWidget(self.overwrite_checkbox)
        checkbox_layout.addStretch()
        
        layout.addLayout(checkbox_layout)
        
        # 하단 버튼들
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # 취소 버튼 (왼쪽)
        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # 스트레치로 중간 공간 채우기
        button_layout.addStretch()
        
        # 저장 버튼 (오른쪽)
        save_btn = QPushButton("저장")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #10B981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #059669;
            }
            QPushButton:pressed {
                background: #047857;
            }
        """)
        save_btn.clicked.connect(self.save_project)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def save_project(self):
        """프로젝트 저장 실행"""
        try:
            from database_manager_module import DatabaseManager
            db_manager = DatabaseManager(self.app_instance)
            # 덮어쓰기 체크박스 상태 전달
            overwrite = self.overwrite_checkbox.isChecked()
            
            # 편집된 프로젝트명 가져오기
            edited_project_name = self.project_name_input.text().strip()
            
            # 덮어쓰기 모드일 때는 편집된 프로젝트명으로 덮어쓰기 (프로젝트명이 있으면)
            if overwrite:
                if edited_project_name:
                    # 편집된 프로젝트명으로 덮어쓰기
                    success = db_manager.save_project_database(overwrite=True, project_name=edited_project_name)
                else:
                    # 프로젝트명이 없으면 현재 프로젝트에 덮어쓰기
                    success = db_manager.save_project_database(overwrite=True)
            else:
                # 덮어쓰기 모드가 아니면 편집된 프로젝트명으로 새 프로젝트 저장
                success = db_manager.save_project_database(overwrite=False, project_name=edited_project_name if edited_project_name else None)
            
            if success:
                self.save_success = True
                self.accept()
            else:
                # 오류는 DatabaseManager에서 이미 메시지 박스로 표시됨
                pass
            
        except Exception as e:
            self.show_error_message("오류", f"프로젝트 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def show_error_message(self, title, message):
        """에러 메시지 표시"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Critical)
        
        # 다크 테마 스타일 적용
        msg_box.setStyleSheet("""
            QMessageBox {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(15,15,25,0.95), stop:1 rgba(20,20,30,0.85));
                color: #F0F2F5;
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 8px;
                font-family: 'Segoe UI';
            }
            
            QMessageBox QLabel {
                color: #F0F2F5;
                font-size: 12px;
                padding: 10px;
                background: transparent;
                font-family: 'Segoe UI';
            }
            
            QMessageBox QPushButton {
                background: #EF4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 600;
                min-width: 80px;
                font-family: 'Segoe UI';
            }
            
            QMessageBox QPushButton:hover {
                background: #F87171;
            }
            
            QMessageBox QPushButton:pressed {
                background: #DC2626;
            }
        """)
        
        msg_box.exec()


def show_save_project_dialog(app_instance):
    """세이브 프로젝트 대화상자 표시"""
    dialog = SaveProjectDialog(app_instance, app_instance)
    result = dialog.exec()
    
    if result == QDialog.Accepted and dialog.save_success:
        if hasattr(app_instance, 'statusBar'):
            app_instance.statusBar().showMessage("프로젝트 저장 완료")
        return True
    
    return False





