from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io

app = FastAPI()

# --- HUB DE TEMPLATES ---
TEMPLATES = {
    "gastronomia": {"gold": "#d4af72", "title_font": "CormorantGaramond-Medium.ttf", "sub_font": "Montserrat-Light.ttf", "v_center": 40, "v_edge": 180},
    "diversao": {"gold": "#d9b87a", "title_font": "CormorantGaramond-Medium.ttf", "sub_font": "Montserrat-Light.ttf", "v_center": 30, "v_edge": 220},
    "quizz": {"gold": "#ff4d4d", "title_font": "Montserrat-Bold.ttf", "sub_font": "Montserrat-Light.ttf", "v_center": 50, "v_edge": 200},
    "sabia": {"gold": "#4db8ff", "title_font": "CormorantGaramond-MediumItalic.ttf", "sub_font": "Montserrat-Light.ttf", "v_center": 40, "v_edge": 190}
}

# NOVA LÓGICA: Medição exata de pixels (Evita texto vazando da tela)
def wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in str(text).split('\n'):
        words = paragraph.split()
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word]) if current_line else word
            w = draw.textlength(test_line, font=font)
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        if current_line:
            lines.append(' '.join(current_line))
    return lines

def draw_text_centered(draw, text, y, font, fill, max_width=900):
    if not text or text in ["undefined", "null"]: return y
    lines = wrap_text(draw, text, font, max_width)
    current_y = y
    bbox = draw.textbbox((0, 0), "A", font=font)
    line_height = bbox[3] - bbox[1]
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((1080 - w) / 2, current_y), line, font=font, fill=fill)
        current_y += line_height * 1.25 # Espaçamento elegante entre linhas
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
    
    img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    img = ImageOps.fit(img, (1080, 1350), method=Image.Resampling.LANCZOS)
    target_w, target_h = 1080, 1350

    overlay = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    for i in range(target_h):
        if i < target_h/4: alpha = int(cfg["v_edge"] * (1 - i/(target_h/4)))
        elif i > 3*target_h/4: alpha = int(cfg["v_edge"] * ((i-3*target_h/4)/(target_h/4)))
        else: alpha = cfg["v_center"]
        d.line([(0, i), (target_w, i)], fill=(0,0,0,alpha))
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(img)

    if not (slide_num == 6 and template_name in ["diversao", "quizz"]):
        draw.rectangle([(25, 25), (1055, 1325)], outline=cfg["gold"], width=2)
    
    badge_str = str(badge).upper() if badge and badge not in ["undefined", "null"] else ""
    
    try:
        # Tamanhos recalibrados para visual de revista editorial
        f_badge = ImageFont.truetype("Montserrat-Light.ttf", 20)
        f_title = ImageFont.truetype(cfg["title_font"], 75 if template_name != "quizz" else 85)
        f_sub = ImageFont.truetype(cfg["sub_font"], 30)
        f_capa = ImageFont.truetype("CormorantGaramond-MediumItalic.ttf", 95)
        f_div = ImageFont.truetype("CormorantGaramond-Medium.ttf", 85)
    except:
        f_badge = f_title = f_sub = f_capa = f_div = ImageFont.load_default()

    if badge_str:
        w = draw.textlength(badge_str, font=f_badge)
        draw.text(((1080 - w)/2, 60), badge_str, font=f_badge, fill="white")

    if slide_num == 1:
        last_y = draw_text_centered(draw, title, 500, f_capa, "white", max_width=950)
        draw_text_centered(draw, subtitle, last_y + 40, f_sub, "white", max_width=850)
    elif slide_num == 6:
        if template_name == "diversao":
            draw.rectangle([(0, 1050), (1080, 1350)], fill="#3d4038")
            w_cta = draw.textlength("SALVA ESSE POST", font=f_badge)
            draw.text(((1080 - w_cta)/2, 1180), "SALVA ESSE POST", font=f_badge, fill="white")
            draw_text_centered(draw, title, 780, f_div, "white", max_width=950)
        elif template_name == "quizz":
            draw.rectangle([(0, 1050), (1080, 1350)], fill=cfg["gold"])
            w_cta = draw.textlength("QUAL SEU PALPITE?", font=f_badge)
            draw.text(((1080 - w_cta)/2, 1180), "QUAL SEU PALPITE?", font=f_badge, fill="black")
            draw_text_centered(draw, title, 550, f_title, "white", max_width=950)
        else:
            draw_text_centered(draw, title, 550, f_title, "white", max_width=950)
            draw.rounded_rectangle([(365, 750), (365+350, 750+60)], radius=30, outline="white", width=2)
            w_cta = draw.textlength("SALVA ESSE POST", font=f_badge)
            draw.text(((1080 - w_cta)/2, 765), "SALVA ESSE POST", font=f_badge, fill="white")
    else:
        last_y = draw_text_centered(draw, title, 520, f_title, "white", max_width=950)
        draw_text_centered(draw, subtitle, last_y + 40, f_sub, "white", max_width=850)

    if not (slide_num == 6 and template_name in ["diversao", "quizz"]):
        draw.text((500, 1270), f"{slide_num:02d} / 06", font=f_badge, fill=cfg["gold"])

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format='JPEG', quality=95)
    return Response(content=buf.getvalue(), media_type="image/jpeg")
