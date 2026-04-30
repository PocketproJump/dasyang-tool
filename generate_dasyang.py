#!/usr/bin/env python3
"""
打樣稿生成器
使用方式：python3 generate_dasyang.py 設定檔.json
"""

from PIL import Image, ImageDraw, ImageFont
import json, sys, os, re

# ── 字體路徑 ──────────────────────────────────────────────────────────
FONT_CJK  = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
FONT_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_LATIN_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

_font_cache = {}

def get_font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(
                FONT_LATIN_BOLD if bold else FONT_LATIN, size)
        except:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

def get_cjk_font(size):
    key = ("cjk", size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(FONT_CJK, size)
        except:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

# ── 混合字體文字渲染（中英文自動切換字體）─────────────────────────────
def is_cjk(ch):
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or   # CJK Unified
            0x3400 <= cp <= 0x4DBF or   # CJK Extension A
            0xF900 <= cp <= 0xFAFF or   # CJK Compatibility
            0x3000 <= cp <= 0x303F or   # CJK Symbols
            0xFF00 <= cp <= 0xFFEF or   # Fullwidth
            0x2E80 <= cp <= 0x2EFF)     # CJK Radicals

def text_width(text, size, bold=False):
    """計算混合文字寬度"""
    total = 0
    for ch in text:
        if is_cjk(ch):
            f = get_cjk_font(size)
        else:
            f = get_font(size, bold)
        bb = f.getbbox(ch)
        total += bb[2] - bb[0]
    return total

def draw_mixed(draw, pos, text, size, fill, bold=False, anchor_center=False):
    """在畫布上渲染中英混合文字"""
    if anchor_center:
        w = text_width(text, size, bold)
        x = pos[0] - w // 2
    else:
        x = pos[0]
    y = pos[1]

    for ch in text:
        if is_cjk(ch):
            f = get_cjk_font(size)
        else:
            f = get_font(size, bold)
        draw.text((x, y), ch, fill=fill, font=f)
        bb = f.getbbox(ch)
        x += bb[2] - bb[0]

# ── 圖片載入 ──────────────────────────────────────────────────────────
def load_img(path, size, label=""):
    """載入圖片並縮放至指定大小，找不到則顯示灰色佔位符"""
    if path and os.path.exists(path):
        img = Image.open(path).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
        bg = Image.new("RGBA", size, (245, 245, 245, 255))
        x = (size[0] - img.width) // 2
        y = (size[1] - img.height) // 2
        bg.paste(img, (x, y), img)
        return bg.convert("RGB")
    else:
        bg = Image.new("RGB", size, (225, 225, 225))
        d = ImageDraw.Draw(bg)
        draw_mixed(d, (size[0]//2, size[1]//2), label or "（無圖）",
                   12, (140, 140, 140), anchor_center=True)
        return bg

# ── 顏色轉換 ──────────────────────────────────────────────────────────
def hex_to_rgb(hex_str, fallback=(180, 180, 180)):
    try:
        h = hex_str.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except:
        return fallback

# ══════════════════════════════════════════════════════════════════════
# 主要生成函式
# ══════════════════════════════════════════════════════════════════════
def generate(cfg):
    W, H   = 1700, 510
    BAR_H  = 58
    MAIN_H = H - BAR_H
    SW     = W // 5
    PAD    = 14
    HDR_H  = 36

    C_BLUE  = (0, 102, 187)
    C_RED   = (210, 35, 45)
    C_DARK  = (30,  30,  30)
    C_GRAY  = (100, 100, 100)
    C_DIV   = (210, 210, 210)

    FS_HEAD  = 21
    FS_BODY  = 16
    FS_SMALL = 13

    canvas = Image.new("RGB", (W, H), "white")
    draw   = ImageDraw.Draw(canvas)

    # ── 底部紅色橫條 ────────────────────────────────────────────────
    draw.rectangle([0, MAIN_H, W, H], fill=C_RED)
    bar_text = f"打樣：{cfg.get('sample_requirement', '包包樣x2')}"
    draw_mixed(draw, (W//2, MAIN_H + BAR_H//2 - 13),
               bar_text, 26, "white", bold=True, anchor_center=True)

    # ── 欄位分隔線 ──────────────────────────────────────────────────
    for i in range(1, 5):
        draw.line([i*SW, 0, i*SW, MAIN_H], fill=C_DIV, width=2)

    # ════════════════════════════════════════════════════════════════
    # 欄 1：袋形示意
    # ════════════════════════════════════════════════════════════════
    X = 0
    draw_mixed(draw, (X+PAD, 8), "袋形示意：", FS_HEAD, C_BLUE, bold=True)

    bag_h   = MAIN_H - HDR_H - 65
    bag_img = load_img(cfg.get("bag_image"), (SW-2*PAD, bag_h), "袋形圖片")
    canvas.paste(bag_img, (X+PAD, HDR_H))

    note = cfg.get("fold_note", "")
    if note:
        draw_mixed(draw, (X+PAD, HDR_H+bag_h+5), note, FS_SMALL, C_GRAY)

    y_mat = MAIN_H - 52
    for line in [f"材質：{cfg.get('material','')}", f"印刷：{cfg.get('print_method','')}"]:
        draw_mixed(draw, (X+PAD, y_mat), line, FS_BODY, C_DARK)
        y_mat += 24

    # ════════════════════════════════════════════════════════════════
    # 欄 2：印刷裁片
    # ════════════════════════════════════════════════════════════════
    X = SW
    draw_mixed(draw, (X+PAD, 8), "印刷裁片：", FS_HEAD, C_BLUE, bold=True)
    draw_mixed(draw, (X+178, 10), "─── 刀模線", FS_SMALL, C_GRAY)
    draw_mixed(draw, (X+283, 10), "··· 車線",   FS_SMALL, C_GRAY)

    draw_mixed(draw, (X+PAD, HDR_H+2), "定位印：", FS_BODY, C_DARK)

    thumb_w = (SW - 3*PAD) // 2
    thumb_h = 110
    y_thumb = HDR_H + 24
    canvas.paste(load_img(cfg.get("front_open_image"), (thumb_w, thumb_h), "展開前幅"),
                 (X+PAD, y_thumb))
    canvas.paste(load_img(cfg.get("front_fold_image"), (thumb_w, thumb_h), "收折前幅"),
                 (X+PAD*2+thumb_w, y_thumb))
    draw_mixed(draw, (X+PAD+thumb_w//2, y_thumb-14), "展開前幅：", FS_SMALL, C_GRAY, anchor_center=True)
    draw_mixed(draw, (X+PAD*2+thumb_w+thumb_w//2, y_thumb-14), "收折前幅：", FS_SMALL, C_GRAY, anchor_center=True)

    y_wrap = y_thumb + thumb_h + 10
    draw_mixed(draw, (X+PAD, y_wrap),    "展開底部包圍＆拉桿背插、", FS_SMALL, C_DARK)
    draw_mixed(draw, (X+PAD, y_wrap+18), "收折包圍：",              FS_SMALL, C_DARK)

    wrap_hex  = cfg.get("bottom_wrap_color_hex", "#A8263B")
    wrap_name = cfg.get("bottom_wrap_pantone",   "Pantone 187C")
    draw.rectangle([X+PAD, y_wrap+38, X+PAD+130, y_wrap+56], fill=hex_to_rgb(wrap_hex))
    draw_mixed(draw, (X+PAD+140, y_wrap+39), wrap_name, FS_SMALL, C_DARK)

    y_cut = y_wrap + 65
    cut_h = MAIN_H - y_cut - PAD
    if cut_h > 30:
        canvas.paste(load_img(cfg.get("cut_layout_image"), (SW-2*PAD, cut_h), "版型圖"),
                     (X+PAD, y_cut))

    # ════════════════════════════════════════════════════════════════
    # 欄 3：其餘 Pattern + Pantone
    # ════════════════════════════════════════════════════════════════
    X    = SW * 2
    pat_w = SW // 2 - PAD - 5

    draw_mixed(draw, (X+PAD, 8), "其餘Pattern:", FS_HEAD, C_BLUE, bold=True)
    canvas.paste(load_img(cfg.get("pattern_image"), (pat_w, 160), "Pattern"),
                 (X+PAD, HDR_H))

    draw_mixed(draw, (X+PAD, HDR_H+165), "內裏：", FS_BODY, C_BLUE, bold=True)
    canvas.paste(load_img(cfg.get("lining_image"), (pat_w, 90), "內裏"),
                 (X+PAD, HDR_H+190))
    if cfg.get("lining_note"):
        draw_mixed(draw, (X+PAD, HDR_H+287), f"*{cfg['lining_note']}", FS_SMALL, C_RED)

    # Pantone 色票欄
    draw_mixed(draw, (X+SW//2+5, 8), "Pantone", FS_HEAD, C_DARK, bold=True)
    py = HDR_H + 4
    for p in cfg.get("pantone_colors", [])[:7]:
        rgb = hex_to_rgb(p.get("hex","#888"), (140,140,140))
        draw.rectangle([X+SW//2+5, py, X+SW//2+30, py+18], fill=rgb, outline=(0,0,0))
        draw_mixed(draw, (X+SW//2+36, py+1), p.get("name",""), FS_SMALL, C_DARK)
        py += 30

    # ════════════════════════════════════════════════════════════════
    # 欄 4：輔料
    # ════════════════════════════════════════════════════════════════
    X  = SW * 3
    ay = HDR_H + 4
    draw_mixed(draw, (X+PAD, 8), "輔料：", FS_HEAD, C_BLUE, bold=True)

    for i, acc in enumerate(cfg.get("accessories", [])[:5], 1):
        draw_mixed(draw, (X+PAD, ay), f"{i}.{acc.get('name','')}", FS_BODY, C_DARK)
        ay += 22
        if acc.get("detail"):
            if acc.get("detail_hex"):
                rgb = hex_to_rgb(acc["detail_hex"])
                draw.rectangle([X+PAD+10, ay, X+PAD+42, ay+13], fill=rgb, outline=(0,0,0))
                draw_mixed(draw, (X+PAD+48, ay), acc["detail"], FS_SMALL, C_DARK)
            else:
                draw_mixed(draw, (X+PAD+10, ay), acc["detail"], FS_SMALL, C_GRAY)
            ay += 18
        if acc.get("image"):
            acc_img = load_img(acc["image"], (SW-2*PAD, 45), acc.get("name",""))
            canvas.paste(acc_img, (X+PAD, ay))
            ay += 50
        ay += 4

    # ════════════════════════════════════════════════════════════════
    # 欄 5：設計稿
    # ════════════════════════════════════════════════════════════════
    X = SW * 4
    draw_mixed(draw, (X+PAD, 8), "設計稿：", FS_HEAD, C_BLUE, bold=True)
    design_img = load_img(cfg.get("design_image"),
                          (SW-2*PAD, MAIN_H-HDR_H-PAD), "設計稿")
    canvas.paste(design_img, (X+PAD, HDR_H))

    return canvas


# ══════════════════════════════════════════════════════════════════════
# 執行
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python3 generate_dasyang.py 設定檔.json")
        sys.exit(1)

    cfg_path = sys.argv[1]
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    base_dir = os.path.dirname(os.path.abspath(cfg_path))

    def abs_path(p):
        if p and not os.path.isabs(p):
            return os.path.join(base_dir, p)
        return p

    for key in ["bag_image","front_open_image","front_fold_image",
                "cut_layout_image","pattern_image","lining_image","design_image"]:
        if cfg.get(key):
            cfg[key] = abs_path(cfg[key])
    for acc in cfg.get("accessories", []):
        if acc.get("image"):
            acc["image"] = abs_path(acc["image"])

    out_path = abs_path(cfg.get("output_path", "打樣稿_output.jpg"))
    canvas = generate(cfg)
    canvas.save(out_path, "JPEG", quality=95)
    print(f"✅ 打樣稿已生成：{out_path}")
