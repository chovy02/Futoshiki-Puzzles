"""Theme - colors, fonts, layout constants and easing helpers."""
import pygame

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
FPS = 60

BG_PRIMARY = (15, 18, 28)
BG_SECONDARY = (24, 28, 42)
BG_TERTIARY = (34, 40, 58)
BG_ELEVATED = (44, 52, 74)

BORDER = (55, 65, 90)
BORDER_HOVER = (95, 110, 145)
BORDER_BRIGHT = (130, 150, 195)

TEXT_PRIMARY = (240, 244, 252)
TEXT_SECONDARY = (160, 170, 195)
TEXT_TERTIARY = (110, 120, 145)
TEXT_DISABLED = (75, 82, 105)

ACCENT = (94, 234, 212)
ACCENT_HOVER = (153, 246, 228)
ACCENT_DIM = (45, 130, 120)
ACCENT_DARK = (15, 60, 55)

EASY = (110, 231, 183)
MEDIUM = (252, 211, 77)
HARD = (251, 146, 60)
EXTREME = (248, 113, 113)

CELL_GIVEN_BG = (30, 70, 60)
CELL_GIVEN_BORDER = (60, 130, 110)
CELL_GIVEN_TEXT = (165, 245, 215)

CELL_SOLVED_BG = (28, 50, 85)
CELL_SOLVED_BORDER = (60, 110, 175)
CELL_SOLVED_TEXT = (175, 215, 255)

CELL_CURRENT_BG = (90, 65, 20)
CELL_CURRENT_BORDER = (250, 180, 50)
CELL_CURRENT_TEXT = (255, 220, 130)

CELL_EMPTY_BG = (28, 32, 48)
CELL_EMPTY_BORDER = (60, 70, 95)
CELL_EMPTY_TEXT = (140, 150, 175)

SIGN_COLOR = (255, 145, 90)

SUCCESS = (110, 231, 183)
ERROR = (248, 113, 113)
INFO = (94, 234, 212)
WARNING = (252, 211, 77)


_fonts_cache = {}


def get_font(size, bold=False):
    key = (size, bold)
    if key in _fonts_cache:
        return _fonts_cache[key]
    try:
        font = pygame.font.SysFont("segoeui,helveticaneue,arial,sans-serif", size, bold=bold)
    except Exception:
        font = pygame.font.Font(None, size)
    _fonts_cache[key] = font
    return font


def get_mono(size, bold=False):
    key = ("mono", size, bold)
    if key in _fonts_cache:
        return _fonts_cache[key]
    try:
        font = pygame.font.SysFont("consolas,menlo,monaco,monospace", size, bold=bold)
    except Exception:
        font = pygame.font.Font(None, size)
    _fonts_cache[key] = font
    return font


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t):
    t = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2