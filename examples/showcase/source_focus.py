"""Map full-page annotations into an original-image detail viewport."""
import math


def box_in_view(box, viewport):
    """Return the visible intersection in viewport coordinates, or None.

    Both inputs are (x, y, width, height) normalized to the original page.
    Cropping clips the display overlay only; it does not change source pixels.
    """
    for bounds in (box, viewport):
        if len(bounds) != 4 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in bounds):
            raise ValueError('Four finite normalized coordinates required.')
        x, y, width, height = bounds
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1.000001 or y + height > 1.000001:
            raise ValueError('Positive box inside the original page required.')
    x, y, width, height = box
    vx, vy, vw, vh = viewport
    left, top = max(x, vx), max(y, vy)
    right, bottom = min(x + width, vx + vw), min(y + height, vy + vh)
    if right <= left or bottom <= top:
        return None
    return ((left - vx) / vw, (top - vy) / vh, (right - left) / vw, (bottom - top) / vh)
