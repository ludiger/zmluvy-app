import sys, json

def generate_pdf_bezucelova(company_id, dlznik_meno, dlznik_datum, dlznik_adresa, dlznik_op,
                             suma, miesto, datum, output_path,
                             logo_path=None, sig_images=None,
                             dlznik_firma=None, dlznik_ico=None, dlznik_dic=None,
                             dlznik_firma_sidlo=None, dlznik_iban=None,
                             vozidlo=None, vin=None,
                             company_name=None, company_sidlo=None, company_ico=None, company_dic=None,
                             **kwargs):

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units    import mm
    from reportlab.lib          import colors
    from reportlab.platypus     import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                        TableStyle, HRFlowable, Image as RLImage)
    from reportlab.lib.styles   import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums    import TA_CENTER, TA_LEFT, TA_JUSTIFY

    companies = {
        "stability":   {"name":"stability s. r. o.",   "sidlo":"Nábrežie mládeže 569/81, 949 12 Nitra","ico":"53392663","dic":"2121373353"},
        "autazababku": {"name":"autazababku s. r. o.","sidlo":"Nábrežie mládeže 569/81, 949 01 Nitra","ico":"57364508","dic":"2122716079"},
        "finlife":     {"name":"Finlife s. r. o.",    "sidlo":"Nábrežie mládeže 569/81, 949 01 Nitra","ico":"56332441","dic":"2122276574"},
    }
    company = companies.get(company_id, companies["stability"])
    if company_name: company["name"]  = company_name
    if company_sidlo: company["sidlo"] = company_sidlo
    if company_ico:  company["ico"]   = company_ico
    if company_dic:  company["dic"]   = company_dic

    DARK  = colors.HexColor("#2d3441")
    GRAY  = colors.HexColor("#555555")
    LGRAY = colors.HexColor("#cccccc")

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            topMargin=18*mm, bottomMargin=18*mm,
                            leftMargin=20*mm, rightMargin=20*mm)

    def sty(name, **kw):
        base = getSampleStyleSheet()["Normal"]
        return ParagraphStyle(name, parent=base, **kw)

    normal  = sty("n",  fontSize=9,  leading=13, textColor=GRAY, alignment=TA_JUSTIFY, spaceBefore=2*mm)
    bold    = sty("b",  fontSize=9,  leading=13, textColor=DARK, fontName="Helvetica-Bold")
    sekcia  = sty("s",  fontSize=10, leading=13, textColor=DARK, fontName="Helvetica-Bold", spaceBefore=4*mm, spaceAfter=1*mm)
    poz     = sty("pz", fontSize=8,  leading=11, textColor=GRAY, fontName="Helvetica-Oblique")
    pod_sty = sty("ps", size=9, alignment=TA_CENTER, spaceBefore=2*mm)

    def hr(thick=False):
        return HRFlowable(width="100%", thickness=2 if thick else 0.5,
                          color=DARK if thick else LGRAY, spaceAfter=2*mm, spaceBefore=1*mm)

    def blok(title, rows):
        story.append(Paragraph(title, bold))
        for label, val in rows:
            if val:
                story.append(Paragraph(f"<b>{label}</b>&nbsp;&nbsp;{val}", normal))
        story.append(Spacer(1, 1*mm))

    story = []

    # Logo
    if logo_path:
        try:
            story.append(RLImage(logo_path, width=50*mm, height=12*mm))
            story.append(Spacer(1, 4*mm))
        except: pass

    # Title
    story.append(Paragraph("ZMLUVA O BEZÚČELOVEJ PÔŽIČKE", sty("t", fontSize=14,
        fontName="Helvetica-Bold", textColor=DARK, alignment=TA_CENTER, spaceBefore=2*mm, spaceAfter=2*mm)))
    story.append(Paragraph(
        "uzatvorená podľa § 657 a nasl. Občianskeho zákonníka č. 40/1964 Zb. v platnom znení",
        sty("sub", fontSize=8, alignment=TA_CENTER, textColor=GRAY, spaceAfter=4*mm)))
    story.append(hr(True))

    story.append(Paragraph("1. Zmluvné strany", sekcia))
    story.append(hr())

    blok("Veriteľ (Sprostredkovateľ)", [
        ("Obchodné meno:", company["name"]),
        ("Sídlo:", company["sidlo"]),
        ("IČO:", company["ico"]),
        ("DIČ:", company["dic"]),
    ])
    story.append(Paragraph("(ďalej len Veriteľ)", poz))
    story.append(Spacer(1, 3*mm))

    blok("Dlžník", [
        ("Meno:", dlznik_meno),
        ("Dátum narodenia:", dlznik_datum),
        ("Adresa:", dlznik_adresa),
        ("OP:", dlznik_op),
        ("IBAN:", dlznik_iban),
        ("Firma:", dlznik_firma),
        ("IČO:", dlznik_ico),
        ("DIČ:", dlznik_dic),
        ("Sídlo firmy:", dlznik_firma_sidlo),
    ])
    story.append(Paragraph("(ďalej len Dlžník)", poz))
    story.append(hr(True))

    story.append(Paragraph("2. Predmet zmluvy", sekcia))
    story.append(hr())
    story.append(Paragraph(
        f"Veriteľ poskytuje Dlžníkovi bezúčelovú pôžičku vo výške <b>{suma} EUR</b>. "
        f"Dlžník sa zaväzuje vrátiť pôžičku Veriteľovi za podmienok dohodnutých v tejto zmluve.",
        normal))
    if vozidlo:
        story.append(Paragraph(f"<b>Vozidlo:</b>&nbsp;&nbsp;{vozidlo}", normal))
    if vin:
        story.append(Paragraph(f"<b>VIN:</b>&nbsp;&nbsp;{vin}", normal))
    story.append(hr(True))

    story.append(Paragraph("3. Podmienky pôžičky", sekcia))
    story.append(hr())
    for p in [
        "3.1 Pôžička je poskytnutá ako bezúčelová, t. j. Dlžník nie je povinný uvádzať účel použitia finančných prostriedkov.",
        "3.2 Dlžník sa zaväzuje vrátiť pôžičku v lehote a spôsobom dohodnutým zmluvnými stranami.",
        "3.3 Zmluvné strany sa dohodli, že pôžička je bezúročná, pokiaľ nie je písomne dohodnuté inak.",
        "3.4 Dlžník je povinný informovať Veriteľa o akýchkoľvek okolnostiach ovplyvňujúcich schopnosť splácania.",
    ]:
        story.append(Paragraph(p, normal))
    story.append(hr(True))

    story.append(Paragraph("4. Záverečné ustanovenia", sekcia))
    story.append(hr())
    for p in [
        "4.1 Táto zmluva nadobúda platnosť a účinnosť dňom jej podpisu oboma zmluvnými stranami.",
        "4.2 Zmeny a doplnky tejto zmluvy je možné vykonať len písomnou formou so súhlasom oboch zmluvných strán.",
        "4.3 Zmluvné strany vyhlasujú, že si zmluvu prečítali, jej obsahu rozumejú a uzatvárajú ju slobodne, vážne a bez nátlaku.",
    ]:
        story.append(Paragraph(p, normal))

    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(f"V {miesto} dňa {datum}", normal))
    story.append(Spacer(1, 10*mm))

    # Signature section
    import io as _io, base64 as _b64
    _name_map = {
        'Sprostredkovateľ': company['name'],
        'Dlžník': dlznik_meno,
    }
    sig_cells  = []
    name_cells = []
    for _role in ['Sprostredkovateľ', 'Dlžník']:
        _key = _role.lower()
        for _c,_r in [(" ","_"),("á","a"),("í","i"),("é","e"),("ú","u"),("ľ","l"),("š","s"),("č","c"),("ť","t"),("ž","z")]:
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
        name_cells.append(Paragraph(f"{_role}<br/><font size='8'>{_person_name}</font>", pod_sty))
    pod_data = [sig_cells, name_cells]
    t = Table(pod_data, colWidths=[84*mm, 84*mm])
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
    generate_pdf_bezucelova(**data)
