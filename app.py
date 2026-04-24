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

# --- CONFIGS DE TEMPLATE (O Hub de Marcas) ---
TEMPLATES = {
    "gastronomia": {
        "gold": "#d4af72",
        "title_font": "serif.ttf",
        "sub_font": "sans.ttf",
        "vignette_center_alpha": 40,
        "vignette_edge_alpha": 180,
    },
    "diversao": {
        "gold": "#d9b87a", # Ouro Safari mais quente
        "title_font": "serif.ttf",
        "sub_font": "sans.ttf",
        "vignette_center_alpha": 30, # Centro mais claro
        "vignette_edge_alpha": 220, # Bordas quase pretas para drama
    }
}

def draw_text_centered(draw, text, y, font, fill, max_chars=28, line_spacing=1.1):
    lines = textwrap.wrap(text, width=max_chars)
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
    slide_num: int = Form(...),
    template_name: str = Form("gastronomia") # Novo Parâmetro
):
    # Carrega Template Config
    cfg = TEMPLATES.get(template_name, TEMPLATES["gastronomia"])
    gold = cfg["gold"]

    # 1. Processamento Imagem Base (Crop 1080x1350)
    img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    target_w, target_h = 1080, 1350
    img = img.resize((target_w, int(target_w * img.height / img.width)), Image.Resampling.LANCZOS)
    img = img.crop((0, (img.height - target_h)//2, target_w, (img.height + target_h)//2))

    # 2. Overlay Dramático Customizado (Vignette)
    overlay = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    c_a = cfg["vignette_center_alpha"]
    e_a = cfg["vignette_edge_alpha"]
    for i in range(target_h):
        if i < target_h/4: alpha = int(e_a * (1 - i/(target_h/4)))
        elif i > 3*target_h/4: alpha = int(e_a * ((i-3*target_h/4)/(target_h/4)))
        else: alpha = c_a
        d.line([(0, i), (target_w, i)], fill=(0,0,0,alpha))
    
    mask = Image.new('L', (target_w, target_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.ellipse([-target_w//4, -target_h//4, 1.25*target_w, 1.25*target_h], fill=180)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=250))
    vignette = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
    vignette.putalpha(Image.eval(mask, lambda x: 255 - x))
    
    combined = Image.alpha_composite(img.convert('RGBA'), overlay)
    img = Image.alpha_composite(combined, vignette)
    draw = ImageDraw.Draw(img)

    # 3. Moldura (Não desenha no Slide 6 Diversão)
    if not (template_name == "diversao" and slide_num == 6):
        draw.rectangle([(25, 25), (1055, 1325)], outline=gold, width=2)
    
    # Badge (Montserrat Light)
    font_badge = ImageFont.truetype("sans.ttf", 22)
    draw.text(((1080 - draw.textbbox((0,0), badge, font=font_badge)[2])/2, 60), badge.upper(), font=font_badge, fill="white")

    # Fonts
    f_title = ImageFont.truetype(cfg["title_font"], 78)
    f_title_capa = ImageFont.truetype("serif_italic.ttf", 100) # Mantém itálico na capa para todos
    f_sub = ImageFont.truetype(cfg["sub_font"], 33)

    # 4. Textos (Capa vs Internos vs Finais)
    if slide_num == 1:
        last_y = draw_text_centered(draw, title, 500, f_title_capa, "white")
        draw_text_centered(draw, subtitle, last_y + 40, f_sub, "white", max_chars=40)
    elif slide_num == 6:
        # Layout Especial Diversão (Kruger Style)
        if template_name == "diversao":
            f_end_title = ImageFont.truetype("serif.ttf", 90)
            draw_text_centered(draw, title, 780, f_end_title, "white")
            # Barra sólida no rodapé (Dourado escuro queimado)
            draw.rectangle([(0, 1050), (1080, 1350)], fill="#3d4038") # Cor inspirada no Safari
            draw.text((390, 1180), "SALVA ESSE POST", font=font_badge, fill="white", spacing=4) # Letras espaçadas
        else: # Layout Padrão Gastronomia
            f_end_title = ImageFont.truetype("serif.ttf", 80)
            draw_text_centered(draw, title, 550, f_end_title, "white")
            # Botão Pill
            draw.rounded_rectangle([(365, 750), (365+350, 750+60)], radius=30, outline="white", width=2)
            draw.text((435, 765), "SALVA ESSE POST", font=font_badge, fill="white")
    else: # Slides Internos
        last_y = draw_text_centered(draw, title, 520, f_title, "white")
        draw_text_centered(draw, subtitle, last_y + 30, f_sub, "white", max_chars=40)

    # 5. Rodapé (Paginação)
    if not (template_name == "diversao" and slide_num == 6):
        draw.text((500, 1270), f"{slide_num:02d} / 06", font=font_badge, fill=gold)

    # Export
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format='JPEG', quality=95)
    return Response(content=buf.getvalue(), media_type="image/jpeg")
