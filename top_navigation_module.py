"""
상단 네비게이션바 모듈
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class TopNavigationModule:
    """상단 네비게이션바 관리 모듈"""
    
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.dragging = False
        self.drag_start_position = None
        
    def create_navigation_bar(self):
        """상단 네비게이션바 생성"""
        nav_bar = QWidget()
        nav_bar.setFixedHeight(60)
        nav_bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, 
                    stop:0 rgba(10,10,15,0.95), stop:1 rgba(15,15,25,0.85));
                border-bottom: 1px solid rgba(75,85,99,0.2);
            }
        """)
        
        # 드래그 기능을 위한 마우스 이벤트 설정 (간단한 버전)
        nav_bar.mousePressEvent = self.mouse_press_event
        nav_bar.mouseMoveEvent = self.mouse_move_event
        
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(15, 8, 15, 8)
        nav_layout.setSpacing(15)
        
        # Logo/Title (왼쪽 탭 헤더에서 가져옴)
        icon_label = QLabel("🖼️")
        icon_label.setStyleSheet("""
            font-size: 28px;
            text-decoration: none;
            border: none;
            outline: none;
            background: transparent;
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title = QLabel("Image Library")
        title.setStyleSheet("""
            color: #FFFFFF;
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            font-size: 22px;
            font-weight: 700;
            text-decoration: none;
            border: none;
            outline: none;
        """)
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        subtitle = QLabel("Select images to tag")
        subtitle.setStyleSheet("""
            color: #B0BEC5;
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            font-size: 10px;
            font-weight: 300;
            text-decoration: none;
            border: none;
            outline: none;
        """)
        subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        nav_layout.addWidget(icon_label)
        nav_layout.addLayout(title_layout)
        nav_layout.addStretch()
        
        # Navigation buttons
        self.app_instance.btn_home = QPushButton("Home")
        self.app_instance.btn_home.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CFD8DC;
                border: none;
                padding: 8px 16px;
                font-family: 'Segoe UI';
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)

        self.app_instance.btn_settings = QPushButton("Settings")
        self.app_instance.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CFD8DC;
                border: none;
                padding: 8px 16px;
                font-family: 'Segoe UI';
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        self.app_instance.btn_help = QPushButton("Help")
        self.app_instance.btn_help.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CFD8DC;
                border: none;
                padding: 8px 16px;
                font-family: 'Segoe UI';
            font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        nav_layout.addWidget(self.app_instance.btn_home)
        nav_layout.addWidget(self.app_instance.btn_settings)
        nav_layout.addWidget(self.app_instance.btn_help)
        
        # Window controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(0)
        
        self.app_instance.btn_minimize = QPushButton("−")
        self.app_instance.btn_minimize.setFixedSize(30, 30)
        self.app_instance.btn_minimize.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #CFD8DC;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
        """)
        self.app_instance.btn_minimize.clicked.connect(self.app_instance.showMinimized)
        
        self.app_instance.btn_maximize = QPushButton("□")
        self.app_instance.btn_maximize.setFixedSize(30, 30)
        self.app_instance.btn_maximize.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #CFD8DC;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #FFFFFF;
            }
        """)
        self.app_instance.btn_maximize.clicked.connect(self.toggle_maximize)
        
        self.app_instance.btn_close = QPushButton("×")
        self.app_instance.btn_close.setFixedSize(30, 30)
        self.app_instance.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #CFD8DC;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #E53E3E;
                color: #FFFFFF;
            }
        """)
        self.app_instance.btn_close.clicked.connect(self.app_instance.close)
        
        controls_layout.addWidget(self.app_instance.btn_minimize)
        controls_layout.addWidget(self.app_instance.btn_maximize)
        controls_layout.addWidget(self.app_instance.btn_close)
        
        nav_layout.addLayout(controls_layout)
        
        return nav_bar
    
    def toggle_maximize(self):
        """창 모드와 전체화면 모드 전환"""
        if self.app_instance.isMaximized():
            # 현재 최대화 상태면 창 모드로 복원
            self.app_instance.showNormal()
            self.app_instance.btn_maximize.setText("□")
        else:
            # 현재 창 모드면 전체화면으로 최대화
            self.app_instance.showMaximized()
            self.app_instance.btn_maximize.setText("❐")
    
    def mouse_press_event(self, event):
        """마우스 누름 이벤트 - 드래그 시작"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_position = event.globalPosition().toPoint() - self.app_instance.frameGeometry().topLeft()
            event.accept()
    
    def mouse_move_event(self, event):
        """마우스 이동 이벤트 - 창 드래그"""
        if self.dragging and event.buttons() == Qt.LeftButton:
            # 창이 최대화되어 있으면 드래그하지 않음
            if not self.app_instance.isMaximized():
                self.app_instance.move(event.globalPosition().toPoint() - self.drag_start_position)
            event.accept()


# 단독 실행을 위한 테스트 코드
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    class TestApp:
        def __init__(self):
            self.btn_home = None
            self.btn_settings = None
            self.btn_help = None
            self.btn_minimize = None
            self.btn_maximize = None
            self.btn_close = None
        
        def showMinimized(self):
            print("창 최소화")
        
        def close(self):
            print("창 닫기")
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Top Navigation Module Test")
            self.setGeometry(100, 100, 800, 100)
            
            # 중앙 위젯
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 레이아웃
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # 테스트 앱 인스턴스
            test_app = TestApp()
            
            # 상단 네비게이션바 모듈 생성
            top_nav_module = TopNavigationModule(test_app)
            nav_bar = top_nav_module.create_navigation_bar()
            
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
