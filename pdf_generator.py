import sys, json

def generate_pdf(company_id, kupujuci_meno, kupujuci_datum, kupujuci_adresa, kupujuci_op,
                 predavajuci_meno, predavajuci_datum, predavajuci_adresa, predavajuci_op,
                 vozidlo, vin, kupna_cena, akontacia, financovana, iban, miesto, datum, output_path,
                 sig_images=None,
                 logo_path=None,
                 kupujuci_firma=None, kupujuci_ico=None, kupujuci_dic=None, kupujuci_firma_sidlo=None,
                 predavajuci_firma=None, predavajuci_ico=None, predavajuci_dic=None, predavajuci_firma_sidlo=None,
                 **kwargs):

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, Image as RLImage
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.pdfmetrics import registerFontFamily

    import os
    # Try DejaVu fonts, fall back to Liberation if not available
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/",
        "/usr/share/fonts/truetype/liberation/",
        "/usr/share/fonts/truetype/freefont/",
    ]
    
    font_normal = None
    font_bold = None
    font_italic = None
    
    for base in font_paths:
        if os.path.exists(base + "DejaVuSans.ttf"):
            font_normal = base + "DejaVuSans.ttf"
            font_bold = base + "DejaVuSans-Bold.ttf"
            font_italic = base + "DejaVuSans-Oblique.ttf" if os.path.exists(base + "DejaVuSans-Oblique.ttf") else base + "DejaVuSans.ttf"
            break
        elif os.path.exists(base + "LiberationSans-Regular.ttf"):
            font_normal = base + "LiberationSans-Regular.ttf"
            font_bold = base + "LiberationSans-Bold.ttf"
            font_italic = base + "LiberationSans-Italic.ttf" if os.path.exists(base + "LiberationSans-Italic.ttf") else base + "LiberationSans-Regular.ttf"
            break
        elif os.path.exists(base + "FreeSans.ttf"):
            font_normal = base + "FreeSans.ttf"
            font_bold = base + "FreeSansBold.ttf" if os.path.exists(base + "FreeSansBold.ttf") else base + "FreeSans.ttf"
            font_italic = base + "FreeSansOblique.ttf" if os.path.exists(base + "FreeSansOblique.ttf") else base + "FreeSans.ttf"
            break
    
    if font_normal:
        pdfmetrics.registerFont(TTFont("DVSans", font_normal))
        pdfmetrics.registerFont(TTFont("DVSans-Bold", font_bold))
        pdfmetrics.registerFont(TTFont("DVSans-Italic", font_italic))
        registerFontFamily("DVSans", normal="DVSans", bold="DVSans-Bold", italic="DVSans-Italic", boldItalic="DVSans-Bold")
    else:
        # Fallback to built-in Helvetica
        from reportlab.lib.styles import getSampleStyleSheet
        pass

    companies = {
        "stability":   {"name": "stability s. r. o.",   "sidlo": "N\u00e1bre\u017eie ml\u00e1de\u017ee 569/81, 949 12 Nitra", "ico": "53392663", "dic": "2121373353"},
        "autazababku": {"name": "autazababku s. r. o.", "sidlo": "N\u00e1bre\u017eie ml\u00e1de\u017ee 569/81, 949 01 Nitra", "ico": "57364508", "dic": "2122716079"},
        "finlife":     {"name": "Finlife s. r. o.",     "sidlo": "N\u00e1bre\u017eie ml\u00e1de\u017ee 569/81, 949 01 Nitra", "ico": "56332441", "dic": "2122276574"}
    }
    company = companies[company_id]

    DARK  = colors.HexColor("#2d3441")
    GRAY  = colors.HexColor("#555555")
    LGRAY = colors.HexColor("#cccccc")

    doc = SimpleDocTemplate(output_path, pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm, topMargin=12*mm, bottomMargin=18*mm)

    def sty(name, font="DVSans", size=9.5, **kw):
        return ParagraphStyle(name, fontName=font, fontSize=size, **kw)

    nadpis    = sty("n",  font="DVSans-Bold", size=14, alignment=TA_CENTER, spaceAfter=2*mm, textColor=DARK)
    podnadpis = sty("pn", size=8.5, alignment=TA_CENTER, spaceAfter=5*mm, textColor=GRAY)
    sekcia    = sty("s",  font="DVSans-Bold", size=10, spaceBefore=5*mm, spaceAfter=2*mm, textColor=DARK)
    normal    = sty("no", size=9.5, spaceAfter=1.5*mm, leading=14)
    bl        = sty("bl", font="DVSans-Bold", size=9.5, spaceAfter=1*mm)
    poz       = sty("po", font="DVSans-Italic", size=8.5, textColor=GRAY, spaceAfter=1.5*mm)
    tl_sty    = sty("tl", font="DVSans-Bold", size=9)
    tv_sty    = sty("tv", size=9)
    pod_sty   = sty("ps", size=9, alignment=TA_CENTER, spaceBefore=2*mm)
    it_sty    = sty("it", font="DVSans-Italic", size=8.5, textColor=GRAY, spaceBefore=2*mm, spaceAfter=3*mm)

    def hr(bold=False):
        return HRFlowable(width="100%", thickness=1.5 if bold else 0.5,
                          color=DARK if bold else LGRAY, spaceAfter=3*mm, spaceBefore=1*mm)

    story = []

    if logo_path:
        try:
            logo_img = RLImage(logo_path, width=70*mm, height=14.7*mm)
            ht = Table([[logo_img, ""]], colWidths=[80*mm, 90*mm])
            ht.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), DARK),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("LEFTPADDING", (0,0), (0,0), 8),
                ("TOPPADDING", (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(ht)
            story.append(Spacer(1, 5*mm))
        except Exception as e:
            print(f"Logo error: {e}")

    story.append(Paragraph("ZMLUVA O SPROSTREDKOVAN\u00cd", nadpis))
    story.append(Paragraph(
        "uzatvoren\u00e1 pod\u013ea \u00a7 588 a nasl. z\u00e1kona \u010d. 40/1964 Zb. Ob\u010diansky z\u00e1konn\u00edk v platnom znen\u00ed (\u010falej len Ob\u010diansky z\u00e1konn\u00edk)",
        podnadpis))
    story.append(hr(True))

    story.append(Paragraph("1. Zmluvn\u00e9 strany", sekcia))
    story.append(hr())

    def blok(title, rows):
        story.append(Paragraph(title, bl))
        tdata = [[Paragraph(l, tl_sty), Paragraph(v or "\u2014", tv_sty)] for l, v in rows]
        t = Table(tdata, colWidths=[45*mm, 120*mm])
        t.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("TOPPADDING",(0,0),(-1,-1),2),
            ("LEFTPADDING",(0,0),(0,-1),0),
        ]))
        story.append(t)
        story.append(Spacer(1, 3*mm))

    blok("Sprostredkovate\u013e", [
        ("Obchodn\u00e9 meno:", company["name"]),
        ("S\u00eddlo:", company["sidlo"]),
        ("I\u010cO:", company["ico"]),
        ("DI\u010c:", company["dic"]),
    ])
    story.append(Paragraph("(\u010falej len Sprostredkovate\u013e)", poz))
    story.append(hr())

    pred_rows = []
    if predavajuci_firma:
        pred_rows = [
            ("Obchodn\u00e9 meno:", predavajuci_firma),
            ("I\u010cO:", predavajuci_ico or ""),
            ("DI\u010c:", predavajuci_dic or ""),
            ("S\u00eddlo firmy:", predavajuci_firma_sidlo or predavajuci_adresa),
            ("Konate\u013e / z\u00e1stupca:", predavajuci_meno),
            ("D\u00e1tum narodenia:", predavajuci_datum),
            ("OP konate\u013ea:", predavajuci_op),
        ]
    else:
        pred_rows = [
            ("Meno:", predavajuci_meno),
            ("D\u00e1tum narodenia:", predavajuci_datum),
            ("Adresa:", predavajuci_adresa),
            ("OP:", predavajuci_op),
        ]
        if predavajuci_ico:
            pred_rows += [
                ("I\u010cO:", predavajuci_ico),
                ("DI\u010c:", predavajuci_dic or ""),
            ]
    blok("Pred\u00e1vaj\u00faci", pred_rows)
    story.append(Paragraph("(\u010falej len Pred\u00e1vaj\u00faci)", poz))
    story.append(hr())

    # Kupujuci - firma, živnostník alebo FO
    kup_rows = []
    if kupujuci_firma:
        kup_rows = [
            ("Obchodné meno:", kupujuci_firma),
            ("IČO:", kupujuci_ico or ""),
            ("DIČ:", kupujuci_dic or ""),
            ("Sídlo:", kupujuci_firma_sidlo or kupujuci_adresa),
            ("Konateľ / zástupca:", kupujuci_meno),
            ("Dátum narodenia:", kupujuci_datum),
            ("OP konateľa:", kupujuci_op),
        ]
    else:
        kup_rows = [
            ("Meno:", kupujuci_meno),
            ("Dátum narodenia:", kupujuci_datum),
            ("Adresa:", kupujuci_adresa),
            ("OP:", kupujuci_op),
        ]
        if kupujuci_ico:
            kup_rows += [
                ("IČO:", kupujuci_ico),
                ("DIČ:", kupujuci_dic or ""),
            ]
    blok("Kupuj\u00faci", kup_rows)
    story.append(Paragraph("(\u010falej len Kupuj\u00faci)", poz))
    story.append(hr(True))

    story.append(Paragraph("2. Predmet zmluvy", sekcia))
    story.append(hr())

    rows2 = [
        ("2.1 Sprostredkovate\u013e sa zav\u00e4zuje sprostredkova\u0165 financovanie na motorov\u00e9 vozidlo:", vozidlo),
        ("2.2 VIN vozidla:", vin),
        ("2.3 K\u00fapna cena vozidla:", f"{kupna_cena} EUR"),
        ("Akont\u00e1cia:", f"{akontacia} EUR \u2013 pri podpise KZ"),
        ("Financovan\u00e1 \u010diastka:", f"{financovana} EUR"),
        ("IBAN (\u00fa\u010det pred\u00e1vaj\u00faceho):", iban),
    ]
    for label, val in rows2:
        row = [[Paragraph(label, tl_sty), Paragraph(val, tv_sty)]]
        t = Table(row, colWidths=[95*mm, 75*mm])
        t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BOTTOMPADDING",(0,0),(-1,-1),3),
                               ("TOPPADDING",(0,0),(-1,-1),2),("LEFTPADDING",(0,0),(0,-1),0)]))
        story.append(t)

    story.append(Paragraph("pri\u010dom financovan\u00e1 \u010diastka bude pouk\u00e1zan\u00e1 Pred\u00e1vaj\u00facemu na uveden\u00fd \u00fa\u010det.", it_sty))
    story.append(hr(True))

    story.append(Paragraph("3. Pr\u00e1va a povinnosti zmluvn\u00fdch str\u00e1n", sekcia))
    story.append(hr())
    for p in [
        "3.1 Sprostredkovate\u013e sa zav\u00e4zuje kona\u0165 s odbornou starostlivos\u0165ou a dodr\u017eova\u0165 pokyny Pred\u00e1vaj\u00faceho.",
        "3.2 Pred\u00e1vaj\u00faci sa zav\u00e4zuje: akt\u00edvne spolupracova\u0165 so Sprostredkovate\u013eom, poskytova\u0165 aktu\u00e1lne inform\u00e1cie, oznamova\u0165 skuto\u010dnosti ovplyv\u0148uj\u00face uzavretie k\u00fapnej zmluvy.",
        "3.3 Pred\u00e1vaj\u00faci prehlasuje, \u017ee je v\u00fdlu\u010dn\u00fdm vlastn\u00edkom motorov\u00e9ho vozidla.",
        "3.4 Zmluvn\u00e9 strany sa zav\u00e4zuj\u00fa zachov\u00e1va\u0165 ml\u010danlipos\u0165 o obsahu tejto zmluvy.",
    ]:
        story.append(Paragraph(p, normal))
    story.append(hr(True))

    story.append(Paragraph("4. Z\u00e1vere\u010dn\u00e9 ustanovenia", sekcia))
    story.append(hr())
    for p in [
        "4.1 Zmeny a dodatky k tejto zmluve mo\u017eno vykona\u0165 len p\u00edsomnou formou so s\u00fahlasom oboch str\u00e1n.",
        "4.3 Zmluva nadob\u00fada platnos\u0165 a \u00fa\u010dinnos\u0165 d\u0148om jej podpisu v\u0161etk\u00fdmi stranami.",
        "4.4 Zmluvn\u00e9 strany vyhlasuj\u00fa, \u017ee zmluvu uzavreli slobodne, pravdivo, bez n\u00e1tlaku a nie v tiesni.",
    ]:
        story.append(Paragraph(p, normal))

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(f"V {miesto} d\u0148a {datum}", normal))
    story.append(Spacer(1, 10*mm))

    import io as _io, base64 as _b64
    _name_map = {
        'Sprostredkovate\u013e': company['name'],
        'Pred\u00e1vaj\u00faci': predavajuci_meno,
        'Kupuj\u00faci': kupujuci_meno,
    }
    sig_cells = []
    name_cells = []
    for _role in ['Sprostredkovate\u013e', 'Pred\u00e1vaj\u00faci', 'Kupuj\u00faci']:
        _key = _role.lower()
        for _c,_r in [(" ","_"),("\u00e1","a"),("\u00ed","i"),("\u00e9","e"),("\u00fa","u"),("\u013e","l"),("\u0161","s"),("\u010d","c"),("\u0165","t"),("\u017e","z")]:
            _key = _key.replace(_c,_r)
        _sig_data = (sig_images or {}).get(_key)
        _person_name = _name_map.get(_role, "")
        if _sig_data:
            try:
                _raw = _b64.b64decode(_sig_data.split(",")[-1])
                _img = RLImage(_io.BytesIO(_raw), width=45*mm, height=14*mm)
                sig_cells.append(_img)
            except:
                sig_cells.append(Paragraph("__________________________", pod_sty))
        else:
            sig_cells.append(Paragraph("__________________________", pod_sty))
        name_cells.append(Paragraph(f"{_role}<br/><font size=\'8\'>{_person_name}</font>", pod_sty))
    pod_data = [sig_cells, name_cells]
    t = Table(pod_data, colWidths=[56*mm, 56*mm, 56*mm])
    t.setStyle(TableStyle([
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,1),(-1,1),2),
    ]))
    story.append(t)

    doc.build(story)
    print("OK")

if __name__ == "__main__":
    data = json.loads(sys.argv[1])
    generate_pdf(**data)
