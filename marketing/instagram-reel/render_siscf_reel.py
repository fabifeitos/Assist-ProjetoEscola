#!/usr/bin/env python3
"""Render a Conta Azul-style Instagram Reel (9:16, ~22s) for SISCF."""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DURATION = 22.0
TOTAL = int(DURATION * FPS)
OUT = Path("/tmp/siscf_video/frames")
ASSETS = Path("/tmp/siscf_video/assets")

# Brand — slightly deeper gold for better white-text contrast
GOLD = (184, 145, 28)  # #B8911C
GOLD_DEEP = (150, 115, 14)
GOLD_LIGHT = (245, 220, 130)
WHITE = (255, 255, 255)
OFF_WHITE = (245, 245, 242)
DARK = (28, 28, 28)
DARK2 = (40, 40, 40)
GRAY = (120, 120, 120)
SOFT = (230, 230, 228)
BLACK = (0, 0, 0)

FONT_REG = "/usr/share/fonts/truetype/macos/Inter-Regular.ttf"
FONT_MED = "/usr/share/fonts/truetype/macos/Inter-Medium.ttf"
FONT_SEMI = "/usr/share/fonts/truetype/macos/Inter-SemiBold.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/macos/Inter-Bold.ttf"
FONT_SCRIPT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # fallback; italic via BoldItalic if needed
FONT_ITALIC = "/usr/share/fonts/truetype/macos/Inter-BoldItalic.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def ease_out_cubic(t: float) -> float:
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    t = clamp01(t)
    return 3 * t * t - 2 * t * t * t


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = clamp01(t)
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def text_size(draw, text, fnt):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_text_shadow(draw, xy, text, fnt, fill, shadow=(0, 0, 0, 140), offset=3):
    x, y = xy
    # shadow as separate layer handled by caller when needed; simple offset:
    draw.text((x + offset, y + offset), text, font=fnt, fill=(0, 0, 0))
    draw.text((x, y), text, font=fnt, fill=fill)


def logo_mark(size=120):
    """Crop circular logo from brand asset."""
    src = Image.open(ASSETS / "01a1f02f-2c1c-7263-a74b-66d557446aae.jpg").convert("RGBA")
    s = min(src.size)
    left = (src.width - s) // 2
    top = (src.height - s) // 2
    crop = src.crop((left, top, left + s, top + s)).resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((2, 2, size - 3, size - 3), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(crop, (0, 0))
    out.putalpha(mask)
    return out


def logo_icon(size=160):
    """Only the triangular network icon in a gold circle (no wordmark)."""
    src = Image.open(ASSETS / "01a1f02f-2c1c-7263-a74b-66d557446aae.jpg").convert("RGBA")
    w, h = src.size
    crop = src.crop((int(w * 0.12), int(h * 0.34), int(w * 0.36), int(h * 0.66)))
    side = min(crop.size)
    crop = crop.crop(
        ((crop.width - side) // 2, (crop.height - side) // 2, (crop.width + side) // 2, (crop.height + side) // 2)
    )
    crop = crop.resize((size, size), Image.Resampling.LANCZOS)
    # place on white circle plate for clean CTA
    plate = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, size - 2, size - 2), fill=255)
    plate.paste(crop, (0, 0))
    plate.putalpha(mask)
    return plate


def draw_label(draw, xy, text, fnt, fill, shadow=True):
    x, y = xy
    if shadow:
        for dx, dy in ((2, 2), (1, 1)):
            draw.text((x + dx, y + dy), text, font=fnt, fill=(0, 0, 0, 90) if len(fill) == 4 else (0, 0, 0))
    draw.text((x, y), text, font=fnt, fill=fill)


def prepare_dashboard():
    img = Image.open(ASSETS / "01a1f02f-2c5f-73d2-a180-edc29f1df10c.jpg").convert("RGB")
    w, h = img.size
    # Crop screen content and cut Windows taskbar / desk
    crop = img.crop((int(w * 0.015), int(h * 0.02), int(w * 0.985), int(h * 0.78)))
    return crop


def prepare_login():
    img = Image.open(ASSETS / "01a1f02f-2c05-74e6-ae29-89ffe4c20fcf.jpg").convert("RGB")
    # Mobile screenshot - crop status bar lightly
    w, h = img.size
    return img.crop((0, int(h * 0.04), w, int(h * 0.92)))


def paste_center(base, overlay, y, scale=1.0, opacity=1.0):
    ow, oh = overlay.size
    nw, nh = int(ow * scale), int(oh * scale)
    ov = overlay.resize((nw, nh), Image.Resampling.LANCZOS).convert("RGBA")
    if opacity < 1:
        a = ov.split()[-1].point(lambda p: int(p * opacity))
        ov.putalpha(a)
    x = (W - nw) // 2
    base.alpha_composite(ov, (x, int(y)))


def make_chaos_card(title, subtitle, color, w=420, h=120):
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    rounded_rect(d, (0, 0, w - 1, h - 1), 18, fill=(255, 255, 255, 245))
    d.rectangle((0, 0, 14, h), fill=color + (255,))
    d.text((28, 28), title, font=font(FONT_BOLD, 28), fill=DARK)
    d.text((28, 68), subtitle, font=font(FONT_REG, 22), fill=GRAY)
    return card


def make_check_card(text, done=True, w=780, h=110):
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    bg = (255, 255, 255, 255) if done else (220, 220, 220, 200)
    rounded_rect(d, (0, 0, w - 1, h - 1), 22, fill=bg)
    if done:
        d.ellipse((28, 28, 82, 82), fill=GOLD)
        # checkmark
        d.line([(42, 55), (54, 68), (72, 42)], fill=WHITE, width=6)
        d.text((110, 34), text, font=font(FONT_SEMI, 36), fill=DARK)
    else:
        d.text((40, 34), text, font=font(FONT_MED, 34), fill=GRAY)
    return card


def draw_watermark(img, opacity=0.9):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    f = font(FONT_SEMI, 36)
    text = "SISCF"
    tw, th = text_size(d, text, f)
    d.text((W - tw - 48, 56), text, font=f, fill=(255, 255, 255, int(255 * opacity)))
    img.alpha_composite(overlay)


def scene_problem(t: float) -> Image.Image:
    """0-3s: chaos with floating cards on darkened UI."""
    base = Image.new("RGBA", (W, H), DARK + (255,))
    dash = prepare_dashboard().convert("RGBA")
    # Scale to cover
    scale = max(W / dash.width, H / dash.height) * 1.08
    nw, nh = int(dash.width * scale), int(dash.height * scale)
    dash = dash.resize((nw, nh), Image.Resampling.LANCZOS)
    # Ken burns slow pan
    ox = int((nw - W) * 0.3 + math.sin(t * 0.4) * 20)
    oy = int((nh - H) * 0.2)
    base.paste(dash, (-ox, -oy))
    # dark overlay
    veil = Image.new("RGBA", (W, H), (20, 16, 8, 150))
    base.alpha_composite(veil)
    # bottom gradient for text
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(H // 2, H):
        a = int(200 * ((y - H / 2) / (H / 2)))
        gd.line([(0, y), (W, y)], fill=(20, 16, 8, a))
    base.alpha_composite(grad)

    # floating chaos cards
    cards = [
        make_chaos_card("mensalidades_atrasadas.xlsx", "12 abas · erros", (180, 50, 50)),
        make_chaos_card("Carnê de cobrança", "Vence hoje · R$ 189,00", (201, 162, 39)),
        make_chaos_card("Cobrar cliente!!", "Post-it · urgente", (220, 160, 40)),
    ]
    positions = [
        (80, 280 + int(math.sin(t * 2.1) * 12)),
        (520, 420 + int(math.cos(t * 1.7) * 14)),
        (160, 620 + int(math.sin(t * 1.3 + 1) * 10)),
    ]
    pops = [clamp01((t - 0.08 * i) / 0.28) for i in range(3)]
    for card, (x, y), p in zip(cards, positions, pops):
        if p <= 0:
            continue
        e = ease_out_cubic(p)
        sc = 0.7 + 0.3 * e
        op = e
        cw, ch = card.size
        nw, nh = int(cw * sc), int(ch * sc)
        c = card.resize((nw, nh), Image.Resampling.LANCZOS)
        a = c.split()[-1].point(lambda px: int(px * op))
        c.putalpha(a)
        base.alpha_composite(c, (x, y))

    d = ImageDraw.Draw(base)
    # headline appears mid
    appear = ease_out_cubic(clamp01((t - 0.4) / 0.5))
    if appear > 0:
        f1 = font(FONT_BOLD, 64)
        f2 = font(FONT_BOLD, 64)
        line1 = "Planilhas, carnês"
        line2_a = "e cobranças "
        line2_b = "manuais?"
        # measure
        y0 = 1480
        tw1, _ = text_size(d, line1, f1)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.text(((W - tw1) // 2, y0), line1, font=f1, fill=WHITE)
        tw2a, _ = text_size(od, line2_a, f2)
        tw2b, _ = text_size(od, line2_b, f2)
        total = tw2a + tw2b
        x0 = (W - total) // 2
        od.text((x0, y0 + 78), line2_a, font=f2, fill=WHITE)
        od.text((x0 + tw2a, y0 + 78), line2_b, font=f2, fill=GOLD_LIGHT)
        # fade in + slight rise
        shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dy = int((1 - appear) * 40)
        shifted.alpha_composite(overlay, (0, dy))
        a = shifted.split()[-1].point(lambda px: int(px * appear))
        shifted.putalpha(a)
        base.alpha_composite(shifted)

    draw_watermark(base)
    return base


def scene_stuck(t: float) -> Image.Image:
    """3-5s: Ainda preso à papelada?"""
    # dark warm bg with subtle login blur
    base = Image.new("RGBA", (W, H), (22, 18, 10, 255))
    login = prepare_login().convert("RGBA")
    scale = max(W / login.width, H / login.height)
    nw, nh = int(login.width * scale), int(login.height * scale)
    login = login.resize((nw, nh), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(18))
    login = ImageEnhance.Brightness(login).enhance(0.35)
    base.paste(login, ((W - nw) // 2, (H - nh) // 2))
    veil = Image.new("RGBA", (W, H), (20, 16, 8, 160))
    base.alpha_composite(veil)

    d = ImageDraw.Draw(base)
    appear = ease_out_cubic(clamp01(t / 0.45))
    f_script = font(FONT_ITALIC, 72)
    f_bold = font(FONT_BOLD, 72)
    a_word = "Ainda"
    rest = " preso à papelada?"
    # center block
    tw_a, _ = text_size(d, a_word, f_script)
    tw_r, _ = text_size(d, rest, f_bold)
    # two lines for readability
    line1 = a_word
    line2 = "preso à papelada?"
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    tw1, _ = text_size(od, line1, f_script)
    tw2, _ = text_size(od, line2, f_bold)
    od.text(((W - tw1) // 2, H // 2 - 90), line1, font=f_script, fill=GOLD_LIGHT)
    od.text(((W - tw2) // 2, H // 2 + 10), line2, font=f_bold, fill=WHITE)
    dy = int((1 - appear) * 30)
    shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shifted.alpha_composite(overlay, (0, dy))
    alpha = shifted.split()[-1].point(lambda px: int(px * appear))
    shifted.putalpha(alpha)
    base.alpha_composite(shifted)
    draw_watermark(base)
    return base


def scene_forget_manual(t: float) -> Image.Image:
    """5-7s: Esqueça a gestão ultrapassada. -> No SISCF, tudo integrado."""
    base = Image.new("RGBA", (W, H), GOLD + (255,))
    # slight vignette
    # phase: first half one text, second half other
    phase = t / 2.0  # 0..1 over 2s scene mapped externally
    d = ImageDraw.Draw(base)
    draw_watermark(base, 0.85)

    if t < 1.0:
        appear = ease_out_cubic(clamp01(t / 0.4))
        f1 = font(FONT_BOLD, 70)
        f2 = font(FONT_BOLD, 70)
        l1 = "Esqueça a"
        l2a = "gestão "
        l2b = "ultrapassada."
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        tw1, _ = text_size(od, l1, f1)
        draw_label(od, ((W - tw1) // 2, H // 2 - 90), l1, f1, WHITE)
        tw2a, _ = text_size(od, l2a, f2)
        tw2b, _ = text_size(od, l2b, f2)
        x0 = (W - (tw2a + tw2b)) // 2
        draw_label(od, (x0, H // 2 + 10), l2a, f2, WHITE)
        draw_label(od, (x0 + tw2a, H // 2 + 10), l2b, f2, DARK, shadow=False)
        dy = int((1 - appear) * 40)
        shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shifted.alpha_composite(overlay, (0, dy))
        a = shifted.split()[-1].point(lambda px: int(px * appear))
        shifted.putalpha(a)
        base.alpha_composite(shifted)
    else:
        local = t - 1.0
        appear = ease_out_cubic(clamp01(local / 0.35))
        f1 = font(FONT_BOLD, 64)
        f2 = font(FONT_BOLD, 64)
        l1 = "No SISCF,"
        l2a = "tudo "
        l2b = "integrado."
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        tw1, _ = text_size(od, l1, f1)
        draw_label(od, ((W - tw1) // 2, H // 2 - 90), l1, f1, WHITE)
        tw2a, _ = text_size(od, l2a, f2)
        tw2b, _ = text_size(od, l2b, f2)
        x0 = (W - (tw2a + tw2b)) // 2
        draw_label(od, (x0, H // 2 + 10), l2a, f2, WHITE)
        draw_label(od, (x0 + tw2a, H // 2 + 10), l2b, f2, DARK, shadow=False)
        dy = int((1 - appear) * 40)
        shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shifted.alpha_composite(overlay, (0, dy))
        a = shifted.split()[-1].point(lambda px: int(px * appear))
        shifted.putalpha(a)
        base.alpha_composite(shifted)
    return base


def scene_features(t: float) -> Image.Image:
    """7-12s: feature cards transforming."""
    base = Image.new("RGBA", (W, H), GOLD + (255,))
    draw_watermark(base, 0.85)

    # header text
    appear_h = ease_out_cubic(clamp01(t / 0.35))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    f1 = font(FONT_BOLD, 56)
    f2 = font(FONT_BOLD, 56)
    l1 = "No SISCF,"
    l2a = "tudo "
    l2b = "no automático"
    tw1, _ = text_size(od, l1, f1)
    draw_label(od, ((W - tw1) // 2, 320), l1, f1, WHITE)
    tw2a, _ = text_size(od, l2a, f2)
    tw2b, _ = text_size(od, l2b, f2)
    x0 = (W - (tw2a + tw2b)) // 2
    draw_label(od, (x0, 400), l2a, f2, WHITE)
    draw_label(od, (x0 + tw2a, 400), l2b, f2, DARK, shadow=False)
    a = overlay.split()[-1].point(lambda px: int(px * appear_h))
    overlay.putalpha(a)
    base.alpha_composite(overlay)

    # three feature pairs: old -> new
    pairs = [
        ("Carnê e cobrança manual", "Mensalidade automatizada"),
        ("Gaveta de documentos", "Contratos e OS digitais"),
        ("Contas no caderno", "Contas a receber em dia"),
    ]
    for i, (old, new) in enumerate(pairs):
        start = 0.5 + i * 1.35
        local = t - start
        if local < 0:
            continue
        # show old first, then morph to new
        show_new = local > 0.7
        card_t = clamp01(local / 0.35) if not show_new else clamp01((local - 0.7) / 0.35)
        e = ease_out_cubic(card_t)
        text = new if show_new else old
        card = make_check_card(text, done=show_new)
        y = 560 + i * 150
        # pop scale
        sc = 0.85 + 0.15 * e
        op = e
        cw, ch = card.size
        nw, nh = int(cw * sc), int(ch * sc)
        c = card.resize((nw, nh), Image.Resampling.LANCZOS)
        alpha = c.split()[-1].point(lambda px: int(px * op))
        c.putalpha(alpha)
        x = (W - nw) // 2
        base.alpha_composite(c, (x, y))
    return base


def scene_dashboard(t: float) -> Image.Image:
    """12-16s: dashboard showcase."""
    base = Image.new("RGBA", (W, H), (18, 16, 12, 255))
    # soft gold glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((80, 200, W - 80, 1500), fill=GOLD + (40,))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    base.alpha_composite(glow)

    dash = prepare_dashboard().convert("RGBA")
    # fit in a device frame
    target_w = 980
    scale = target_w / dash.width
    nw, nh = target_w, int(dash.height * scale)
    dash = dash.resize((nw, nh), Image.Resampling.LANCZOS)

    # laptop-like frame
    pad = 18
    frame_w, frame_h = nw + pad * 2, nh + pad * 2
    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(frame)
    rounded_rect(fd, (0, 0, frame_w - 1, frame_h - 1), 28, fill=(45, 45, 45, 255))
    rounded_rect(fd, (pad - 4, pad - 4, frame_w - pad + 3, frame_h - pad + 3), 18, fill=(255, 255, 255, 255))
    frame.alpha_composite(dash, (pad, pad))

    appear = ease_out_cubic(clamp01(t / 0.5))
    # Ken Burns slow zoom for readability on 9:16
    sc = (0.92 + 0.08 * appear) * (1.0 + 0.06 * ease_in_out(clamp01(t / 4.0)))
    y = 260 + int((1 - appear) * 60) - int(20 * ease_in_out(clamp01(t / 4.0)))
    paste_center(base, frame, y, scale=sc, opacity=appear)

    # caption
    cap_a = ease_out_cubic(clamp01((t - 0.4) / 0.4))
    if cap_a > 0:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        f1 = font(FONT_BOLD, 58)
        f2 = font(FONT_BOLD, 58)
        l1 = "O controle total"
        l2a = "da sua "
        l2b = "funerária."
        tw1, _ = text_size(od, l1, f1)
        od.text(((W - tw1) // 2, 1520), l1, font=f1, fill=WHITE)
        tw2a, _ = text_size(od, l2a, f2)
        tw2b, _ = text_size(od, l2b, f2)
        x0 = (W - (tw2a + tw2b)) // 2
        od.text((x0, 1605), l2a, font=f2, fill=WHITE)
        od.text((x0 + tw2a, 1605), l2b, font=f2, fill=GOLD_LIGHT)
        a = overlay.split()[-1].point(lambda px: int(px * cap_a))
        overlay.putalpha(a)
        base.alpha_composite(overlay)

    draw_watermark(base)
    return base


def scene_past(t: float) -> Image.Image:
    """16-18s: Desorganização? Ficou no passado."""
    base = Image.new("RGBA", (W, H), GOLD + (255,))
    draw_watermark(base, 0.85)
    appear = ease_out_cubic(clamp01(t / 0.4))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    f1 = font(FONT_BOLD, 64)
    f2 = font(FONT_BOLD, 64)
    l1 = "Desorganização?"
    l2a = "Ficou "
    l2b = "no passado."
    tw1, _ = text_size(od, l1, f1)
    draw_label(od, ((W - tw1) // 2, H // 2 - 90), l1, f1, WHITE)
    tw2a, _ = text_size(od, l2a, f2)
    tw2b, _ = text_size(od, l2b, f2)
    x0 = (W - (tw2a + tw2b)) // 2
    draw_label(od, (x0, H // 2 + 10), l2a, f2, WHITE)
    draw_label(od, (x0 + tw2a, H // 2 + 10), l2b, f2, DARK, shadow=False)
    dy = int((1 - appear) * 35)
    shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shifted.alpha_composite(overlay, (0, dy))
    a = shifted.split()[-1].point(lambda px: int(px * appear))
    shifted.putalpha(a)
    base.alpha_composite(shifted)
    return base


def scene_cta(t: float) -> Image.Image:
    """18-22s: logo + CTA button with cursor click."""
    base = Image.new("RGBA", (W, H), GOLD + (255,))
    appear = ease_out_cubic(clamp01(t / 0.45))

    # icon only (wordmark is rendered as clean type below)
    mark = logo_icon(240)
    paste_center(base, mark, 460 + int((1 - appear) * 40), opacity=appear)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    f_brand = font(FONT_BOLD, 96)
    f_sub = font(FONT_MED, 34)
    brand = "SISCF"
    sub = "Sistema de Controle Funerário"
    tw, _ = text_size(od, brand, f_brand)
    od.text(((W - tw) // 2, 760), brand, font=f_brand, fill=WHITE)
    sw, _ = text_size(od, sub, f_sub)
    od.text(((W - sw) // 2, 875), sub, font=f_sub, fill=DARK)

    tag = "Gestão com respeito pelo seu tempo."
    f_tag = font(FONT_REG, 32)
    twt, _ = text_size(od, tag, f_tag)
    od.text(((W - twt) // 2, 960), tag, font=f_tag, fill=(55, 45, 15))

    # CTA button — Conta Azul uses yellow on blue; we use dark on gold
    btn_w, btn_h = 640, 118
    btn_x = (W - btn_w) // 2
    btn_y = 1160
    # subtle press when cursor arrives
    press = 1.0
    if t > 2.05:
        press = 0.97
    bw, bh = int(btn_w * press), int(btn_h * press)
    bx = (W - bw) // 2
    by = btn_y + (btn_h - bh) // 2
    rounded_rect(od, (bx, by, bx + bw, by + bh), 30, fill=DARK)
    btn_text = "Agende uma demonstração"
    f_btn = font(FONT_SEMI, 36)
    btw, bth = text_size(od, btn_text, f_btn)
    od.text((bx + (bw - btw) // 2, by + (bh - bth) // 2 - 4), btn_text, font=f_btn, fill=WHITE)

    a = overlay.split()[-1].point(lambda px: int(px * appear))
    overlay.putalpha(a)
    base.alpha_composite(overlay)

    # cursor animation
    if t > 0.8:
        local = t - 0.8
        cx0, cy0 = W // 2 + 180, btn_y + 220
        cx1, cy1 = W // 2 + 40, btn_y + btn_h // 2 + 10
        p = ease_in_out(clamp01(local / 1.2))
        cx, cy = int(lerp(cx0, cx1, p)), int(lerp(cy0, cy1, p))
        cur = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(cur)
        pts = [
            (cx, cy),
            (cx, cy + 46),
            (cx + 14, cy + 36),
            (cx + 28, cy + 58),
            (cx + 36, cy + 54),
            (cx + 20, cy + 30),
            (cx + 34, cy + 28),
        ]
        cd.polygon(pts, fill=WHITE, outline=BLACK)
        if local > 1.25:
            rp = clamp01((local - 1.25) / 0.5)
            r = int(20 + 40 * rp)
            alpha = int(180 * (1 - rp))
            cd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, alpha), width=4)
        base.alpha_composite(cur)

    return base


def render_frame(i: int) -> Image.Image:
    t = i / FPS
    # timeline matching Conta Azul (~22s)
    if t < 3.0:
        frame = scene_problem(t)
    elif t < 5.0:
        frame = scene_stuck(t - 3.0)
    elif t < 7.0:
        frame = scene_forget_manual(t - 5.0)
    elif t < 12.0:
        frame = scene_features(t - 7.0)
    elif t < 16.0:
        frame = scene_dashboard(t - 12.0)
    elif t < 18.0:
        frame = scene_past(t - 16.0)
    else:
        frame = scene_cta(t - 18.0)
    return frame.convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Rendering {TOTAL} frames at {FPS}fps ({DURATION}s)...")
    for i in range(TOTAL):
        img = render_frame(i)
        img.save(OUT / f"frame_{i:05d}.png", optimize=False)
        if i % 30 == 0 or i == TOTAL - 1:
            print(f"  {i+1}/{TOTAL} ({(i+1)/TOTAL*100:.0f}%)")
    print("Done frames.")


if __name__ == "__main__":
    main()
