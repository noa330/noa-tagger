import math
from typing import List, Dict, Any


class ImageLoaderPlugin:
    """Unified pagination manager for image/video thumbnail grids."""

    def __init__(self, page_size: int = 50):
        self.page_size = max(1, page_size)
        self.media_items: Dict[str, List[Any]] = {
            "image": [],
            "video": [],
        }
        self.current_pages: Dict[str, int] = {
            "image": 0,
            "video": 0,
        }

    # ------------------------------------------------------------------
    # Data management
    # ------------------------------------------------------------------
    def set_items(self, media_type: str, items: List[Any], reset_page: bool = False):
        items = list(items) if items else []
        self.media_items[media_type] = items
        page_count = self.get_page_count(media_type)

        if reset_page or self.current_pages.get(media_type, 0) >= page_count:
            self.current_pages[media_type] = 0 if page_count > 0 else 0

    def append_items(self, media_type: str, items: List[Any]):
        if not items:
            return
        self.media_items.setdefault(media_type, []).extend(items)

    # ------------------------------------------------------------------
    # Pagination helpers
    # ------------------------------------------------------------------
    def get_page_count(self, media_type: str) -> int:
        total = len(self.media_items.get(media_type, []))
        if total == 0:
            return 0
        return math.ceil(total / self.page_size)

    def clamp_page(self, media_type: str, page_index: int) -> int:
        page_count = self.get_page_count(media_type)
        if page_count == 0:
            return 0
        return max(0, min(page_index, page_count - 1))

    def set_page(self, media_type: str, page_index: int):
        self.current_pages[media_type] = self.clamp_page(media_type, page_index)

    def reset_page(self, media_type: str = "image"):
        self.current_pages[media_type] = 0

    def get_current_page(self, media_type: str) -> int:
        return self.current_pages.get(media_type, 0)

    def get_page_items(self, media_type: str, page_index: int = None) -> List[Any]:
        items = self.media_items.get(media_type, [])
        if not items:
            return []

        if page_index is None:
            page_index = self.get_current_page(media_type)
        else:
            page_index = self.clamp_page(media_type, page_index)
            self.current_pages[media_type] = page_index

        start = page_index * self.page_size
        end = start + self.page_size
        return items[start:end]

    def next_page(self, media_type: str):
        page = self.get_current_page(media_type) + 1
        self.current_pages[media_type] = self.clamp_page(media_type, page)

    def prev_page(self, media_type: str):
        page = self.get_current_page(media_type) - 1
        self.current_pages[media_type] = self.clamp_page(media_type, page)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------
    def get_total_items(self, media_type: str) -> int:
        return len(self.media_items.get(media_type, []))

    def ensure_page_valid(self, media_type: str):
        self.current_pages[media_type] = self.clamp_page(media_type, self.get_current_page(media_type))
