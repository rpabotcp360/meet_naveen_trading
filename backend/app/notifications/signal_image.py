"""Renders a BUY-signal notification as a PNG card matching the web app's
dark trading-terminal look, so Telegram alerts read as a premium at-a-glance
card instead of a wall of plain text."""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.timezone import to_ist

WIDTH = 900
PAD = 36

# Same palette as the app's globals.css tokens.
COLOR_BG = (5, 7, 13)
COLOR_SURFACE = (13, 17, 25)
COLOR_SURFACE_2 = (19, 24, 38)
COLOR_BORDER = (30, 36, 51)
COLOR_FOREGROUND = (233, 235, 241)
COLOR_MUTED = (139, 147, 167)
COLOR_MUTED_2 = (86, 95, 116)
COLOR_ACCENT = (99, 102, 241)
COLOR_ACCENT_SOFT = (99, 102, 241, 36)
COLOR_BUY = (34, 197, 94)
COLOR_BUY_SOFT = (34, 197, 94, 36)
COLOR_SELL = (244, 63, 94)
COLOR_SELL_SOFT = (244, 63, 94, 36)

# Prefer fonts that include ₹ (U+20B9), en-dash, and · on Windows and Ubuntu.
_FONT_CANDIDATES: dict[str, list[str]] = {
    "sans": [
        r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ],
    "sans_bold": [
        r"C:\Windows\Fonts\segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ],
    "mono": [
        r"C:\Windows\Fonts\consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    ],
    "mono_bold": [
        r"C:\Windows\Fonts\consolab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
    ],
}


@lru_cache(maxsize=32)
def _font(family: str, size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES.get(family, []):
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


F_SYMBOL = None
F_COMPANY = None
F_BADGE = None
F_META = None
F_LABEL = None
F_PRICE = None
F_SUB = None
F_FOOTER_LABEL = None
F_FOOTER_VALUE = None
F_BRAND = None


def _ensure_fonts() -> None:
    global F_SYMBOL, F_COMPANY, F_BADGE, F_META, F_LABEL
    global F_PRICE, F_SUB, F_FOOTER_LABEL, F_FOOTER_VALUE, F_BRAND
    if F_SYMBOL is not None:
        return
    F_SYMBOL = _font("sans_bold", 40)
    F_COMPANY = _font("sans", 22)
    F_BADGE = _font("sans_bold", 24)
    F_META = _font("sans", 18)
    F_LABEL = _font("sans_bold", 15)
    F_PRICE = _font("mono_bold", 23)
    F_SUB = _font("mono", 15)
    F_FOOTER_LABEL = _font("sans", 18)
    F_FOOTER_VALUE = _font("mono_bold", 20)
    F_BRAND = _font("sans", 16)


def _rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _blend(base_rgb, overlay_rgba):
    """Flatten a translucent overlay color onto an opaque base, since PIL's
    non-RGBA draw surface can't composite alpha directly."""
    r, g, b, a = overlay_rgba
    a = a / 255
    return tuple(int(base_rgb[i] * (1 - a) + overlay_rgba[i] * a) for i in range(3))


def _price_box(draw, xy, w, h, label, value, tone_rgb, tone_soft_rgba, sub_lines=None):
    x, y = xy
    fill = _blend(COLOR_SURFACE, tone_soft_rgba)
    _rounded_rect(draw, [x, y, x + w, y + h], 14, fill=fill, outline=tone_rgb, width=2)
    draw.text((x + 14, y + 12), label, font=F_LABEL, fill=tone_rgb)
    draw.text((x + 14, y + 38), value, font=F_PRICE, fill=tone_rgb)
    if sub_lines:
        for i, line in enumerate(sub_lines):
            draw.text((x + 14, y + 76 + i * 20), line, font=F_SUB, fill=tone_rgb)


def render_signal_card(signal) -> bytes:
    _ensure_fonts()
    height = 520
    img = Image.new("RGB", (WIDTH, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Outer card
    card_box = [16, 16, WIDTH - 16, height - 16]
    _rounded_rect(draw, card_box, 20, fill=COLOR_SURFACE, outline=COLOR_BORDER, width=2)
    draw.rectangle([16, 16, 22, height - 16], fill=COLOR_BUY)

    x = PAD + 12
    y = 36

    draw.text((x, y), signal.symbol, font=F_SYMBOL, fill=COLOR_FOREGROUND)
    if getattr(signal, "company_name", ""):
        draw.text((x, y + 50), signal.company_name, font=F_COMPANY, fill=COLOR_MUTED)

    # BUY badge, top-right
    badge_text = "BUY"
    badge_w, badge_h = 110, 46
    bx = WIDTH - PAD - badge_w
    by = 36
    _rounded_rect(draw, [bx, by, bx + badge_w, by + badge_h], 23, fill=_blend(COLOR_SURFACE, COLOR_BUY_SOFT))
    tw = draw.textlength(badge_text, font=F_BADGE)
    draw.text((bx + (badge_w - tw) / 2, by + 10), badge_text, font=F_BADGE, fill=COLOR_BUY)

    # Alert type + trigger time
    y2 = y + 92
    candle_start = to_ist(signal.candle_timestamp_utc)
    candle_end = to_ist(signal.generated_at_utc)
    is_realtime = getattr(signal, "is_realtime", True)
    alert_label = "Live Alert" if is_realtime else "Past Alert"
    alert_color = COLOR_BUY if is_realtime else COLOR_MUTED
    meta_text = (
        f"{alert_label}   \u00b7   {candle_start.strftime('%d %b %Y, %H:%M')}"
        f"\u2013{candle_end.strftime('%H:%M')} IST \u00b7 5m candle"
    )
    draw.text((x, y2), meta_text, font=F_META, fill=alert_color)

    # Price boxes: Entry, T1, T2, T3, Stop Loss
    sign = 1
    entry = signal.entry

    def pnl(level: float):
        pct = ((level - entry) / entry) * 100 * sign
        amount = (level - entry) * signal.quantity * sign if signal.quantity else None
        return amount, pct

    def fmt_money(amount):
        s = "+" if amount > 0 else "-" if amount < 0 else ""
        return f"{s}\u20b9{abs(amount):.2f}"

    def fmt_pct(pct):
        s = "+" if pct > 0 else ""
        return f"{s}{pct:.2f}%"

    boxes_y = y2 + 48
    box_h = 136
    gap = 10
    box_w = (WIDTH - 2 * x - 4 * gap) / 5

    entries = [
        ("ENTRY", entry, COLOR_ACCENT, COLOR_ACCENT_SOFT, None),
    ]
    for label, level in (("T1", signal.target_1), ("T2", signal.target_2), ("T3", signal.target_3)):
        amount, pct = pnl(level)
        sub_lines = [fmt_money(amount), f"({fmt_pct(pct)})"] if amount is not None else [fmt_pct(pct)]
        entries.append((label, level, COLOR_BUY, COLOR_BUY_SOFT, sub_lines))
    stop_amount, stop_pct = pnl(signal.stop_loss)
    stop_sub_lines = [fmt_money(stop_amount), f"({fmt_pct(stop_pct)})"] if stop_amount is not None else [fmt_pct(stop_pct)]
    entries.append(("STOP LOSS", signal.stop_loss, COLOR_SELL, COLOR_SELL_SOFT, stop_sub_lines))

    for i, (label, level, tone, tone_soft, sub_lines) in enumerate(entries):
        bx2 = x + i * (box_w + gap)
        _price_box(draw, (bx2, boxes_y), box_w, box_h, label, f"\u20b9{level:.2f}", tone, tone_soft, sub_lines)

    # Footer strip: quantity, invested, score, rvol
    footer_y = boxes_y + box_h + 34
    footer_items = [
        ("QTY", f"{signal.quantity} shares" if signal.quantity else "\u2014"),
        ("INVESTED", f"\u20b9{signal.capital_used:.0f}" if signal.capital_used else "\u2014"),
        ("SCORE", f"{signal.buy_score}/100"),
        ("RVOL", f"{signal.rvol:.2f}x"),
    ]
    fx = x
    for fl, fv in footer_items:
        draw.text((fx, footer_y), fl, font=F_FOOTER_LABEL, fill=COLOR_MUTED_2)
        draw.text((fx, footer_y + 26), fv, font=F_FOOTER_VALUE, fill=COLOR_FOREGROUND)
        fx += 210

    # Extra context line
    ctx_y = footer_y + 66
    ctx_text = f"HTF {signal.htf_direction}   \u00b7   {signal.universe_source}   \u00b7   Mode: {signal.mode.title()}"
    draw.text((x, ctx_y), ctx_text, font=F_META, fill=COLOR_MUTED)

    # Brand footer
    draw.text((x, height - 56), "NSE Intraday Scanner", font=F_BRAND, fill=COLOR_MUTED_2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
