"""
왼쪽 세로 네비게이션바 모듈
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class LeftNavigationModule:
    """왼쪽 세로 네비게이션바 관리 모듈"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        
    def create_vertical_navigation_bar(self):
        """왼쪽 세로 네비게이션바 생성"""
        nav_widget = QWidget()
        nav_widget.setFixedWidth(60)
        nav_widget.setObjectName("VerticalNavBar")
        nav_widget.setStyleSheet("""
            QWidget#VerticalNavBar {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, 
                    stop:0 rgba(10,10,15,0.95), stop:1 rgba(15,15,25,0.85));
                border-right: 1px solid rgba(75,85,99,0.2);
            }
        """)
        
        layout = QVBoxLayout(nav_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 로고/아이콘 영역 (아이콘 제거)
        logo_widget = QWidget()
        logo_widget.setFixedHeight(60)
        logo_widget.setStyleSheet("""
            QWidget {
                background: rgba(0,0,0,0.2);
                border-bottom: 1px solid rgba(75,85,99,0.2);
            }
        """)
        
        layout.addWidget(logo_widget)
        
        # 폴더 관리 버튼 추가 (모듈 사용)
        from database_manager_module import FolderManagerButton, FolderManager
        folder_btn = FolderManagerButton()
        self.app_instance.folder_manager = FolderManager(self.app_instance)
        folder_btn.folder_clicked.connect(self.app_instance.folder_manager.open_folder)
        layout.addWidget(folder_btn)
        
        # 미라클 매니저 버튼 추가 (모듈 사용)
        from miracle_manager_module import MiracleManagerButton, MiracleManager
        miracle_btn = MiracleManagerButton()
        self.app_instance.miracle_manager = MiracleManager(self.app_instance)
        miracle_btn.miracle_clicked.connect(self.app_instance.miracle_manager.toggle_miracle_mode)
        layout.addWidget(miracle_btn)
        
        # 타임머신 버튼 추가 (모듈 사용) - 지연 임포트 및 안전 처리
        try:
            from timemachine_module import TimeMachineButton, TimeMachine
            timemachine_btn = TimeMachineButton()
            self.app_instance.timemachine_manager = TimeMachine(self.app_instance)
            timemachine_btn.timemachine_clicked.connect(self.app_instance.timemachine_manager.toggle_timemachine_mode)
            layout.addWidget(timemachine_btn)
        except Exception as e:
            # 임포트/초기화 실패 시 안전 폴백: 비활성 버튼 표시
            fallback_btn = QPushButton("🕐")
            fallback_btn.setFixedSize(60, 50)
            fallback_btn.setToolTip(f"Time Machine (비활성) — {str(e)[:120]}")
            fallback_btn.setEnabled(False)
            fallback_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6B7280;
                border: none;
                font-size: 18px;
                text-decoration: none;
                outline: none;
            }
            QPushButton:disabled { color: #4B5563; }
            """)
            layout.addWidget(fallback_btn)
        
        # 단축키 매니저 버튼 추가 (모듈 사용)
        from shortcut_manager_module import ShortcutManagerButton, ShortcutManager
        shortcut_btn = ShortcutManagerButton()
        self.app_instance.shortcut_manager = ShortcutManager(self.app_instance)
        shortcut_btn.shortcut_clicked.connect(self.app_instance.shortcut_manager.open_shortcuts)
        layout.addWidget(shortcut_btn)
        
        # 미라클 설정 모듈 초기화 (API 키 로드)
        try:
            self.app_instance.miracle_manager.initialize_settings(self.app_instance)
        except Exception as e:
            print(f"미라클 설정 모듈 초기화 실패: {e}")
        
        # 스페이서 추가
        layout.addStretch()
        
        # 설정 버튼
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(60, 50)
        settings_btn.setToolTip("설정")
        settings_btn.setStyleSheet("""
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
        settings_btn.clicked.connect(self.app_instance.open_settings)
        layout.addWidget(settings_btn)
        
        return nav_widget


# 단독 실행을 위한 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
    
    class TestApp:
        def __init__(self):
            self.miracle_manager = None
            self.folder_manager = None
        
        def open_settings(self):
            print("설정 열기")
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Left Navigation Module Test")
            self.setGeometry(100, 100, 200, 400)
            
            # 중앙 위젯
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 레이아웃
            layout = QHBoxLayout(central_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # 테스트 앱 인스턴스
            test_app = TestApp()
            
            # 왼쪽 네비게이션바 모듈 생성
            left_nav_module = LeftNavigationModule(test_app)
            nav_bar = left_nav_module.create_vertical_navigation_bar()
            
            layout.addWidget(nav_bar)
            
            # 스타일시트 적용
            self.setStyleSheet("""
                QMainWindow {
                    background: #1F2937;
                    color: #E5E7EB;
                }
            """)
    
    # 애플리케이션 실행
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
