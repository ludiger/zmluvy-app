import os, json, uuid, base64, asyncio, datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import anthropic

app = FastAPI(title="Zmluvy App")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE   = Path(__file__).parent
STATIC = BASE / "static"
DATA   = BASE / "data"
SESSIONS_DIR = DATA / "sessions"
DATA.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
LOGO_PATH = str(STATIC / "logo.png")

COMPANIES = {
    "stability":   {"name":"stability s. r. o.",  "sidlo":"Nábrežie mládeže 569/81, 949 12 Nitra","ico":"53392663","dic":"2121373353"},
    "autazababku": {"name":"autazababku s. r. o.","sidlo":"Nábrežie mládeže 569/81, 949 01 Nitra","ico":"57364508","dic":"2122716079"},
    "finlife":     {"name":"Finlife s. r. o.",    "sidlo":"Nábrežie mládeže 569/81, 949 01 Nitra","ico":"56332441","dic":"2122276574"},
}

GIST_ID    = os.environ.get("GIST_ID",    "5f7895bf5cc2d738463b2072cb1b6441")
GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
if not GIST_TOKEN:
    _sf = BASE / ".gist_token"
    if _sf.exists():
        GIST_TOKEN = _sf.read_text().strip()

def _gist_get():
    import urllib.request
    req = urllib.request.Request(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "User-Agent": "zmluvy-app"}
    )
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read())

def _gist_patch(files):
    import urllib.request
    payload = json.dumps({"files": {k: ({"content": v} if v is not None else None) for k,v in files.items()}}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/gists/{GIST_ID}",
        data=payload, method="PATCH",
        headers={"Authorization": f"token {GIST_TOKEN}", "Content-Type": "application/json", "User-Agent": "zmluvy-app"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()

def _slug(role):
    s = role.lower()
    for c,r in [(" ","_"),("á","a"),("í","i"),("é","e"),("ú","u"),("ľ","l"),("š","s"),("č","c"),("ť","t"),("ž","z")]:
        s = s.replace(c,r)
    return s

# ─── PERSONS ──────────────────────────────────────────────────────────────────
PERSONS_FILE = DATA / "persons.json"

def load_persons():
    try:
        d = _gist_get()
        c = d["files"].get("persons.json", {}).get("content", "")
        if c:
            return json.loads(c)
    except Exception as e:
        print(f"persons gist error: {e}")
    if PERSONS_FILE.exists():
        return json.loads(PERSONS_FILE.read_text(encoding="utf-8"))
    return {"pred":[],"kup":[],"dlz":[]}

def save_persons(data):
    PERSONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        _gist_patch({"persons.json": json.dumps(data, ensure_ascii=False, indent=2)})
    except Exception as e:
        print(f"persons gist save error: {e}")

@app.get("/api/persons")
def get_persons():
    return load_persons()

@app.post("/api/persons/{grp}")
async def save_person(grp: str, request: Request):
    person = await request.json()
    data = load_persons()
    key = {"p":"pred","k":"kup","b":"dlz"}.get(grp, grp)
    if key not in data:
        data[key] = []
    if not person.get("id"):
        person["id"] = str(uuid.uuid4())
    existing = next((i for i,p in enumerate(data[key]) if p.get("id") == person.get("id")), -1)
    if existing >= 0:
        data[key][existing] = person
    else:
        data[key].append(person)
    save_persons(data)
    return {"ok": True, "id": person["id"]}

@app.delete("/api/persons/{grp}/{pid}")
def delete_person(grp: str, pid: str):
    data = load_persons()
    key = {"p":"pred","k":"kup","b":"dlz"}.get(grp, grp)
    if key in data:
        data[key] = [p for p in data[key] if p.get("id") != pid and p.get("meno") != pid]
    save_persons(data)
    return {"ok": True}

# ─── SESSIONS INDEX ───────────────────────────────────────────────────────────
def load_sessions_index():
    try:
        d = _gist_get()
        c = d["files"].get("sessions_index.json", {}).get("content", "")
        if c:
            return json.loads(c)
    except Exception as e:
        print(f"index gist error: {e}")
    return []

def save_sessions_index(index):
    try:
        _gist_patch({"sessions_index.json": json.dumps(index, ensure_ascii=False, indent=2)})
    except Exception as e:
        print(f"index gist save error: {e}")

# ─── SESSION ──────────────────────────────────────────────────────────────────
def load_session(token):
    f = SESSIONS_DIR / f"{token}.json"
    local = None
    if f.exists():
        local = json.loads(f.read_text(encoding="utf-8"))
    try:
        d = _gist_get()
        fname = f"session_{token}.json"
        c = d["files"].get(fname, {}).get("content", "")
        if c:
            gs = json.loads(c)
            if local:
                for ls in local.get("signers", []):
                    for gss in gs.get("signers", []):
                        if ls["role"] == gss["role"]:
                            ls["signed"] = gss["signed"]
                local["pdf_in_gist"] = gs.get("pdf_in_gist", False)
                f.write_text(json.dumps(local, ensure_ascii=False, indent=2), encoding="utf-8")
                return local
            else:
                f.write_text(c, encoding="utf-8")
                return gs
    except Exception as e:
        print(f"session load error: {e}")
    return local

def save_session(token, data):
    f = SESSIONS_DIR / f"{token}.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ─── AI EXTRACT ───────────────────────────────────────────────────────────────
@app.post("/api/extract")
async def extract_from_images(files: list[UploadFile] = File(...)):
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        content = []
        for f in files:
            raw = await f.read()
            b64 = base64.b64encode(raw).decode()
            mt = f.content_type or "image/jpeg"
            if mt == "application/pdf":
                content.append({"type":"document","source":{"type":"base64","media_type":mt,"data":b64}})
            else:
                content.append({"type":"image","source":{"type":"base64","media_type":mt,"data":b64}})
        content.append({"type":"text","text":(
            'Extrahuj z dokladov tieto údaje ako JSON:\n{"meno":"","datum":"DD.MM.YYYY","adresa":"","op":"","iban":""}\n'
            'Vráť IBA JSON bez iného textu.'
        )})
        resp = client.messages.create(model="claude-sonnet-4-5", max_tokens=500,
            messages=[{"role":"user","content":content}])
        text = resp.content[0].text.strip().replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e:
        raise HTTPException(500, f"Chyba extrakcie: {e}")

# ─── GENERATE PDF ─────────────────────────────────────────────────────────────
@app.post("/api/generate")
async def generate(request: Request):
    data = await request.json()
    out = str(SESSIONS_DIR / f"prev_{uuid.uuid4().hex[:8]}.pdf")
    data["output_path"] = out
    data["logo_path"]   = LOGO_PATH
    data["sig_images"]  = {}
    from pdf_generator import generate_pdf
    generate_pdf(**data)
    return FileResponse(out, media_type="application/pdf", filename="zmluva.pdf")

@app.post("/api/generate/bezucelova")
async def generate_bez(request: Request):
    data = await request.json()
    out = str(SESSIONS_DIR / f"prev_{uuid.uuid4().hex[:8]}.pdf")
    data["output_path"] = out
    data["logo_path"]   = LOGO_PATH
    data["sig_images"]  = {}
    from pdf_generator_bezucelova import generate_pdf_bezucelova
    generate_pdf_bezucelova(**data)
    return FileResponse(out, media_type="application/pdf", filename="bezucelova.pdf")

# ─── SIGN CREATE ──────────────────────────────────────────────────────────────
@app.post("/api/sign/create")
async def create_sign_session(request: Request):
    body  = await request.json()
    token = str(uuid.uuid4())
    ztyp  = body.get("ztyp","kup")
    data  = body.get("data",{})

    if ztyp == "bez":
        signers = [
            {"role":"Dlžník",          "name":data.get("dlznik_meno","Dlžník"),          "signed":False},
            {"role":"Sprostredkovateľ","name":data.get("company_name","Sprostredkovateľ"),"signed":False},
        ]
        label = f"Bezúčelová — {data.get('dlznik_meno','?')} — {data.get('suma','?')} EUR"
    else:
        signers = [
            {"role":"Predávajúci",     "name":data.get("predavajuci_meno","Predávajúci"),"signed":False},
            {"role":"Kupujúci",        "name":data.get("kupujuci_meno","Kupujúci"),      "signed":False},
            {"role":"Sprostredkovateľ","name":data.get("company_name","Sprostredkovateľ"),"signed":False},
        ]
        label = f"Zmluva — {data.get('predavajuci_meno','?')} / {data.get('kupujuci_meno','?')} — {data.get('vozidlo','?')}"

    links = {s["role"]: f"/sign/{token}/{_slug(s['role'])}" for s in signers}
    session = {"token":token,"ztyp":ztyp,"signers":signers,"data":data,
               "created":datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}
    save_session(token, session)

    async def _persist():
        try:
            gs = {k:v for k,v in session.items() if k!="signers"}
            gs["signers"] = [{"role":s["role"],"name":s["name"],"signed":False} for s in signers]
            _gist_patch({f"session_{token}.json": json.dumps(gs, ensure_ascii=False, indent=2)})
        except Exception as e:
            print(f"session gist create error: {e}")
    asyncio.create_task(_persist())

    for attempt in range(3):
        try:
            index = load_sessions_index()
            index = [e for e in index if e["token"] != token]
            index.insert(0,{"token":token,"ztyp":ztyp,"label":label,"draft":False,
                            "created":session["created"],"all_signed":False,
                            "signers":[{"role":s["role"],"name":s["name"],"signed":False} for s in signers]})
            save_sessions_index(index[:50])
            break
        except Exception as e:
            print(f"index save attempt {attempt+1}: {e}")
            await asyncio.sleep(0.5)

    return {"token":token,"links":links,"signers":signers}

# ─── SIGN SUBMIT ──────────────────────────────────────────────────────────────
@app.post("/api/sign/{token}/submit")
async def submit_signature(token: str, request: Request):
    body = await request.json()
    role = body.get("role","")
    sig  = body.get("signature","")

    session = load_session(token)
    if not session:
        raise HTTPException(404, "Relácia nenájdená")

    for s in session["signers"]:
        if s["role"] == role:
            s["signed"] = True
            s["sig"]    = sig
            break

    all_signed = all(s["signed"] for s in session["signers"])

    if all_signed:
        signed_path = SESSIONS_DIR / f"{token}_signed.pdf"
        sig_images  = {}
        for s in session["signers"]:
            if s.get("sig"):
                sig_images[_slug(s["role"])] = s["sig"]
        data = session["data"].copy()
        data["output_path"] = str(signed_path)
        data["logo_path"]   = LOGO_PATH
        data["sig_images"]  = sig_images
        if session.get("ztyp") == "bez":
            from pdf_generator_bezucelova import generate_pdf_bezucelova as gen
        else:
            from pdf_generator import generate_pdf as gen
        gen(**data)
        session["final_pdf"] = str(signed_path)

    save_session(token, session)

    _r, _s, _all = role, sig, all_signed
    async def _bg():
        try:
            from storage_helper import gh_save as _gh_save
            # Save signature to GitHub storage (not Gist - too large over time)
            if _s:
                sig_only = _s.split(",")[-1] if "," in _s else _s
                sig_bytes = base64.b64decode(sig_only)
                _gh_save(f"sigs/{token}/{_slug(_r)}.png", sig_bytes, "sig")
            # Save session status to Gist (small JSON)
            gs = {k:v for k,v in session.items() if k!="signers"}
            gs["signers"] = [{"role":s["role"],"name":s["name"],"signed":s["signed"]} for s in session["signers"]]
            _gist_patch({f"session_{token}.json": json.dumps(gs, ensure_ascii=False, indent=2)})
            # Save signed PDF to GitHub storage
            if _all:
                sp = SESSIONS_DIR / f"{token}_signed.pdf"
                if sp.exists():
                    _gh_save(f"pdfs/{token}/signed.pdf", sp.read_bytes(), "signed")
            # Update index
            index = load_sessions_index()
            for entry in index:
                if entry["token"] == token:
                    for es in entry.get("signers",[]):
                        for ss in session["signers"]:
                            if es["role"] == ss["role"]:
                                es["signed"] = ss["signed"]
                    entry["all_signed"] = _all
                    break
            save_sessions_index(index)
        except Exception as e:
            print(f"bg save error: {e}")
    asyncio.create_task(_bg())

    return {"ok":True,"all_signed":all_signed,"token":token}

# ─── SIGN GET ─────────────────────────────────────────────────────────────────
@app.get("/api/sign/{token}/download")
async def download_signed(token: str):
    session = load_session(token)
    if not session:
        raise HTTPException(404,"Relácia nenájdená")
    signed_path = SESSIONS_DIR / f"{token}_signed.pdf"

    if not signed_path.exists():
        from storage_helper import gh_load as _gh_load
        try:
            signed_bytes = _gh_load(f"pdfs/{token}/signed.pdf")
            if signed_bytes:
                signed_path.write_bytes(signed_bytes)
        except Exception as e:
            print(f"signed pdf restore error: {e}")

    if not signed_path.exists():
        from storage_helper import gh_load as _gh_load
        try:
            sig_images = {}
            for s in session.get("signers", []):
                slug = _slug(s["role"])
                sig_bytes_stored = _gh_load(f"sigs/{token}/{slug}.png")
                if sig_bytes_stored:
                    sig_images[slug] = "data:image/png;base64," + base64.b64encode(sig_bytes_stored).decode()
                    print(f"Loaded sig {slug}: {len(sig_bytes_stored)} bytes")
            if not sig_images:
                raise HTTPException(404, "Podpisy nenajdene")
            data = session["data"].copy()
            data["output_path"] = str(signed_path)
            data["logo_path"]   = LOGO_PATH
            data["sig_images"]  = sig_images
            if session.get("ztyp") == "bez":
                from pdf_generator_bezucelova import generate_pdf_bezucelova as gen
            else:
                from pdf_generator import generate_pdf as gen
            gen(**data)
            print(f"Regenerated PDF: {token[:8]}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Chyba generovania: {e}")

    if not signed_path.exists():
        raise HTTPException(404,"PDF nenajdeny")

    d = session.get("data",{})
    if session.get("ztyp") == "bez":
        name = f"Bezucelova_{(d.get('dlznik_meno','') or '').split()[-1]}"
    else:
        p = (d.get("predavajuci_meno","") or "").split()
        k = (d.get("kupujuci_meno","") or "").split()
        name = f"Zmluva_{p[-1] if p else ''}_{k[-1] if k else ''}"
    return FileResponse(str(signed_path), media_type="application/pdf", filename=f"{name}_podpisana.pdf")


@app.get("/api/sign/{token}")
def get_sign_session(token: str):
    session = load_session(token)
    if not session:
        raise HTTPException(404,"Relácia nenájdená")
    signers = [{"role":s["role"],"name":s["name"],"signed":s["signed"]} for s in session["signers"]]
    return {"token":token,"ztyp":session["ztyp"],"signers":signers,"data":session["data"]}

@app.get("/api/sign/{token}/{role_slug}")
def get_sign_role(token: str, role_slug: str):
    session = load_session(token)
    if not session:
        raise HTTPException(404,"Relácia nenájdená")
    my_role = next((s["role"] for s in session["signers"] if _slug(s["role"])==role_slug), None)
    if not my_role:
        raise HTTPException(403,"Neplatný odkaz")
    signers = [{"role":s["role"],"name":s["name"],"signed":s["signed"]} for s in session["signers"]]
    return {"token":token,"ztyp":session["ztyp"],"signers":signers,"data":session["data"],"my_role":my_role}

# ─── SESSIONS CRUD ────────────────────────────────────────────────────────────
@app.get("/api/sessions")
def list_sessions():
    return load_sessions_index()

@app.delete("/api/sessions/{token}")
async def delete_session(token: str):
    try:
        index = load_sessions_index()
        save_sessions_index([e for e in index if e["token"]!=token])
    except Exception as e:
        print(f"delete index error: {e}")
    for suf in ["",".json","_signed.pdf"]:
        if suf == ".json":
            f = SESSIONS_DIR / f"{token}{suf}"
        elif suf == "_signed.pdf":
            f = SESSIONS_DIR / f"{token}{suf}"
        else:
            continue
        if f.exists(): f.unlink()
    async def _del():
        try:
            from storage_helper import gh_delete as _gh_delete
            # Delete from Gist
            _gist_patch({f"session_{token}.json": None})
            # Delete from GitHub storage
            for s in ["predavajuci","kupujuci","sprostredkovatel","dlznik"]:
                _gh_delete(f"sigs/{token}/{s}.png")
            _gh_delete(f"pdfs/{token}/signed.pdf")
        except Exception as e:
            print(f"delete error: {e}")
    asyncio.create_task(_del())
    return {"ok":True}

# ─── DRAFTS ───────────────────────────────────────────────────────────────────
@app.post("/api/drafts/save")
async def save_draft_endpoint(request: Request):
    data  = await request.json()
    token = data.get("token") or str(uuid.uuid4())
    ztyp  = data.get("ztyp","kup")
    d     = data.get("data",{})
    if ztyp == "bez":
        label = f"Koncept — Bezúčelová — {d.get('dlznik_meno','?')} — {d.get('suma','?')} EUR"
    else:
        label = f"Koncept — Zmluva — {d.get('predavajuci_meno','?')} / {d.get('kupujuci_meno','?')} — {d.get('vozidlo','?')}"
    draft = {"token":token,"ztyp":ztyp,"label":label,"draft":True,
             "created":datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),"data":d,"signers":[]}
    (SESSIONS_DIR / f"{token}.json").write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding="utf-8")
    async def _save():
        try:
            index = load_sessions_index()
            existing = next((i for i,e in enumerate(index) if e["token"]==token),-1)
            entry = {"token":token,"ztyp":ztyp,"label":label,"draft":True,"created":draft["created"],"signers":[]}
            if existing>=0: index[existing]=entry
            else: index.insert(0,entry)
            save_sessions_index(index[:50])
            _gist_patch({f"session_{token}.json":json.dumps(draft,ensure_ascii=False,indent=2)})
        except Exception as e:
            print(f"draft save error: {e}")
    asyncio.create_task(_save())
    return {"token":token,"label":label}

@app.get("/api/drafts/{token}")
def get_draft_endpoint(token: str):
    s = load_session(token)
    if not s: raise HTTPException(404,"Koncept nenájdený")
    return s

@app.delete("/api/drafts/{token}")
async def delete_draft_endpoint(token: str):
    f = SESSIONS_DIR / f"{token}.json"
    if f.exists(): f.unlink()
    async def _del():
        try:
            index = load_sessions_index()
            save_sessions_index([e for e in index if e["token"]!=token])
            _gist_patch({f"session_{token}.json":None})
        except Exception as e:
            print(f"delete draft error: {e}")
    asyncio.create_task(_del())
    return {"ok":True}

# ─── PODPIS DOKUMENTU ─────────────────────────────────────────────────────────
try:
    import podpis_docs
    app.include_router(podpis_docs.router)
except Exception as e:
    print(f"podpis_docs not loaded: {e}")

# ─── PAGES ────────────────────────────────────────────────────────────────────
@app.get("/")
def index_page():
    return FileResponse(STATIC/"index.html")

@app.get("/sign/{token}/{role_slug}")
def sign_role_page(token:str, role_slug:str):
    return FileResponse(STATIC/"sign.html")

@app.get("/sign/{token}")
def sign_page(token:str):
    return FileResponse(STATIC/"sign.html")

@app.get("/podpis/sign/{token}")
def podpis_sign_page_route(token:str):
    return FileResponse(STATIC/"podpis_sign.html")

@app.get("/ping")
def ping():
    return {"ok":True}

@app.get("/version")
def version():
    return {"version":"2.1.0"}
