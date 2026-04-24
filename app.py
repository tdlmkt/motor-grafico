from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import os
import requests

app = FastAPI()

# --- Sistema de Fontes Automático ---
def download_font(url, filename):
    if not os.path.exists(filename):
        r = requests.get(url, allow_redirects=True)
        open(filename, 'wb').write(r.content)

# Baixando Cormorant Garamond e Montserrat direto do Google
download_font("https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond-Regular.ttf", "title_font.ttf")
download_font("https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Light.ttf", "badge_font.ttf")

def apply_premium_overlay(img):
    w, h = img.size
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    for y in range(h):
        if y < h // 4: alpha = int(180 * (1 - y / (h // 4)))
        elif y > 3 * h // 4: alpha = int(180 * ((y - 3 * h // 4) / (h // 4)))
        else: alpha = 40
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        
    mask = Image.new('L', img.size, 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.ellipse([-w//4, -h//4, 1.25*w, 1.25*h], fill=220)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=250))
    
    vignette = Image.new('RGBA', img.size, (0, 0, 0, 0))
    vignette.putalpha(Image.eval(mask, lambda x: 255 - x))
    
    combined = Image.alpha_composite(img.convert('RGBA'), overlay)
    return Image.alpha_composite(combined, vignette)

@app.post("/render-slide")
async def render_slide(
    file: UploadFile = File(...),
    badge: str = Form(...),
    title: str = Form(...),
    subtitle: str = Form(""),
    slide_num: str = Form(...)
):
    # Carrega imagem
    image_data = await file.read()
    img = Image.open(io.BytesIO(image_data)).convert("RGB")
    
    # Crop Premium (1080x1350)
    target_w, target_h = 1080, 1350
    bg_ratio = img.width / img.height
    if bg_ratio > (target_w / target_h):
        new_h = target_h
        new_w = int(target_h * bg_ratio)
    else:
        new_w = target_w
        new_h = int(target_w / bg_ratio)
        
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left, top = (new_w - target_w) // 2, (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    
    # Efeitos Visuais
    img = apply_premium_overlay(img)
    draw = ImageDraw.Draw(img)
    
    # Borda Dourada Fina (Inset 25px)
    draw.rectangle([(25, 25), (target_w - 25, target_h - 25)], outline="#d4af72", width=2)
    
    # --- Os textos entrariam aqui (versão simplificada para garantir a conexão inicial) ---
    
    # Exporta
    img_byte_arr = io.BytesIO()
    img.convert("RGB").save(img_byte_arr, format='JPEG', quality=95)
    return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")
