#!/usr/bin/env python3
"""
打樣稿網頁工具
執行：python3 web_dasyang.py
瀏覽器開啟：http://localhost:5050
"""

import os, json, uuid, tempfile, io, base64
from flask import Flask, request, send_file, render_template_string, jsonify
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

# ─── 字體 ────────────────────────────────────────────────────────────
FONT_CJK   = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
FONT_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD  = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_fc = {}

def gf(size, bold=False):
    k = (size, bold)
    if k not in _fc:
        try: _fc[k] = ImageFont.truetype(FONT_BOLD if bold else FONT_LATIN, size)
        except: _fc[k] = ImageFont.load_default()
    return _fc[k]

def gcjk(size):
    k = ("c", size)
    if k not in _fc:
        try: _fc[k] = ImageFont.truetype(FONT_CJK, size)
        except: _fc[k] = ImageFont.load_default()
    return _fc[k]

def is_cjk(c):
    cp = ord(c)
    return (0x4E00<=cp<=0x9FFF or 0x3400<=cp<=0x4DBF or 0xF900<=cp<=0xFAFF
            or 0x3000<=cp<=0x303F or 0xFF00<=cp<=0xFFEF or 0x2E80<=cp<=0x2EFF)

def tw(text, size, bold=False):
    w = 0
    for c in text:
        f = gcjk(size) if is_cjk(c) else gf(size, bold)
        b = f.getbbox(c); w += b[2]-b[0]
    return w

def dm(draw, pos, text, size, fill, bold=False, cx=False):
    x = pos[0] - tw(text,size,bold)//2 if cx else pos[0]
    y = pos[1]
    for c in text:
        f = gcjk(size) if is_cjk(c) else gf(size, bold)
        draw.text((x,y), c, fill=fill, font=f)
        b = f.getbbox(c); x += b[2]-b[0]

def hex2rgb(h, fb=(180,180,180)):
    try: h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
    except: return fb

def load_img(data_or_path, size, label=""):
    img = None
    try:
        if data_or_path:
            if isinstance(data_or_path, bytes):
                img = Image.open(io.BytesIO(data_or_path)).convert("RGBA")
            elif os.path.exists(data_or_path):
                img = Image.open(data_or_path).convert("RGBA")
    except: pass
    if img:
        img.thumbnail(size, Image.LANCZOS)
        bg = Image.new("RGBA", size, (245,245,245,255))
        bg.paste(img, ((size[0]-img.width)//2, (size[1]-img.height)//2), img)
        return bg.convert("RGB")
    bg = Image.new("RGB", size, (225,225,225))
    d  = ImageDraw.Draw(bg)
    dm(d, (size[0]//2, size[1]//2-8), label or "（無圖）", 12, (140,140,140), cx=True)
    return bg

# ─── 核心生成 ─────────────────────────────────────────────────────────
def generate(cfg, imgs):
    W,H   = 1700, 510
    BAR   = 58
    MH    = H-BAR
    SW    = W//5
    PAD   = 14
    HDR   = 36
    CB    = (0,102,187); CR=(210,35,45); CD=(30,30,30)
    CG    = (100,100,100); CDV=(210,210,210)
    FS_H=21; FS_B=16; FS_S=13

    c = Image.new("RGB",(W,H),"white")
    d = ImageDraw.Draw(c)

    # 底部橫條
    d.rectangle([0,MH,W,H], fill=CR)
    dm(d,(W//2, MH+BAR//2-13), f"打樣：{cfg.get('sample_requirement','包包樣x2')}",
       26,"white",bold=True,cx=True)
    for i in range(1,5): d.line([i*SW,0,i*SW,MH],fill=CDV,width=2)

    # ── 欄1 袋形示意 ──
    X=0
    dm(d,(X+PAD,8),"袋形示意：",FS_H,CB,True)
    bh=MH-HDR-65
    c.paste(load_img(imgs.get("bag_image"),(SW-2*PAD,bh),"袋形圖片"),(X+PAD,HDR))
    if cfg.get("fold_note"): dm(d,(X+PAD,HDR+bh+5),cfg["fold_note"],FS_S,CG)
    ym=MH-52
    for ln in [f"材質：{cfg.get('material','')}",f"印刷：{cfg.get('print_method','')}"]:
        dm(d,(X+PAD,ym),ln,FS_B,CD); ym+=24

    # ── 欄2 印刷裁片 ──
    X=SW
    dm(d,(X+PAD,8),"印刷裁片：",FS_H,CB,True)
    dm(d,(X+178,10),"─── 刀模線",FS_S,CG)
    dm(d,(X+283,10),"··· 車線",FS_S,CG)
    dm(d,(X+PAD,HDR+2),"定位印：",FS_B,CD)
    tw2=(SW-3*PAD)//2; th=110; yt=HDR+24
    c.paste(load_img(imgs.get("front_open_image"),(tw2,th),"展開前幅"),(X+PAD,yt))
    c.paste(load_img(imgs.get("front_fold_image"),(tw2,th),"收折前幅"),(X+PAD*2+tw2,yt))
    dm(d,(X+PAD+tw2//2,yt-14),"展開前幅：",FS_S,CG,cx=True)
    dm(d,(X+PAD*2+tw2+tw2//2,yt-14),"收折前幅：",FS_S,CG,cx=True)
    yw=yt+th+10
    dm(d,(X+PAD,yw),"展開底部包圍＆拉桿背插、",FS_S,CD)
    dm(d,(X+PAD,yw+18),"收折包圍：",FS_S,CD)
    d.rectangle([X+PAD,yw+38,X+PAD+130,yw+56],fill=hex2rgb(cfg.get("bottom_wrap_color_hex","#A8263B")))
    dm(d,(X+PAD+140,yw+39),cfg.get("bottom_wrap_pantone","Pantone 187C"),FS_S,CD)
    yc=yw+65; ch_=MH-yc-PAD
    if ch_>30: c.paste(load_img(imgs.get("cut_layout_image"),(SW-2*PAD,ch_),"版型圖"),(X+PAD,yc))

    # ── 欄3 Pattern + Pantone ──
    X=SW*2; pw=SW//2-PAD-5
    dm(d,(X+PAD,8),"其餘Pattern:",FS_H,CB,True)
    c.paste(load_img(imgs.get("pattern_image"),(pw,160),"Pattern"),(X+PAD,HDR))
    dm(d,(X+PAD,HDR+165),"內裏：",FS_B,CB,True)
    c.paste(load_img(imgs.get("lining_image"),(pw,90),"內裏"),(X+PAD,HDR+190))
    if cfg.get("lining_note"):
        dm(d,(X+PAD,HDR+287),f"*{cfg['lining_note']}",FS_S,CR)
    dm(d,(X+SW//2+5,8),"Pantone",FS_H,CD,True)
    py=HDR+4
    for p in cfg.get("pantone_colors",[])[:7]:
        rgb=hex2rgb(p.get("hex","#888"),(140,140,140))
        d.rectangle([X+SW//2+5,py,X+SW//2+30,py+18],fill=rgb,outline=(0,0,0))
        dm(d,(X+SW//2+36,py+1),p.get("name",""),FS_S,CD)
        py+=30

    # ── 欄4 輔料 ──
    X=SW*3; ay=HDR+4
    dm(d,(X+PAD,8),"輔料：",FS_H,CB,True)
    for i,acc in enumerate(cfg.get("accessories",[])[:5],1):
        dm(d,(X+PAD,ay),f"{i}.{acc.get('name','')}",FS_B,CD); ay+=22
        if acc.get("detail"):
            if acc.get("detail_hex"):
                d.rectangle([X+PAD+10,ay,X+PAD+42,ay+13],fill=hex2rgb(acc["detail_hex"]),outline=(0,0,0))
                dm(d,(X+PAD+48,ay),acc["detail"],FS_S,CD)
            else:
                dm(d,(X+PAD+10,ay),acc["detail"],FS_S,CG)
            ay+=18
        key=f"acc_image_{i-1}"
        if imgs.get(key):
            c.paste(load_img(imgs[key],(SW-2*PAD,45),acc.get("name","")), (X+PAD,ay))
            ay+=50
        ay+=4

    # ── 欄5 設計稿 ──
    X=SW*4
    dm(d,(X+PAD,8),"設計稿：",FS_H,CB,True)
    c.paste(load_img(imgs.get("design_image"),(SW-2*PAD,MH-HDR-PAD),"設計稿"),(X+PAD,HDR))

    return c

# ─── HTML ─────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>打樣稿生成器</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f0f2f5;color:#1a1a1a}
  header{background:#d22333;color:#fff;padding:18px 32px;display:flex;align-items:center;gap:14px}
  header h1{font-size:22px;font-weight:700;letter-spacing:.5px}
  header span{font-size:13px;opacity:.85}
  .wrap{max-width:980px;margin:32px auto;padding:0 20px 60px}
  .card{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);margin-bottom:22px;overflow:hidden}
  .card-head{background:#f7f8fa;border-bottom:1px solid #eee;padding:14px 22px;font-weight:700;font-size:15px;color:#333;display:flex;align-items:center;gap:8px}
  .card-head .badge{background:#d22333;color:#fff;border-radius:20px;padding:2px 10px;font-size:12px}
  .card-body{padding:20px 22px}
  .row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:14px}
  .field{flex:1;min-width:200px}
  label{display:block;font-size:12px;font-weight:600;color:#555;margin-bottom:5px}
  input[type=text],input[type=color],select,textarea{width:100%;border:1px solid #ddd;border-radius:7px;padding:8px 11px;font-size:14px;transition:border .2s}
  input:focus,select:focus,textarea:focus{outline:none;border-color:#d22333}
  .upload-box{border:2px dashed #ddd;border-radius:8px;padding:18px 12px;text-align:center;cursor:pointer;transition:.2s;background:#fafafa;position:relative}
  .upload-box:hover{border-color:#d22333;background:#fff5f5}
  .upload-box input[type=file]{position:absolute;inset:0;opacity:0;cursor:pointer}
  .upload-box .icon{font-size:28px;margin-bottom:4px}
  .upload-box .name{font-size:12px;color:#888;margin-top:4px}
  .upload-box .fname{font-size:12px;color:#d22333;font-weight:600;margin-top:4px;word-break:break-all}
  .preview-img{max-width:100%;max-height:90px;border-radius:5px;margin-top:6px;object-fit:contain}
  .upload-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:12px}
  .pantone-list,.acc-list{display:flex;flex-direction:column;gap:10px}
  .pantone-row,.acc-row{display:flex;gap:10px;align-items:center;background:#f9f9f9;border-radius:8px;padding:10px 12px}
  .pantone-row input[type=text]{flex:1}
  .pantone-row input[type=color]{width:44px;height:36px;padding:2px;border-radius:6px;cursor:pointer}
  .acc-row .acc-name{flex:2}
  .acc-row .acc-detail{flex:2}
  .acc-row .acc-color{width:44px;height:36px;padding:2px;border-radius:6px;cursor:pointer}
  .acc-row .acc-img-box{flex:1;min-width:80px}
  .btn-add{background:none;border:1.5px dashed #bbb;color:#888;border-radius:7px;padding:7px 16px;cursor:pointer;font-size:13px;width:100%;margin-top:8px;transition:.2s}
  .btn-add:hover{border-color:#d22333;color:#d22333}
  .btn-del{background:none;border:none;color:#ccc;cursor:pointer;font-size:18px;flex-shrink:0;padding:0 4px;line-height:1}
  .btn-del:hover{color:#d22333}
  .generate-btn{width:100%;padding:16px;background:#d22333;color:#fff;border:none;border-radius:10px;font-size:18px;font-weight:700;cursor:pointer;letter-spacing:1px;transition:.2s;display:flex;align-items:center;justify-content:center;gap:10px}
  .generate-btn:hover{background:#b51c2a}
  .generate-btn:disabled{background:#ccc;cursor:not-allowed}
  .spinner{width:22px;height:22px;border:3px solid #fff3;border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;display:none}
  @keyframes spin{to{transform:rotate(360deg)}}
  .result-area{display:none;margin-top:24px;text-align:center}
  .result-area img{max-width:100%;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,.15)}
  .dl-btn{display:inline-block;margin-top:14px;background:#1a7a3b;color:#fff;padding:10px 30px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px}
  .dl-btn:hover{background:#145f2e}
  .tip{font-size:12px;color:#999;margin-top:4px}
</style>
</head>
<body>
<header>
  <div style="font-size:30px">📋</div>
  <div><h1>打樣稿生成器</h1><span>填寫資料 → 一鍵生成打樣稿 JPG</span></div>
</header>

<div class="wrap">
<form id="mainForm" enctype="multipart/form-data">

  <!-- 基本資訊 -->
  <div class="card">
    <div class="card-head"><span class="badge">基本</span> 產品資訊</div>
    <div class="card-body">
      <div class="row">
        <div class="field">
          <label>輸出檔名</label>
          <input type="text" name="output_name" placeholder="例：20260501-輕簡旅袋-PEKO打樣稿" value="打樣稿_output">
        </div>
        <div class="field">
          <label>打樣要求</label>
          <input type="text" name="sample_requirement" placeholder="包包樣x2" value="包包樣x2">
        </div>
      </div>
      <div class="row">
        <div class="field">
          <label>材質</label>
          <input type="text" name="material" placeholder="最新三分格">
        </div>
        <div class="field">
          <label>印刷方式</label>
          <input type="text" name="print_method" placeholder="數位印">
        </div>
        <div class="field">
          <label>收攝備註</label>
          <input type="text" name="fold_note" placeholder="收攝後">
        </div>
      </div>
    </div>
  </div>

  <!-- 欄2 印刷裁片 -->
  <div class="card">
    <div class="card-head"><span class="badge">欄2</span> 印刷裁片</div>
    <div class="card-body">
      <div class="row">
        <div class="field">
          <label>底部包圍 Pantone 名稱</label>
          <input type="text" name="bottom_wrap_pantone" placeholder="Pantone 187C" value="Pantone 187C">
        </div>
        <div class="field">
          <label>底部包圍顏色</label>
          <input type="color" name="bottom_wrap_color_hex" value="#A8263B">
        </div>
      </div>
      <div class="upload-grid">
        <div>
          <label>袋形示意圖</label>
          <div class="upload-box" id="box_bag_image">
            <input type="file" name="bag_image" accept="image/*" onchange="prevImg(this,'box_bag_image')">
            <div class="icon">🖼️</div><div class="name">袋形圖片</div>
            <div class="fname" id="fn_bag_image"></div>
            <img class="preview-img" id="pv_bag_image" style="display:none">
          </div>
        </div>
        <div>
          <label>展開前幅</label>
          <div class="upload-box" id="box_front_open_image">
            <input type="file" name="front_open_image" accept="image/*" onchange="prevImg(this,'box_front_open_image')">
            <div class="icon">📐</div><div class="name">展開前幅</div>
            <div class="fname" id="fn_front_open_image"></div>
            <img class="preview-img" id="pv_front_open_image" style="display:none">
          </div>
        </div>
        <div>
          <label>收折前幅</label>
          <div class="upload-box" id="box_front_fold_image">
            <input type="file" name="front_fold_image" accept="image/*" onchange="prevImg(this,'box_front_fold_image')">
            <div class="icon">📐</div><div class="name">收折前幅</div>
            <div class="fname" id="fn_front_fold_image"></div>
            <img class="preview-img" id="pv_front_fold_image" style="display:none">
          </div>
        </div>
        <div>
          <label>版型裁片圖（選填）</label>
          <div class="upload-box" id="box_cut_layout_image">
            <input type="file" name="cut_layout_image" accept="image/*" onchange="prevImg(this,'box_cut_layout_image')">
            <div class="icon">✂️</div><div class="name">版型圖</div>
            <div class="fname" id="fn_cut_layout_image"></div>
            <img class="preview-img" id="pv_cut_layout_image" style="display:none">
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 欄3 Pattern + Pantone -->
  <div class="card">
    <div class="card-head"><span class="badge">欄3</span> 其餘 Pattern + Pantone 色票</div>
    <div class="card-body">
      <div class="upload-grid" style="margin-bottom:18px">
        <div>
          <label>循環印花 Pattern</label>
          <div class="upload-box" id="box_pattern_image">
            <input type="file" name="pattern_image" accept="image/*" onchange="prevImg(this,'box_pattern_image')">
            <div class="icon">🎨</div><div class="name">Pattern</div>
            <div class="fname" id="fn_pattern_image"></div>
            <img class="preview-img" id="pv_pattern_image" style="display:none">
          </div>
        </div>
        <div>
          <label>內裏圖片（選填）</label>
          <div class="upload-box" id="box_lining_image">
            <input type="file" name="lining_image" accept="image/*" onchange="prevImg(this,'box_lining_image')">
            <div class="icon">🏷️</div><div class="name">內裏</div>
            <div class="fname" id="fn_lining_image"></div>
            <img class="preview-img" id="pv_lining_image" style="display:none">
          </div>
        </div>
        <div style="display:flex;flex-direction:column;justify-content:flex-end">
          <label>內裏備註</label>
          <input type="text" name="lining_note" placeholder="不可裂開" value="不可裂開">
        </div>
      </div>
      <label style="margin-bottom:10px;display:block">Pantone 色票（最多 7 個）</label>
      <div class="pantone-list" id="pantoneList"></div>
      <button type="button" class="btn-add" onclick="addPantone()">＋ 新增色票</button>
    </div>
  </div>

  <!-- 欄4 輔料 -->
  <div class="card">
    <div class="card-head"><span class="badge">欄4</span> 輔料（最多 5 項）</div>
    <div class="card-body">
      <div class="acc-list" id="accList"></div>
      <button type="button" class="btn-add" onclick="addAcc()">＋ 新增輔料</button>
    </div>
  </div>

  <!-- 欄5 設計稿 -->
  <div class="card">
    <div class="card-head"><span class="badge">欄5</span> 設計稿</div>
    <div class="card-body">
      <div class="upload-box" id="box_design_image" style="max-width:220px">
        <input type="file" name="design_image" accept="image/*" onchange="prevImg(this,'box_design_image')">
        <div class="icon">📄</div><div class="name">設計稿圖片</div>
        <div class="fname" id="fn_design_image"></div>
        <img class="preview-img" id="pv_design_image" style="display:none">
      </div>
    </div>
  </div>

  <!-- 生成按鈕 -->
  <button type="submit" class="generate-btn" id="genBtn">
    <div class="spinner" id="spinner"></div>
    <span id="btnText">🖨️ 生成打樣稿</span>
  </button>
</form>

<!-- 結果 -->
<div class="result-area" id="resultArea">
  <img id="resultImg" src="" alt="打樣稿預覽">
  <br>
  <a id="dlBtn" href="#" class="dl-btn" download>⬇ 下載 JPG</a>
</div>
</div><!-- wrap -->

<script>
// ── 圖片預覽 ──────────────────────────────────────────────────────────
function prevImg(input, boxId) {
  const file = input.files[0];
  if (!file) return;
  document.getElementById('fn_' + boxId.replace('box_', '')).textContent = file.name;
  const pv = document.getElementById('pv_' + boxId.replace('box_', ''));
  pv.src = URL.createObjectURL(file);
  pv.style.display = 'block';
}

// ── Pantone 色票 ──────────────────────────────────────────────────────
const PANTONE_DEFAULTS = [
  {name:'Pantone 7594C', hex:'#5C3A2E'},
  {name:'Pantone 474C',  hex:'#F5D9B0'},
  {name:'Pantone 185C',  hex:'#E31837'},
  {name:'Pantone BlakC', hex:'#231F20'},
  {name:'Pantone 187C',  hex:'#A8263B'},
];
let pantoneCount = 0;

function addPantone(name='', hex='#888888') {
  const list = document.getElementById('pantoneList');
  const i = pantoneCount++;
  const row = document.createElement('div');
  row.className = 'pantone-row';
  row.id = 'prow_'+i;
  row.innerHTML = `
    <input type="color" name="p_hex_${i}" value="${hex}">
    <input type="text"  name="p_name_${i}" placeholder="Pantone XXXC" value="${name}">
    <button type="button" class="btn-del" onclick="this.closest('.pantone-row').remove()">✕</button>`;
  list.appendChild(row);
}

PANTONE_DEFAULTS.forEach(p => addPantone(p.name, p.hex));

// ── 輔料 ──────────────────────────────────────────────────────────────
const ACC_DEFAULTS = [
  {name:'拉鍊、織帶：', detail:'Pantone 7594C', hex:'#5C3A2E'},
  {name:'拉牌：',        detail:'',              hex:''},
  {name:'murmurLOGO反光標', detail:'',           hex:''},
  {name:'織標(授權(C)2026)', detail:'',           hex:''},
  {name:'水洗標',        detail:'',              hex:''},
];
let accCount = 0;

function addAcc(name='', detail='', hex='') {
  if (accCount >= 5) { alert('最多 5 項輔料'); return; }
  const list = document.getElementById('accList');
  const i = accCount++;
  const row = document.createElement('div');
  row.className = 'acc-row';
  row.id = 'arow_'+i;
  row.innerHTML = `
    <span style="color:#999;font-size:13px;flex-shrink:0">${i+1}.</span>
    <input type="text" class="acc-name"   name="a_name_${i}"   placeholder="輔料名稱" value="${name}">
    <input type="text" class="acc-detail" name="a_detail_${i}" placeholder="備註/色號" value="${detail}">
    <input type="color" class="acc-color" name="a_hex_${i}" value="${hex||'#888888'}" title="備註色塊（可選）">
    <div class="acc-img-box">
      <div class="upload-box" style="padding:8px 6px" id="box_acc_image_${i}">
        <input type="file" name="acc_image_${i}" accept="image/*"
               onchange="prevImg(this,'box_acc_image_${i}')">
        <div class="icon" style="font-size:18px">🖼️</div>
        <div class="name" style="font-size:11px">圖片</div>
        <div class="fname" id="fn_acc_image_${i}" style="font-size:11px"></div>
      </div>
    </div>
    <button type="button" class="btn-del" onclick="this.closest('.acc-row').remove();accCount--">✕</button>`;
  list.appendChild(row);
}

ACC_DEFAULTS.forEach(a => addAcc(a.name, a.detail, a.hex));

// ── 表單提交 ──────────────────────────────────────────────────────────
document.getElementById('mainForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('genBtn');
  btn.disabled = true;
  document.getElementById('spinner').style.display = 'block';
  document.getElementById('btnText').textContent = '生成中…';

  try {
    const fd = new FormData(e.target);
    const res = await fetch('/generate', {method:'POST', body:fd});
    if (!res.ok) { const t = await res.text(); throw new Error(t); }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const name = document.querySelector('[name=output_name]').value || '打樣稿';
    document.getElementById('resultImg').src = url;
    document.getElementById('dlBtn').href = url;
    document.getElementById('dlBtn').download = name + '.jpg';
    document.getElementById('resultArea').style.display = 'block';
    document.getElementById('resultArea').scrollIntoView({behavior:'smooth'});
  } catch(err) {
    alert('❌ 生成失敗：' + err.message);
  } finally {
    btn.disabled = false;
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('btnText').textContent = '🖨️ 生成打樣稿';
  }
});
</script>
</body>
</html>"""

# ─── Routes ───────────────────────────────────────────────────────────

@app.route("/generate", methods=["POST"])
def generate_route():
    f  = request.form
    fs = request.files

    def read_img(key):
        file = fs.get(key)
        if file and file.filename:
            return file.read()
        return None

    cfg = {
        "sample_requirement":   f.get("sample_requirement","包包樣x2"),
        "material":             f.get("material",""),
        "print_method":         f.get("print_method",""),
        "fold_note":            f.get("fold_note",""),
        "bottom_wrap_color_hex":f.get("bottom_wrap_color_hex","#A8263B"),
        "bottom_wrap_pantone":  f.get("bottom_wrap_pantone","Pantone 187C"),
        "lining_note":          f.get("lining_note",""),
        "pantone_colors": [],
        "accessories":    [],
    }

    # Pantone 色票
    i = 0
    while f.get(f"p_name_{i}") is not None:
        name = f.get(f"p_name_{i}","").strip()
        hex_ = f.get(f"p_hex_{i}","#888")
        if name:
            cfg["pantone_colors"].append({"name":name,"hex":hex_})
        i += 1

    # 輔料
    i = 0
    while f.get(f"a_name_{i}") is not None:
        name   = f.get(f"a_name_{i}","").strip()
        detail = f.get(f"a_detail_{i}","").strip()
        hex_   = f.get(f"a_hex_{i}","")
        if name:
            cfg["accessories"].append({
                "name":name,
                "detail":detail,
                "detail_hex": hex_ if (detail and hex_ not in ("#888888","")) else ""
            })
        i += 1

    imgs = {
        "bag_image":          read_img("bag_image"),
        "front_open_image":   read_img("front_open_image"),
        "front_fold_image":   read_img("front_fold_image"),
        "cut_layout_image":   read_img("cut_layout_image"),
        "pattern_image":      read_img("pattern_image"),
        "lining_image":       read_img("lining_image"),
        "design_image":       read_img("design_image"),
    }
    # 輔料圖片
    for j in range(5):
        imgs[f"acc_image_{j}"] = read_img(f"acc_image_{j}")

    canvas = generate(cfg, imgs)
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=95)
    buf.seek(0)
    return send_file(buf, mimetype="image/jpeg",
                     download_name=f"{f.get('output_name','打樣稿')}.jpg")

@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "打樣稿生成器.html"))

@app.route("/analyze", methods=["POST"])
def analyze_route():
    """接收圖片 + API Key，呼叫 MiniMax 視覺 API 分析設計稿，回傳 JSON"""
    raw = ""
    try:
        import urllib.request as _urllib_req

        # 優先使用伺服器環境變數（部署版），其次使用前端傳入的 Key（本機版）
        api_key = os.environ.get("MINIMAX_API_KEY", "").strip() \
                  or request.headers.get("X-Api-Key", "").strip()
        if not api_key:
            return jsonify({"error": "缺少 API Key（請在 Render 環境變數設定 MINIMAX_API_KEY）"}), 400

        data = request.get_json()
        img_b64   = data.get("image_b64", "")
        img_type  = data.get("image_type", "image/jpeg")
        if not img_b64:
            return jsonify({"error": "缺少圖片資料"}), 400

        prompt = (
            "你是一個專業的產品設計稿分析助手。請仔細分析這張設計稿圖片，"
            "提取所有可見的產品資訊，以純 JSON 格式回傳（不要加 markdown 代碼塊或任何說明文字）：\n\n"
            "{\n"
            '  "material": "材質（如：Polyester、最新三分格）",\n'
            '  "print_method": "印刷方式（如：數位印）",\n'
            '  "fold_note": "收攝相關備註",\n'
            '  "bottom_wrap_pantone": "底部或主要包圍布料的Pantone色號",\n'
            '  "bottom_wrap_color_hex": "#XXXXXX（底部顏色的近似hex）",\n'
            '  "lining_note": "內裏備註（如：不可裂開）",\n'
            '  "pantone_colors": [\n'
            '    {"name": "Pantone XXXC", "hex": "#XXXXXX"}\n'
            '  ],\n'
            '  "accessories": [\n'
            '    {"name": "輔料名稱：", "detail": "備註或色號（若無則空字串）"}\n'
            '  ]\n'
            "}\n\n"
            "注意：pantone_colors 列出圖中所有可見的Pantone色號；"
            "accessories 包含拉鍊、織帶、拉牌、LOGO標、織標、水洗標等；"
            "找不到的欄位填空字串；只回傳 JSON。"
        )

        payload = {
            "model": "MiniMax-VL-01",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img_type};base64,{img_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }],
            "max_tokens": 1500
        }

        req = _urllib_req.Request(
            "https://api.minimax.chat/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with _urllib_req.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())

        raw = result["choices"][0]["message"]["content"].strip()
        # 容錯：移除可能的 ```json 包裝
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return jsonify(parsed)

    except json.JSONDecodeError as e:
        return jsonify({"error": f"回傳格式解析失敗：{e}\n原始：{raw[:300]}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  打樣稿生成器")
    print("  開啟瀏覽器：http://localhost:5050")
    print("  按 Ctrl+C 停止")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5050, debug=False)
