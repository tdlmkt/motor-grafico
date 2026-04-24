from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io, os, requests, textwrap

app = FastAPI()

# --- SETUP DE FONTES ---
def download_font(url, filename):
    if not os.path.exists(filename):
        r = requests.get(url, allow_redirects=True)
        open(filename, 'wb').write(r.content)

# Fontes Premium
download_font("https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond-Medium.ttf", "serif.ttf")
download_font("https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond-MediumItalic.ttf", "serif_italic.ttf")
download_font("https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Light.ttf", "sans.ttf")

def draw_text_centered(draw, text, y, font, fill, max_width=900, line_spacing=1.2):
    lines = textwrap.wrap(text, width=25) # Ajuste de largura conforme a fonte
    current_y = y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((1080 - w) / 2, current_y), line, font=font, fill=fill)
        current_y += font.size * line_spacing
    return current_y

@app.post("/render-slide")
async def render_slide(
    file: UploadFile = File(...),
    badge: str = Form(...),
    title: str = Form(...),
    subtitle: str = Form(""),
    slide_num: int = Form(...)
):
    # 1. Processamento da Imagem Base
    img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    target_w, target_h = 1080, 1350
    img = img.resize((target_w, int(target_w * img.height / img.width)), Image.Resampling.LANCZOS)
    img = img.crop((0, (img.height - target_h)//2, target_w, (img.height + target_h)//2))

    # 2. Overlay Dramático (Vignette)
    overlay = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    for i in range(target_h):
        alpha = int(160 * (1 - i/(target_h/3))) if i < target_h/3 else int(160 * ((i-2*target_h/3)/(target_h/3))) if i > 2*target_h/3 else 50
        d.line([(0, i), (target_w, i)], fill=(0,0,0,alpha))
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(img)

    # 3. Moldura e Badge
    gold = "#d4af72"
    draw.rectangle([(25, 25), (1055, 1325)], outline=gold, width=2)
    
    font_badge = ImageFont.truetype("sans.ttf", 22)
    draw.text(((1080 - draw.textbbox((0,0), badge, font=font_badge)[2])/2, 60), badge.upper(), font=font_badge, fill="white")

    # 4. Textos (Capa vs Internos vs CTA)
    if slide_num == 1:
        f_title = ImageFont.truetype("serif_italic.ttf", 110)
        f_sub = ImageFont.truetype("sans.ttf", 35)
        last_y = draw_text_centered(draw, title, 500, f_title, "white")
        draw_text_centered(draw, subtitle, last_y + 40, f_sub, "white")
    elif slide_num == 6:
        f_title = ImageFont.truetype("serif.ttf", 80)
        draw_text_centered(draw, title, 550, f_title, "white")
        # Botão Salva esse Post
        pill_w, pill_h = 350, 60
        draw.rounded_rectangle([(365, 750), (365+pill_w, 750+pill_h)], radius=30, outline="white", width=2)
        draw.text((435, 765), "SALVA ESSE POST", font=font_badge, fill="white")
    else:
        f_title = ImageFont.truetype("serif.ttf", 75)
        f_sub = ImageFont.truetype("sans.ttf", 32)
        last_y = draw_text_centered(draw, title, 520, f_title, "white")
        draw_text_centered(draw, subtitle, last_y + 30, f_sub, "white")

    # 5. Rodapé (Paginação)
    draw.text((500, 1270), f"{slide_num:02d} / 06", font=font_badge, fill=gold)

    # Export
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format='JPEG', quality=95)
    return Response(content=buf.getvalue(), media_type="image/jpeg")
