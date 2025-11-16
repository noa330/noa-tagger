"""
비디오 타임라인 모듈
- 프레임 롤과 시간 눈금 UI를 담당
- 동영상 프리뷰 모듈과 분리된 전용 카드 제공
"""

from PySide6.QtCore import Qt, QTimer, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QImage
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QProgressBar


class FrameTimeline(QWidget):
    """프레임 타임라인 위젯 - 스마트 캐싱 방식"""

    selectionChanged = Signal(int, int)
    needMoreFrames = Signal(list)  # 필요한 시간(ms) 리스트
    positionChanged = Signal(int)  # 재생 위치 변경 시그널 (ms)
    playheadDragStarted = Signal()  # 헤드 드래그 시작
    playheadDragEnded = Signal()  # 헤드 드래그 종료

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame_cache = {}  # {time_ms: QPixmap} - 생성된 프레임 캐시
        self.duration = 0
        self.current_position = 0  # 현재 재생 위치 (ms)
        self.selection_start = 0
        self.selection_end = 1

        self.dragging_start = False
        self.dragging_end = False
        self.dragging_body = False
        self.dragging_zoom_box = False  # 줌 섹션 박스 드래그 플래그
        self.dragging_playhead = False  # 재생 헤드 드래그 플래그 (파란색/빨간색)
        self.drag_start_pos = None
        self.initial_selection_start = 0
        self.initial_selection_end = 1
        self.initial_scroll_offset = 0.0  # 줌 박스 드래그 시작 시 스크롤 오프셋

        self.zoom_level = 1.0
        self.min_zoom = 1.0  # 최소 줌은 1.0 (1 이하로 내려가지 않음)
        self.max_zoom = 5.0

        self.base_frame_width = 100  # 기본 프레임 너비
        self.fixed_frame_count = 10  # 고정된 프레임 개수 (줌과 무관)
        self.scroll_offset = 0.0  # 스크롤 오프셋 (0.0~1.0)

        self.setMinimumHeight(100)
        self.setMaximumHeight(100)
        self.setCursor(Qt.ArrowCursor)

        self.setStyleSheet(
            """
            FrameTimeline {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
        """
        )

    def clear_cache(self):
        """프레임 캐시 초기화 (새 비디오 로드 시 호출)"""
        self.frame_cache.clear()
        print("🧹 프레임 캐시 초기화됨")
        self.update()

    def set_duration(self, duration, current_position_ms=0):
        """비디오 duration 설정"""
        old_duration = self.duration
        self.duration = duration
        
        # 새 비디오 로드 시 선택 범위는 자동으로 설정하지 않음
        # 사용자가 타임라인에서 직접 드래그해서 선택 범위를 설정하도록 함
        
        self.update()

    def set_current_position(self, position_ms):
        """현재 재생 위치 설정"""
        self.current_position = position_ms
        self.update()

    def add_frame_to_cache(self, time_ms, pixmap):
        """프레임을 캐시에 추가"""
        self.frame_cache[time_ms] = pixmap
        self.update()

    def get_total_timeline_width(self):
        """전체 타임라인 너비 계산 - 항상 위젯 너비와 동일"""
        return self.width()

    def calculate_visible_frames(self):
        """현재 화면에 보이는 프레임 개수와 시간 계산 - 줌에 따라 시간 범위 조절"""
        if self.duration <= 0:
            return []

        # 고정된 개수 사용
        num_visible = self.fixed_frame_count

        # 줌 레벨에 따라 보여줄 시간 범위 계산
        # zoom 1.0 = 전체 duration
        # zoom 2.0 = duration의 50%
        # zoom 5.0 = duration의 20%
        visible_duration = self.duration / max(self.zoom_level, 1.0)  # 최소 줌 1.0 보장

        # 스크롤 오프셋에 따라 시작 시간 계산
        max_offset = self.duration - visible_duration
        start_time = max_offset * self.scroll_offset if max_offset > 0 else 0
        end_time = start_time + visible_duration

        # 시작~끝 시간 범위를 10개 프레임으로 균등 분배
        frame_times = []
        for i in range(num_visible):
            time_ms = int(start_time + (i / max(1, num_visible - 1)) * visible_duration)
            time_ms = min(time_ms, int(self.duration))  # duration 초과 방지
            frame_times.append(time_ms)

        return frame_times

    def get_actual_frame_width(self):
        """실제로 그려질 프레임 너비 계산 - 항상 위젯 폭을 고정 개수로 나눔"""
        return self.width() / self.fixed_frame_count

    def check_and_request_frames(self):
        """필요한 프레임 확인 후 요청"""
        needed_times = self.calculate_visible_frames()

        # 캐시에 없는 프레임만 필터링
        missing_times = [t for t in needed_times if t not in self.frame_cache]

        if missing_times or len(needed_times) > 0:
            if len(needed_times) > 0:
                start_sec = needed_times[0] / 1000.0
                end_sec = needed_times[-1] / 1000.0
                print(f"🎬 시간 범위: {start_sec:.1f}s ~ {end_sec:.1f}s (줌: {self.zoom_level:.2f}x)")

            if missing_times:
                print(f"📥 {len(missing_times)}개 프레임 필요 (캐시: {len(self.frame_cache)}개)")
                self.needMoreFrames.emit(missing_times)

    def get_visible_time_range(self):
        """현재 줌/스크롤 기준 가시 시간 구간 반환: (start_ms, end_ms, duration_ms)"""
        if self.duration <= 0:
            return (0, 0, 0)
        visible_duration = self.duration / max(self.zoom_level, 1.0)  # 최소 줌 1.0 보장
        max_offset = max(0, self.duration - visible_duration)
        start_time = max(0, min(max_offset, max_offset * self.scroll_offset))
        end_time = start_time + visible_duration
        return (int(start_time), int(end_time), int(visible_duration))

    def _update_selection_after_view_change(self):
        """뷰 변경(줌/스크롤) 후 선택 범위 재계산 및 시그널 emit"""
        if self.selection_start < self.selection_end:
            # 현재 선택 범위를 다시 계산해서 시그널 emit
            vis_start_ms, vis_end_ms, vis_dur_ms = self.get_visible_time_range()
            if vis_dur_ms > 0:
                start_ms = int(vis_start_ms + self.selection_start * vis_dur_ms)
                end_ms = int(vis_start_ms + self.selection_end * vis_dur_ms)
            else:
                start_ms = int(self.selection_start * self.duration)
                end_ms = int(self.selection_end * self.duration)
            
            start_ms = max(0, min(self.duration, start_ms))
            end_ms = max(0, min(self.duration, end_ms))
            
            self.selectionChanged.emit(start_ms, end_ms)
    
    def set_selection(self, start, end):
        """선택 범위 설정 (가시 영역 기준)"""
        self.selection_start = max(0, min(1, start))
        self.selection_end = max(0, min(1, end))
        if self.selection_start > self.selection_end:
            self.selection_start, self.selection_end = self.selection_end, self.selection_start
        self.update()

        # 가시 영역 기준으로 시간 계산
        vis_start_ms, vis_end_ms, vis_dur_ms = self.get_visible_time_range()
        if vis_dur_ms > 0:
            # 선택 비율을 가시 영역의 시간 범위에 매핑
            start_ms = int(vis_start_ms + self.selection_start * vis_dur_ms)
            end_ms = int(vis_start_ms + self.selection_end * vis_dur_ms)
        else:
            # 가시 영역이 없으면 전체 duration 기준
            start_ms = int(self.selection_start * self.duration)
            end_ms = int(self.selection_end * self.duration)
        
        start_ms = max(0, min(self.duration, start_ms))
        end_ms = max(0, min(self.duration, end_ms))
        
        self.selectionChanged.emit(start_ms, end_ms)

    def format_timecode(self, ms):
        """타임코드 포맷"""
        total_seconds = ms / 1000.0
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60

        if ms % 1000 == 0:
            return f"{minutes:02d}:{int(seconds):02d}"
        else:
            return f"{minutes:02d}:{seconds:06.3f}"

    def wheelEvent(self, event):
        """마우스 휠로 줌/스크롤"""
        modifiers = event.modifiers()
        delta = event.angleDelta().y()

        if modifiers & Qt.ShiftModifier:
            # Shift + 휠: 좌우 스크롤
            if self.zoom_level > 1.0:  # 줌 인 상태일 때만 스크롤 가능
                scroll_delta = -delta / 1200.0  # 스크롤 속도 조절
                new_offset = self.scroll_offset + scroll_delta
                new_offset = max(0.0, min(1.0, new_offset))

                if new_offset != self.scroll_offset:
                    self.scroll_offset = new_offset
                    print(f"📜 스크롤: {self.scroll_offset:.2f}")
                    self.update()
                    # 스크롤 후 새로운 시간 범위의 프레임 요청
                    QTimer.singleShot(100, self.check_and_request_frames)
                    # 선택 범위 재계산 및 시그널 emit
                    self._update_selection_after_view_change()
        else:
            # 일반 휠: 줌 in/out (0.01 단위 미세 조정)
            # 휠 방향: 휠 up(delta > 0) → 축소, 휠 down(delta < 0) → 확대
            step = 0.01
            new_zoom = self.zoom_level - step if delta > 0 else self.zoom_level + step
            new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))

            if new_zoom != self.zoom_level:
                self.zoom_level = new_zoom

                # 줌 아웃하면 스크롤 오프셋 초기화
                if new_zoom <= 1.0:
                    self.scroll_offset = 0.0

                print(f"🔍 줌: {self.zoom_level:.2f}x (프레임 개수: {self.fixed_frame_count}개 고정)")
                self.update()
                # 줌 변경 후 새로운 시간 범위의 프레임 요청
                QTimer.singleShot(100, self.check_and_request_frames)
                # 선택 범위 재계산 및 시그널 emit
                self._update_selection_after_view_change()

        event.accept()

    def get_zoom_box_rect(self):
        """줌 섹션 박스의 위치와 크기 반환: (x, y, width, height) 또는 None"""
        if self.duration <= 0 or self.zoom_level <= 1.0:
            return None

        width = self.width()
        timecode_height = 24

        if width <= 0:
            return None

        # 전체 duration 기준 픽셀당 밀리초
        px_per_ms = width / self.duration

        # 현재 보이는 시간 범위
        vis_start, vis_end, vis_dur = self.get_visible_time_range()
        if vis_dur <= 0:
            return None

        # 전체 타임라인 기준 시작 위치 (0부터 시작)
        box_x = int(vis_start * px_per_ms)
        box_w = max(1, int(vis_dur * px_per_ms))

        return (box_x, 0, box_w, timecode_height)

    def get_playhead_positions(self):
        """재생 헤드의 위치 반환: (red_x, blue_x) 또는 (None, None)"""
        if self.duration <= 0:
            return (None, None)

        width = self.width()

        if width <= 0:
            return (None, None)

        # 빨간색 헤드 위치 (전체 타임라인 기준)
        px_per_ms_full = width / self.duration
        red_x = int(self.current_position * px_per_ms_full)

        # 파란색 헤드 위치 (줌/스크롤 가시 구간 기준)
        total_timeline_width = self.get_total_timeline_width()
        blue_x = None

        if total_timeline_width > 0:
            vis_start, vis_end, vis_dur = self.get_visible_time_range()
            if vis_dur > 0 and vis_start <= self.current_position <= vis_end:
                position_ratio = (self.current_position - vis_start) / vis_dur
                blue_x = int(position_ratio * total_timeline_width)

        return (red_x, blue_x)

    def paintEvent(self, event):
        """타임라인 그리기"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = self.rect()
        width = rect.width()
        height = rect.height()

        if self.duration <= 0:
            return

        timecode_height = 24
        frame_height = height - timecode_height

        # 필요한 프레임 시간들
        visible_times = self.calculate_visible_frames()
        if len(visible_times) == 0:
            return

        # 실제 프레임 너비 (위젯에 꽉 차도록) + 레퍼런스 스타일 간격 적용
        gap = 2  # 프레임 사이 미세 간격
        actual_frame_width = self.get_actual_frame_width()
        draw_width = max(1, int(actual_frame_width - gap))

        # 프레임 트랙 라운드 박스(줌 섹션 시각화)
        track_rect = QRect(0, timecode_height, width, frame_height)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(track_rect, 8, 8)

        # 프레임 그리기
        current_x = 0
        for time_ms in visible_times:
            # 캐시에서 프레임 가져오기
            if time_ms in self.frame_cache:
                thumb = self.frame_cache[time_ms]

                # 프레임 그리기 (라운드 코너 + 미세 간격)
                x = int(current_x + gap / 2)
                rounded_radius = 6
                scaled_thumb = thumb.scaled(
                    int(draw_width),
                    int(frame_height),
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation,
                )
                from PySide6.QtGui import QPainterPath

                path = QPainterPath()
                path.addRoundedRect(
                    QRect(x, timecode_height, scaled_thumb.width(), int(frame_height)),
                    rounded_radius,
                    rounded_radius,
                )
                painter.save()
                painter.setClipPath(path)
                painter.drawPixmap(x, timecode_height, scaled_thumb)
                painter.restore()
            else:
                # 캐시에 없으면 플레이스홀더
                x = int(current_x + gap / 2)
                painter.fillRect(
                    x,
                    timecode_height,
                    int(draw_width),
                    int(frame_height),
                    QColor(48, 50, 60),
                )

            current_x += actual_frame_width

        # 전체 타임라인 너비 (실제 그려진 프레임들의 전체 너비)
        total_timeline_width = self.get_total_timeline_width()

        # 선택 영역 (파란 사각 테두리 제거, 외부 음영 + 슬림 핸들만)
        if self.selection_start < self.selection_end and total_timeline_width > 0:
            sel_start_x = self.selection_start * total_timeline_width
            sel_end_x = self.selection_end * total_timeline_width

            # 선택 안된 부분 어둡게
            if sel_start_x > 0:
                painter.fillRect(
                    0,
                    timecode_height,
                    int(sel_start_x),
                    frame_height,
                    QColor(0, 0, 0, 180),
                )
            if sel_end_x < total_timeline_width:
                painter.fillRect(
                    int(sel_end_x),
                    timecode_height,
                    int(total_timeline_width - sel_end_x),
                    frame_height,
                    QColor(0, 0, 0, 180),
                )

            # 슬림 핸들 (라운드 캡, 과한 사각 테두리 제거)
            handle_width = 4
            handle_radius = 2
            from PySide6.QtGui import QPainterPath

            painter.setBrush(QColor(255, 255, 255, 180))
            painter.setPen(Qt.NoPen)
            left_handle = QPainterPath()
            left_handle.addRoundedRect(
                QRect(int(sel_start_x), timecode_height, handle_width, frame_height),
                handle_radius,
                handle_radius,
            )
            right_handle = QPainterPath()
            right_handle.addRoundedRect(
                QRect(int(sel_end_x) - handle_width, timecode_height, handle_width, frame_height),
                handle_radius,
                handle_radius,
            )
            painter.drawPath(left_handle)
            painter.drawPath(right_handle)

        # 상단 눈금자 (전체 duration 기준 - 고정 스케일)
        vis_start_for_ticks, vis_end_for_ticks, vis_dur_for_ticks = (
            0,
            int(self.duration),
            int(self.duration),
        )
        if vis_dur_for_ticks > 0 and width > 0:
            px_per_ms = width / vis_dur_for_ticks
            candidates = [100, 200, 500, 1000, 2000, 5000, 10000, 15000, 30000, 60000]
            target_minor_px = 16
            minor_interval = candidates[0]
            for c in candidates:
                if c * px_per_ms >= target_minor_px:
                    minor_interval = c
                    break
            major_every = 5
            first_tick = (
                (vis_start_for_ticks + minor_interval - 1) // minor_interval
            ) * minor_interval
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            font = painter.font()
            font.setPixelSize(9)
            painter.setFont(font)
            y_top = 0
            t = first_tick
            while t <= vis_end_for_ticks:
                x = int((t - vis_start_for_ticks) * px_per_ms)
                is_major = ((t // minor_interval) % major_every) == 0
                h = 10 if is_major else 5
                painter.drawLine(x, y_top, x, y_top + h)
                if is_major:
                    label = self.format_timecode(t)
                    tw = painter.fontMetrics().horizontalAdvance(label)
                    painter.setPen(QColor(220, 224, 230, 180))
                    painter.drawText(x - tw // 2, y_top + h + 10, label)
                    painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
                t += minor_interval

            # 눈금자 위에 현재 줌 섹션 박스 표시 (줌 인 상태에서만)
            vis_start, vis_end, vis_dur = self.get_visible_time_range()
            if self.zoom_level > 1.0 and vis_dur > 0:
                box_x = int((vis_start - vis_start_for_ticks) * px_per_ms)
                box_w = max(1, int((vis_end - vis_start) * px_per_ms))
                zoom_rect = QRect(box_x, 0, box_w, timecode_height)
                painter.fillRect(zoom_rect, QColor(255, 255, 255, 15))

        # 🔵 현재 재생 위치 표시 (줌/스크롤 가시 구간 기준) - 프레임 영역에서만
        if self.duration > 0 and total_timeline_width > 0:
            vis_start, vis_end, vis_dur = self.get_visible_time_range()
            if vis_dur > 0 and vis_start <= self.current_position <= vis_end:
                position_ratio = (self.current_position - vis_start) / vis_dur
                playhead_x = position_ratio * total_timeline_width
                painter.setPen(QPen(QColor(59, 130, 246), 2))
                painter.drawLine(
                    int(playhead_x),
                    timecode_height,
                    int(playhead_x),
                    height,
                )
                # 삼각형 제거 - 막대바만 표시

        # 🔵 눈금자(전체 타임 기준)용 리얼타임 바늘 표시 (파란색으로 통일)
        if self.duration > 0 and width > 0:
            px_per_ms_full = width / self.duration
            needle_x = int(self.current_position * px_per_ms_full)
            painter.setPen(QPen(QColor(59, 130, 246), 2))  # 프레임롤 바늘과 동일한 파란색
            painter.drawLine(needle_x, 0, needle_x, timecode_height)

    def mousePressEvent(self, event):
        """마우스 누름"""
        if event.button() != Qt.LeftButton:
            return

        pos_x = event.position().x()
        pos_y = event.position().y()
        timecode_height = 24
        hit_tolerance = 8  # 헤드 클릭 감지 범위 (픽셀)

        # 재생 헤드 클릭 확인 (빨간색 또는 파란색)
        if self.duration > 0:
            red_x, blue_x = self.get_playhead_positions()

            # 빨간색 헤드 클릭 확인 (눈금자 영역)
            if red_x is not None and pos_y < timecode_height:
                if abs(pos_x - red_x) <= hit_tolerance:
                    self.dragging_playhead = True
                    self.drag_start_pos = pos_x
                    self.setCursor(Qt.SizeHorCursor)
                    self.playheadDragStarted.emit()
                    return

            # 파란색 헤드 클릭 확인 (프레임 영역)
            if blue_x is not None and pos_y >= timecode_height:
                if abs(pos_x - blue_x) <= hit_tolerance:
                    self.dragging_playhead = True
                    self.drag_start_pos = pos_x
                    self.setCursor(Qt.SizeHorCursor)
                    self.playheadDragStarted.emit()
                    return

        # 줌 섹션 박스 영역 클릭 확인 (줌 인 상태일 때만)
        if pos_y < timecode_height and self.zoom_level > 1.0:
            zoom_box = self.get_zoom_box_rect()
            if zoom_box:
                box_x, box_y, box_w, box_h = zoom_box
                if box_x <= pos_x <= box_x + box_w and box_y <= pos_y <= box_y + box_h:
                    self.dragging_zoom_box = True
                    self.drag_start_pos = pos_x
                    self.initial_scroll_offset = self.scroll_offset
                    self.setCursor(Qt.SizeHorCursor)
                    return

        if pos_y < timecode_height:
            # 눈금자 영역 클릭 시 재생 위치 변경 및 선택 범위 업데이트
            if self.duration > 0:
                width = self.width()
                if width > 0:
                    # 가시 영역 기준으로 클릭 위치 계산
                    vis_start_ms, vis_end_ms, vis_dur_ms = self.get_visible_time_range()
                    if vis_dur_ms > 0:
                        click_ratio = pos_x / width if width > 0 else 0
                        click_time_ms = int(vis_start_ms + click_ratio * vis_dur_ms)
                        click_time_ms = max(0, min(self.duration, click_time_ms))
                    else:
                        px_per_ms = width / self.duration
                        click_time_ms = int(pos_x / px_per_ms)
                        click_time_ms = max(0, min(self.duration, click_time_ms))
                    
                    self.positionChanged.emit(click_time_ms)
                    
                    # 눈금 영역 클릭 시 선택 범위를 클릭 위치로 업데이트 (작은 범위)
                    if vis_dur_ms > 0:
                        # 클릭 위치를 가시 영역 기준 비율로 변환
                        click_ratio = (click_time_ms - vis_start_ms) / vis_dur_ms if vis_dur_ms > 0 else 0
                        click_ratio = max(0.0, min(1.0, click_ratio))
                        # 작은 범위로 선택 (예: 0.1초)
                        small_range_ratio = 0.05  # 가시 영역의 5%
                        new_start = max(0.0, click_ratio - small_range_ratio / 2)
                        new_end = min(1.0, click_ratio + small_range_ratio / 2)
                        self.set_selection(new_start, new_end)
            return

        total_width = self.get_total_timeline_width()

        sel_start_x = self.selection_start * total_width
        sel_end_x = self.selection_end * total_width
        handle_width = 6

        if abs(pos_x - sel_start_x) <= handle_width * 2:
            self.dragging_start = True
            self.drag_start_pos = pos_x
            self.setCursor(Qt.SizeHorCursor)
        elif abs(pos_x - sel_end_x) <= handle_width * 2:
            self.dragging_end = True
            self.drag_start_pos = pos_x
            self.setCursor(Qt.SizeHorCursor)
        elif sel_start_x <= pos_x <= sel_end_x:
            self.dragging_body = True
            self.drag_start_pos = pos_x
            self.initial_selection_start = self.selection_start
            self.initial_selection_end = self.selection_end
            self.setCursor(Qt.ClosedHandCursor)
        else:
            # 타임라인 클릭 시 재생 위치 변경
            if self.duration > 0 and total_width > 0:
                vis_start, vis_end, vis_dur = self.get_visible_time_range()
                if vis_dur > 0:
                    click_ratio = pos_x / total_width if total_width > 0 else 0
                    click_time_ms = int(vis_start + click_ratio * vis_dur)
                    click_time_ms = max(0, min(self.duration, click_time_ms))
                    self.positionChanged.emit(click_time_ms)

    def mouseMoveEvent(self, event):
        """마우스 이동"""
        pos_x = event.position().x()
        pos_y = event.position().y()
        total_width = self.get_total_timeline_width()
        timecode_height = 24

        # 재생 헤드 드래그 처리
        if self.dragging_playhead and self.drag_start_pos is not None:
            if self.duration <= 0:
                return

            width = self.width()
            if width <= 0:
                return

            # 가시 영역 기준으로 마우스 위치를 시간(ms)으로 변환
            vis_start_ms, vis_end_ms, vis_dur_ms = self.get_visible_time_range()
            if vis_dur_ms > 0:
                click_ratio = pos_x / width if width > 0 else 0
                new_position_ms = int(vis_start_ms + click_ratio * vis_dur_ms)
                new_position_ms = max(0, min(self.duration, new_position_ms))
            else:
                px_per_ms = width / self.duration
                new_position_ms = int(pos_x / px_per_ms)
                new_position_ms = max(0, min(self.duration, new_position_ms))

            if new_position_ms != self.current_position:
                self.positionChanged.emit(new_position_ms)
                # 재생 헤드 드래그 시 선택 범위도 업데이트 (작은 범위)
                if vis_dur_ms > 0:
                    click_ratio = (new_position_ms - vis_start_ms) / vis_dur_ms if vis_dur_ms > 0 else 0
                    click_ratio = max(0.0, min(1.0, click_ratio))
                    small_range_ratio = 0.05  # 가시 영역의 5%
                    new_start = max(0.0, click_ratio - small_range_ratio / 2)
                    new_end = min(1.0, click_ratio + small_range_ratio / 2)
                    self.set_selection(new_start, new_end)

            return

        # 줌 섹션 박스 드래그 처리
        if self.dragging_zoom_box and self.drag_start_pos is not None:
            if self.duration <= 0 or self.zoom_level <= 1.0:
                return

            px_per_ms = total_width / self.duration if self.duration > 0 else 0
            visible_duration = self.duration / max(self.zoom_level, 1.0)  # 최소 줌 1.0 보장
            max_offset = max(0, self.duration - visible_duration)

            target_time_ms = pos_x / px_per_ms if px_per_ms > 0 else 0
            target_time_ms = max(0, min(self.duration, target_time_ms))

            target_start = target_time_ms - visible_duration / 2
            target_start = max(0, min(max_offset, target_start))

            new_offset = target_start / max_offset if max_offset > 0 else 0
            new_offset = max(0.0, min(1.0, new_offset))

            if abs(new_offset - self.scroll_offset) > 0.001:
                self.scroll_offset = new_offset
                self.update()
                QTimer.singleShot(100, self.check_and_request_frames)
                # 선택 범위 재계산 및 시그널 emit
                self._update_selection_after_view_change()
            return

        # 가시 영역 기준으로 ratio 계산
        vis_start_ms, vis_end_ms, vis_dur_ms = self.get_visible_time_range()
        if vis_dur_ms > 0 and total_width > 0:
            # 마우스 위치를 가시 영역 내의 시간으로 변환
            click_time_ms = vis_start_ms + (pos_x / total_width) * vis_dur_ms
            click_time_ms = max(vis_start_ms, min(vis_end_ms, click_time_ms))
            # 가시 영역 내의 비율로 변환 (0~1)
            ratio = (click_time_ms - vis_start_ms) / vis_dur_ms if vis_dur_ms > 0 else 0
        else:
            ratio = pos_x / total_width if total_width > 0 else 0

        if self.dragging_start:
            self.set_selection(ratio, self.selection_end)
        elif self.dragging_end:
            self.set_selection(self.selection_start, ratio)
        elif self.dragging_body and self.drag_start_pos is not None:
            # 드래그 시작 위치도 가시 영역 기준으로 변환
            if vis_dur_ms > 0 and total_width > 0:
                drag_start_time_ms = vis_start_ms + (self.drag_start_pos / total_width) * vis_dur_ms
                drag_start_time_ms = max(vis_start_ms, min(vis_end_ms, drag_start_time_ms))
                drag_start_ratio = (drag_start_time_ms - vis_start_ms) / vis_dur_ms if vis_dur_ms > 0 else 0
                
                current_time_ms = vis_start_ms + (pos_x / total_width) * vis_dur_ms
                current_time_ms = max(vis_start_ms, min(vis_end_ms, current_time_ms))
                current_ratio = (current_time_ms - vis_start_ms) / vis_dur_ms if vis_dur_ms > 0 else 0
                
                delta = current_ratio - drag_start_ratio
            else:
                delta = (pos_x - self.drag_start_pos) / total_width if total_width > 0 else 0
            
            new_start = self.initial_selection_start + delta
            new_end = self.initial_selection_end + delta

            if new_start < 0:
                new_end -= new_start
                new_start = 0
            elif new_end > 1:
                new_start -= (new_end - 1)
                new_end = 1

            self.set_selection(new_start, new_end)
        else:
            hit_tolerance = 8

            # 재생 헤드 위에 마우스가 있는지 확인
            if self.duration > 0:
                red_x, blue_x = self.get_playhead_positions()

                if red_x is not None and pos_y < timecode_height:
                    if abs(pos_x - red_x) <= hit_tolerance:
                        self.setCursor(Qt.SizeHorCursor)
                        return

                if blue_x is not None and pos_y >= timecode_height:
                    if abs(pos_x - blue_x) <= hit_tolerance:
                        self.setCursor(Qt.SizeHorCursor)
                        return

            # 줌 섹션 박스 위에 마우스가 있는지 확인
            if pos_y < timecode_height and self.zoom_level > 1.0:
                zoom_box = self.get_zoom_box_rect()
                if zoom_box:
                    box_x, box_y, box_w, box_h = zoom_box
                    if box_x <= pos_x <= box_x + box_w and box_y <= pos_y <= box_y + box_h:
                        self.setCursor(Qt.SizeHorCursor)
                        return

            if pos_y < timecode_height:
                self.setCursor(Qt.ArrowCursor)
                return

            sel_start_x = self.selection_start * total_width
            sel_end_x = self.selection_end * total_width
            handle_width = 6

            if (
                abs(pos_x - sel_start_x) <= handle_width * 2
                or abs(pos_x - sel_end_x) <= handle_width * 2
            ):
                self.setCursor(Qt.SizeHorCursor)
            elif sel_start_x <= pos_x <= sel_end_x:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        """마우스 놓음"""
        if event.button() != Qt.LeftButton:
            return

        was_dragging_playhead = self.dragging_playhead

        self.dragging_start = False
        self.dragging_end = False
        self.dragging_body = False
        self.dragging_zoom_box = False
        self.dragging_playhead = False
        self.drag_start_pos = None
        self.setCursor(Qt.ArrowCursor)

        if was_dragging_playhead:
            self.playheadDragEnded.emit()

    def resizeEvent(self, event):
        """위젯 크기 변경 시 필요한 프레임 체크"""
        super().resizeEvent(event)
        if self.duration > 0:
            QTimer.singleShot(100, self.check_and_request_frames)


class VideoTimelineCard(QFrame):
    """프레임 타임라인을 포함하는 카드"""

    selectionChanged = Signal(int, int)
    needMoreFrames = Signal(list)
    positionChanged = Signal(int)
    playheadDragStarted = Signal()
    playheadDragEnded = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoTimelineCard")
        self.setStyleSheet(
            """
            QFrame#VideoTimelineCard {
                background: rgba(17,17,27,0.9);
                border: 1px solid rgba(75,85,99,0.2);
                border-radius: 6px;
                margin: 4px;
            }
            QLabel#TimelineHeader {
                font-size: 11px;
                font-weight: 700;
                color: #9CA3AF;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }
        """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(6)

        header = QLabel("FRAME TIMELINE")
        header.setObjectName("TimelineHeader")
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(header)

        # 프레임 추출 작업명 라벨
        self.extraction_progress_label = QLabel("")
        self.extraction_progress_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
                padding: 4px 0px;
            }
        """)
        self.extraction_progress_label.hide()  # 초기에는 숨김
        root.addWidget(self.extraction_progress_label)

        # 프레임 추출 진행바
        self.extraction_progress_bar = QProgressBar()
        self.extraction_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(75,85,99,0.3);
                border-radius: 6px;
                text-align: center;
                background: rgba(17,17,27,0.9);
                color: #F9FAFB;
                font-size: 11px;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #1D4ED8);
                border-radius: 5px;
            }
        """)
        self.extraction_progress_bar.hide()  # 초기에는 숨김
        self.extraction_progress_bar.setRange(0, 100)
        self.extraction_progress_bar.setValue(0)
        root.addWidget(self.extraction_progress_bar)

        self.timeline = FrameTimeline()
        root.addWidget(self.timeline)

        # 시그널 재전파
        self.timeline.selectionChanged.connect(self.selectionChanged)
        self.timeline.needMoreFrames.connect(self.needMoreFrames)
        self.timeline.positionChanged.connect(self.positionChanged)
        self.timeline.playheadDragStarted.connect(self.playheadDragStarted)
        self.timeline.playheadDragEnded.connect(self.playheadDragEnded)

    # 타임라인 메서드 위임
    def clear_cache(self):
        self.timeline.clear_cache()

    def set_duration(self, duration, current_position_ms=0):
        self.timeline.set_duration(duration, current_position_ms)

    def set_current_position(self, position_ms):
        self.timeline.set_current_position(position_ms)

    def add_frame_to_cache(self, time_ms, pixmap):
        self.timeline.add_frame_to_cache(time_ms, pixmap)

    def check_and_request_frames(self):
        self.timeline.check_and_request_frames()

    def set_selection(self, start_ratio, end_ratio):
        self.timeline.set_selection(start_ratio, end_ratio)

    def get_visible_time_range(self):
        return self.timeline.get_visible_time_range()
    
    def show_extraction_progress(self, task_name=""):
        """프레임 추출 진행바 표시"""
        if self.extraction_progress_label:
            self.extraction_progress_label.setText(task_name)
            self.extraction_progress_label.show()
        if self.extraction_progress_bar:
            self.extraction_progress_bar.setValue(0)
            self.extraction_progress_bar.show()
    
    def update_extraction_progress(self, percent, task_name=None):
        """프레임 추출 진행률 업데이트"""
        if task_name and self.extraction_progress_label:
            self.extraction_progress_label.setText(task_name)
            self.extraction_progress_label.show()
        if self.extraction_progress_bar:
            self.extraction_progress_bar.setValue(int(percent))
            self.extraction_progress_bar.show()
    
    def hide_extraction_progress(self):
        """프레임 추출 진행바 숨김"""
        if self.extraction_progress_label:
            self.extraction_progress_label.hide()
            self.extraction_progress_label.setText("")
        if self.extraction_progress_bar:
            self.extraction_progress_bar.hide()
            self.extraction_progress_bar.setValue(0)



