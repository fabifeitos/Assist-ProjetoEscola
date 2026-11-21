#!/usr/bin/env python3
"""Gera um Reel Instagram (9:16) para o SISCF no estilo do loop de referência."""

from __future__ import annotations

import math
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FRAMES_DIR = ROOT / "frames"
OUT_MP4 = ROOT / "siscf_reel.mp4"
ARTIFACT_MP4 = Path("/opt/cursor/artifacts/siscf_reel.mp4")

W, H = 1080, 1920
FPS = 30
DURATION = 12.0
TOTAL = int(DURATION * FPS)

FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_DISPLAY = "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Bold.ttf"

BG = (0, 0, 0)
WHITE = (245, 245, 245)
SOFT = (210, 210, 210)
ACCENT = (86, 196, 214)  # ciano discreto, alinhado ao sistema Assist


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    return 3 * t * t - 2 * t * t * t


def clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill,
    spacing: int = 12,
) -> None:
    lines = text.split("\n")
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fnt)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + spacing * (len(lines) - 1)
    y = xy[1] - total_h / 2
    for i, line in enumerate(lines):
        x = xy[0] - widths[i] / 2
        draw.text((x, y), line, font=fnt, fill=fill)
        y += heights[i] + spacing


def logo_points(cx: float, cy: float, size: float, angle_deg: float):
    """Hexágono isométrico com recorte em seta (estilo do vídeo de referência)."""
    a = math.radians(angle_deg)
    cos_a, sin_a = math.cos(a), math.sin(a)

    def rot(x, y):
        return cx + x * cos_a - y * sin_a, cy + x * sin_a + y * cos_a

    # face isométrica (hexágono achatado)
    hx = size * 0.92
    hy = size * 0.78
    hex_local = [
        (0, -hy),
        (hx * 0.86, -hy * 0.48),
        (hx * 0.86, hy * 0.48),
        (0, hy),
        (-hx * 0.86, hy * 0.48),
        (-hx * 0.86, -hy * 0.48),
    ]
    hex_pts = [rot(x, y) for x, y in hex_local]

    # seta / avião de papel (marca geométrica)
    arrow_local = [
        (-size * 0.28, -size * 0.42),
        (size * 0.48, 0.0),
        (-size * 0.28, size * 0.42),
        (-size * 0.08, size * 0.08),
        (-size * 0.08, -size * 0.08),
    ]
    arrow_pts = [rot(x, y) for x, y in arrow_local]
    return hex_pts, arrow_pts


def draw_logo(img: Image.Image, cx: float, cy: float, size: float, angle: float, alpha: float = 1.0):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    hex_pts, arrow_pts = logo_points(cx, cy, size, angle)
    a = int(255 * alpha)
    d.polygon(hex_pts, fill=(245, 245, 245, a))
    d.polygon(arrow_pts, fill=(0, 0, 0, a))
    # leve sombra/blur para sensação 3D
    blurred = layer.filter(ImageFilter.GaussianBlur(radius=1.2))
    img.alpha_composite(blurred)
    img.alpha_composite(layer)


def scene_progress(t: float, start: float, end: float) -> float:
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    return (t - start) / (end - start)


def render_frame(i: int) -> Image.Image:
    t = i / FPS
    img = Image.new("RGBA", (W, H), (*BG, 255))
    draw = ImageDraw.Draw(img)

    # grade sutil no fundo
    for y in range(0, H, 96):
        draw.line([(0, y), (W, y)], fill=(18, 18, 18, 255), width=1)
    for x in range(0, W, 96):
        draw.line([(x, 0), (x, H)], fill=(18, 18, 18, 255), width=1)

    # Cenas sem sobreposição: fade-out completo antes do próximo fade-in
    # 0.0–2.0 logo | 2.15–4.3 hook | 4.45–6.9 marca | 7.05–9.5 benefícios | 9.65–12 CTA

    # --- Cena 1: logo girando ---
    if t < 2.05:
        p1 = scene_progress(t, 0.0, 1.85)
        spin = 360 * ease_in_out(p1)
        scale = 0.55 + 0.45 * ease_out_cubic(min(1.0, t / 0.45))
        alpha = 1.0 if t < 1.75 else 1.0 - scene_progress(t, 1.75, 2.05)
        draw_logo(img, W / 2, H * 0.46, 280 * scale, -18 + spin, alpha=alpha)

    # --- Cena 2: hook ---
    if 2.15 <= t < 4.35:
        p = ease_out_cubic(scene_progress(t, 2.15, 2.55))
        fade = 1.0 if t < 4.05 else 1.0 - scene_progress(t, 4.05, 4.35)
        y = H * 0.42 + (1 - p) * 40
        a = int(255 * fade * p)
        f = font(FONT_BOLD, 78)
        draw_centered_text(draw, (W / 2, y), "Sua escola\nainda no papel?", f, (245, 245, 245, a), spacing=18)
        f2 = font(FONT_REG, 36)
        draw_centered_text(
            draw,
            (W / 2, y + 190),
            "Planilhas, cadernos e retrabalho\ntodas as semanas.",
            f2,
            (180, 180, 180, a),
            spacing=10,
        )

    # --- Cena 3: marca SISCF ---
    if 4.45 <= t < 6.95:
        p = ease_out_cubic(scene_progress(t, 4.45, 4.95))
        fade = 1.0 if t < 6.65 else 1.0 - scene_progress(t, 6.65, 6.95)
        a = int(255 * fade * p)
        draw_logo(img, W / 2, H * 0.30, 170, -12 + 8 * math.sin(t * 2), alpha=fade * p)
        f = font(FONT_DISPLAY, 140)
        draw_centered_text(draw, (W / 2, H * 0.48), "SISCF", f, (245, 245, 245, a))
        f2 = font(FONT_BOLD, 42)
        draw_centered_text(
            draw,
            (W / 2, H * 0.58),
            "Sistema de gestão escolar",
            f2,
            (*ACCENT, a),
        )
        f3 = font(FONT_REG, 34)
        draw_centered_text(
            draw,
            (W / 2, H * 0.66),
            "Organize equipe, rotinas\ne cadastros em um só lugar.",
            f3,
            (190, 190, 190, a),
            spacing=10,
        )

    # --- Cena 4: benefícios ---
    if 7.05 <= t < 9.55:
        fade = 1.0 if t < 9.25 else 1.0 - scene_progress(t, 9.25, 9.55)
        items = [
            (7.10, "Cadastro de funcionários"),
            (7.70, "Acesso por usuário e senha"),
            (8.30, "Rotina mais rápida no dia a dia"),
        ]
        for idx, (start, label) in enumerate(items):
            if t < start:
                continue
            p = ease_out_cubic(scene_progress(t, start, start + 0.35))
            a = int(255 * fade * p)
            y = H * 0.34 + idx * 170
            x0 = 120 + (1 - p) * 60
            block = Image.new("RGBA", img.size, (0, 0, 0, 0))
            bd = ImageDraw.Draw(block)
            bd.rounded_rectangle(
                [x0, y, W - 120, y + 120],
                radius=18,
                fill=(22, 22, 22, a),
                outline=(*ACCENT, a),
                width=2,
            )
            img.alpha_composite(block)
            f = font(FONT_BOLD, 40)
            draw.text((x0 + 48, y + 36), label, font=f, fill=(245, 245, 245, a))

    # --- Cena 5: CTA ---
    if t >= 9.65:
        p = ease_out_cubic(scene_progress(t, 9.65, 10.15))
        a = int(255 * p)
        draw_logo(img, W / 2, H * 0.28, 150, -10, alpha=p)
        f = font(FONT_BOLD, 64)
        draw_centered_text(draw, (W / 2, H * 0.48), "Pronto para\nsair do caos?", f, (245, 245, 245, a), spacing=14)
        bw, bh = 520, 100
        bx, by = (W - bw) // 2, int(H * 0.62)
        btn = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(btn)
        bd.rounded_rectangle([bx, by, bx + bw, by + bh], radius=50, fill=(*ACCENT, a))
        img.alpha_composite(btn)
        f2 = font(FONT_BOLD, 40)
        draw_centered_text(draw, (W / 2, by + bh / 2 - 4), "Conheça o SISCF", f2, (0, 0, 0, a))
        f3 = font(FONT_REG, 30)
        draw_centered_text(draw, (W / 2, H * 0.74), "Salve este Reel · Chame no direct", f3, (170, 170, 170, a))
    # vinheta leve
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i_v in range(90):
        alpha = int(90 * (i_v / 90) ** 2)
        vd.rectangle([i_v, i_v, W - 1 - i_v, H - 1 - i_v], outline=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, vignette)

    return img.convert("RGB")


def main() -> None:
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    print(f"Gerando {TOTAL} frames em {FRAMES_DIR} ...")
    for i in range(TOTAL):
        frame = render_frame(i)
        frame.save(FRAMES_DIR / f"frame_{i:05d}.jpg", quality=92, optimize=True)
        if i % 30 == 0:
            print(f"  {i}/{TOTAL}")

    print("Codificando MP4 ...")
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(FRAMES_DIR / "frame_%05d.jpg"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        "-movflags",
        "+faststart",
        str(OUT_MP4),
    ]
    subprocess.run(cmd, check=True)
    shutil.copy2(OUT_MP4, ARTIFACT_MP4)
    print(f"OK: {OUT_MP4}")
    print(f"Cópia: {ARTIFACT_MP4}")


if __name__ == "__main__":
    main()
