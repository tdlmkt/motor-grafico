from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import io, os, requests, textwrap

app = FastAPI()

# --- SETUP DE FONTES ---
def download_font(url, filename):
    if not os.path.exists(filename):
        r = requests.get(url, allow_redirects=True)
        open(filename, 'wb').write(r.content)

download_font("https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond-Medium.ttf", "serif.ttf")
download_font("https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond-MediumItalic.ttf", "serif_italic.ttf")
download_font("https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf", "sans_bold.ttf")
download_font("https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Light.ttf", "sans_light.ttf")

# --- HUB DE TEMPLATES ---
TEMPLATES = {
    "gastronomia": {"gold": "#d4af72", "title_font": "serif.ttf", "sub_font": "sans_light.ttf", "v_center": 40, "v_edge": 180},
    "diversao": {"gold": "#d9b87a", "title_font": "serif.ttf", "sub_font": "sans_light.ttf", "v_center": 30, "v_edge": 220},
    "quizz": {"gold": "#ff4d4d", "title_font": "sans_bold.ttf", "sub_font": "sans_light.ttf", "v_center": 50, "v_edge": 200},
    "sabia": {"gold": "#4db8ff", "title_font": "serif_italic.ttf", "sub_font": "sans_light.ttf", "v_center": 40, "v_edge": 190}
}

def draw_text_centered(draw, text, y, font, fill, max_chars=28):
    if not text or text in ["undefined", "null"]: return y # Trava de segurança
    lines = textwrap.wrap(str(text), width=max_chars)
    current_y = y
    line_height = draw.textbbox((0, 0), "A", font=font)[3] - draw.textbbox((0, 0), "A", font=font)[1]
    for line in lines:
        w = draw.textbbox((0, 0), line, font=font)[2]
        draw.text(((1080 - w) / 2, current_y), line, font=font, fill=fill)
        current_y += line_height * 1.2
    return current_y

@app.post("/render-slide")
async def render_slide(
    file: UploadFile = File(...),
    badge: str = Form(""),
    title: str = Form(""),
    subtitle: str = Form(""),
    slide_num: int = Form(...),
    template_name: str = Form("gastronomia")
):
    cfg = TEMPLATES.get(template_name, TEMPLATES["gastronomia"])
    
    # Recorte Inteligente e Blindado (ImageOps)
    img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    img = ImageOps.fit(img, (1080, 1350), method=Image.Resampling.LANCZOS)
    target_w, target_h = 1080, 1350

    # Vinheta Dramática
    overlay = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    for i in range(target_h):
        if i < target_h/4: alpha = int(cfg["v_edge"] * (1 - i/(target_h/4)))
        elif i > 3*target_h/4: alpha = int(cfg["v_edge"] * ((i-3*target_h/4)/(target_h/4)))
        else: alpha = cfg["v_center"]
        d.line([(0, i), (target_w, i)], fill=(0,0,0,alpha))
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(img)

    # Moldura
    if not (slide_num == 6 and template_name in ["diversao", "quizz"]):
        draw.rectangle([(25, 25), (1055, 1325)], outline=cfg["gold"], width=2)
    
    # Badge
    badge_str = str(badge).upper() if badge and badge not in ["undefined", "null"] else ""
    f_badge = ImageFont.truetype("sans_light.ttf", 22)
    if badge_str:
        w = draw.textbbox((0,0), badge_str, font=f_badge)[2]
        draw.text(((1080 - w)/2, 60), badge_str, font=f_badge, fill="white")

    # Fontes
    f_title = ImageFont.truetype(cfg["title_font"], 80 if template_name != "quizz" else 95)
    f_sub = ImageFont.truetype(cfg["sub_font"], 33)

    # Renderização Condicional de Slides
    if slide_num == 1:
        f_capa = ImageFont.truetype("serif_italic.ttf", 105)
        last_y = draw_text_centered(draw, title, 500, f_capa, "white")
        draw_text_centered(draw, subtitle, last_y + 40, f_sub, "white", max_chars=40)
    elif slide_num == 6:
        if template_name == "diversao":
            draw.rectangle([(0, 1050), (1080, 1350)], fill="#3d4038")
            draw.text((390, 1180), "SALVA ESSE POST", font=f_badge, fill="white")
            draw_text_centered(draw, title, 780, ImageFont.truetype("serif.ttf", 90), "white")
        elif template_name == "quizz":
            draw.rectangle([(0, 1050), (1080, 1350)], fill=cfg["gold"])
            draw.text((390, 1180), "QUAL SEU PALPITE?", font=f_badge, fill="black")
            draw_text_centered(draw, title, 550, f_title, "white")
        else:
            draw_text_centered(draw, title, 550, f_title, "white")
            draw.rounded_rectangle([(365, 750), (365+350, 750+60)], radius=30, outline="white", width=2)
            draw.text((435, 765), "SALVA ESSE POST", font=f_badge, fill="white")
    else:
        last_y = draw_text_centered(draw, title, 520, f_title, "white")
        draw_text_centered(draw, subtitle, last_y + 30, f_sub, "white", max_chars=40)

    # Paginação
    if not (slide_num == 6 and template_name in ["diversao", "quizz"]):
        draw.text((500, 1270), f"{slide_num:02d} / 06", font=f_badge, fill=cfg["gold"])

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format='JPEG', quality=95)
    return Response(content=buf.getvalue(), media_type="image/jpeg")
