# -*- coding: utf-8 -*-
"""
Center Panel Overlay Plugin — Glass Layer + Stack (front-on-click)
- center_splitter 위에 투명 레이어를 덮고, 내부 QStackedLayout으로 오버레이 카드 전환
- 기존 중앙 패널 3개(이미지 프리뷰/태그 트리/태깅)는 가시성만 숨김/복구 (setSizes() 사용 안 함)
- 어떤 카드 버튼을 누르든 해당 타입을 스택 최상단으로 올려 즉시 맨 앞에 표시
"""

from PySide6.QtCore import Qt, QObject, QEvent, QRect
from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedLayout, QFrame, QSizePolicy


class _ResizeSync(QObject):
    """부모(center_splitter)의 변화에 맞춰 오버레이 레이어를 동기화"""
    def __init__(self, parent_widget: QWidget, layer: QWidget):
        super().__init__(parent_widget)
        self._parent = parent_widget
        self._layer = layer

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.LayoutRequest):
            if self._parent and self._layer:
                self._layer.setGeometry(QRect(0, 0, self._parent.width(), self._parent.height()))
        return False


class CenterPanelOverlayPlugin:
    """
    퍼블릭 API (기존과 동일):
      - show_overlay_card(overlay_card: QWidget, overlay_type: str)
      - hide_overlay_card(overlay_type: str)
    """

    # 내부 상태 키
    _K_LAYER   = "_overlay_layer"            # 투명 글래스 레이어
    _K_STACK   = "_overlay_stack"            # QStackedLayout (오버레이 전환)
    _K_REG     = "_overlay_registry"         # {overlay_type: QWidget}
    _K_ORDER   = "_overlay_order"            # [type, ...]  끝이 최상단(최근)
    _K_ACTIVE  = "_overlay_active_type"      # 현재 활성 타입
    _K_SYNC    = "_overlay_resize_sync"      # _ResizeSync

    _K_SAVED_VIS = "_overlay_saved_center_vis"  # 중앙 패널 자식 가시성 스냅샷
    _K_COLLAPSED = "_overlay_center_collapsed"  # 중앙 패널 숨김 여부

    _K_GUARD   = "_overlay_guard"               # 재진입 가드

    def __init__(self, app_instance):
        self.app = app_instance

    # ---------- 내부 준비 ----------

    def _ensure_layer(self) -> bool:
        if not hasattr(self.app, "center_splitter"):
            return False

        if not hasattr(self.app, self._K_LAYER) or getattr(self.app, self._K_LAYER) is None:
            parent = self.app.center_splitter

            layer = QWidget(parent)
            layer.setObjectName("OverlayGlassLayer")
            layer.setAttribute(Qt.WA_StyledBackground, True)
            layer.setAttribute(Qt.WA_TranslucentBackground, True)
            layer.setAutoFillBackground(False)
            layer.setStyleSheet("QWidget#OverlayGlassLayer { background: transparent; }")
            layer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layer.setGeometry(parent.rect())
            layer.hide()

            sync = _ResizeSync(parent, layer)
            parent.installEventFilter(sync)

            root = QVBoxLayout(layer)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            host = QFrame(layer)
            host.setObjectName("OverlayHost")
            host.setStyleSheet("QFrame#OverlayHost { background: transparent; }")
            host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            stack = QStackedLayout(host)
            stack.setContentsMargins(0, 0, 0, 0)
            stack.setSpacing(0)

            root.addWidget(host)

            setattr(self.app, self._K_LAYER, layer)
            setattr(self.app, self._K_STACK, stack)
            setattr(self.app, self._K_REG, {})
            setattr(self.app, self._K_ORDER, [])
            setattr(self.app, self._K_ACTIVE, None)
            setattr(self.app, self._K_SYNC, sync)
            setattr(self.app, self._K_SAVED_VIS, None)
            setattr(self.app, self._K_COLLAPSED, False)
            setattr(self.app, self._K_GUARD, False)

        return True

    def _is_active(self) -> bool:
        return getattr(self.app, self._K_ACTIVE, None) is not None

    # ---------- 중앙 패널 숨김/복구 ----------

    def _collapse_center_children(self):
        if getattr(self.app, self._K_COLLAPSED, False):
            return
        splitter = getattr(self.app, "center_splitter", None)
        if splitter is None:
            return
        saved = []
        for i in range(splitter.count()):
            w = splitter.widget(i)
            saved.append(w.isVisible())
            w.setVisible(False)
        setattr(self.app, self._K_SAVED_VIS, saved)
        setattr(self.app, self._K_COLLAPSED, True)

    def _restore_center_children(self):
        if not getattr(self.app, self._K_COLLAPSED, False):
            return
        splitter = getattr(self.app, "center_splitter", None)
        if splitter is None:
            return
        saved = getattr(self.app, self._K_SAVED_VIS, None)
        if isinstance(saved, list):
            for i in range(min(len(saved), splitter.count())):
                splitter.widget(i).setVisible(saved[i])
        setattr(self.app, self._K_SAVED_VIS, None)
        setattr(self.app, self._K_COLLAPSED, False)

    # ---------- 퍼블릭 API ----------

    def show_overlay_card(self, overlay_card: QWidget, overlay_type: str):
        if not self._ensure_layer():
            return
        if getattr(self.app, self._K_GUARD, False):
            return
        setattr(self.app, self._K_GUARD, True)

        try:
            layer  = getattr(self.app, self._K_LAYER)
            stack  = getattr(self.app, self._K_STACK)
            reg    = getattr(self.app, self._K_REG)
            order  = getattr(self.app, self._K_ORDER)

            # 등록(최초 1회). 동일 타입에 새 위젯이 들어오면 교체.
            if overlay_type not in reg:
                reg[overlay_type] = overlay_card
                overlay_card.setParent(layer)
                overlay_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                if stack.indexOf(overlay_card) == -1:
                    stack.addWidget(overlay_card)
            else:
                if reg[overlay_type] is not overlay_card:
                    # 기존 위젯 교체 (안정성)
                    old = reg[overlay_type]
                    old.hide()
                    if stack.indexOf(old) != -1:
                        stack.removeWidget(old)
                        old.setParent(None)
                    reg[overlay_type] = overlay_card
                    overlay_card.setParent(layer)
                    overlay_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    stack.addWidget(overlay_card)

            # 최초 진입이면 중앙 패널 숨기고 레이어 표시
            if not self._is_active():
                self._collapse_center_children()
                layer.setGeometry(self.app.center_splitter.rect())
                layer.show()
                layer.raise_()

            # === 핵심: 클릭한 타입을 항상 최상단으로 ===
            if overlay_type in order:
                order.remove(overlay_type)
            order.append(overlay_type)

            stack.setCurrentWidget(reg[overlay_type])
            reg[overlay_type].show()
            reg[overlay_type].raise_()
            setattr(self.app, self._K_ACTIVE, overlay_type)

        finally:
            setattr(self.app, self._K_GUARD, False)

    def hide_overlay_card(self, overlay_type: str):
        if not hasattr(self.app, self._K_LAYER):
            return
        if getattr(self.app, self._K_GUARD, False):
            return
        setattr(self.app, self._K_GUARD, True)

        try:
            layer  = getattr(self.app, self._K_LAYER)
            stack  = getattr(self.app, self._K_STACK)
            reg    = getattr(self.app, self._K_REG)
            order  = getattr(self.app, self._K_ORDER)
            active = getattr(self.app, self._K_ACTIVE, None)

            if overlay_type not in reg:
                return

            # 스택 순서에서 제거 + 카드 숨김
            if overlay_type in order:
                order.remove(overlay_type)
            reg[overlay_type].hide()

            # 내가 최상단이 아니면 단순 종료
            if active != overlay_type:
                return

            # 남은 게 있으면 그걸로 전환
            if order:
                next_type = order[-1]
                stack.setCurrentWidget(reg[next_type])
                reg[next_type].show()
                reg[next_type].raise_()
                setattr(self.app, self._K_ACTIVE, next_type)
                return

            # 전부 닫힘 → 레이어 숨김 + 중앙 패널 복구
            setattr(self.app, self._K_ACTIVE, None)
            layer.hide()
            self._restore_center_children()

        finally:
            setattr(self.app, self._K_GUARD, False)
