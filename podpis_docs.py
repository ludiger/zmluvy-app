"""Podpis dokumentu - embedded v zmluvy-app, pouziva pd_ prefix v Giste."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from storage_helper import gh_save, gh_load, gh_delete
from fastapi.responses import FileResponse
import os, json, uuid, asyncio, base64, datetime
from pathlib import Path

router = APIRouter()

BASE     = Path(__file__).parent
DOCS_DIR = BASE / "data" / "podpis_docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

GIST_ID    = os.environ.get("GIST_ID", "5f7895bf5cc2d738463b2072cb1b6441")
GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
if not GIST_TOKEN:
    _sf = BASE / ".gist_token"
    if _sf.exists():
        GIST_TOKEN = _sf.read_text().strip()

INDEX_FILE = "pd_documents_index.json"

# ── GIST ──────────────────────────────────────────────────────────────────────
def _gist_get():
    import urllib.request
    req = urllib.request.Request(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "User-Agent": "zmluvy-podpis"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def _gist_patch(files):
    import urllib.request
    payload = json.dumps({"files": {k: ({"content": v} if v is not None else None) for k,v in files.items()}}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/gists/{GIST_ID}",
        data=payload, method="PATCH",
        headers={"Authorization": f"token {GIST_TOKEN}",
                 "Content-Type": "application/json", "User-Agent": "zmluvy-podpis"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()

def load_index():
    try:
        d = _gist_get()
        c = d["files"].get(INDEX_FILE, {}).get("content", "")
        if c: return json.loads(c)
    except Exception as e:
        print(f"[podpis] index load error: {e}")
    return []

def save_index(index):
    try:
        _gist_patch({INDEX_FILE: json.dumps(index, ensure_ascii=False, indent=2)})
    except Exception as e:
        print(f"[podpis] index save error: {e}")

def load_doc(token):
    f = DOCS_DIR / f"{token}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    try:
        d = _gist_get()
        c = d["files"].get(f"pd_doc_{token}.json", {}).get("content", "")
        if c:
            data = json.loads(c)
            f.write_text(c, encoding="utf-8")
            return data
    except Exception as e:
        print(f"[podpis] doc load error: {e}")
    return None

def save_doc(token, data, to_gist=True):
    f = DOCS_DIR / f"{token}.json"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    f.write_text(content, encoding="utf-8")
    if to_gist:
        try:
            _gist_patch({f"pd_doc_{token}.json": content})
        except Exception as e:
            print(f"[podpis] doc save error: {e}")

# ── UPLOAD ─────────────────────────────────────────────────────────────────────
@router.post("/api/podpis/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        import fitz
    except ImportError:
        raise HTTPException(500, "PyMuPDF nie je nainštalovaný")

    token = str(uuid.uuid4())
    content = await file.read()
    if not content:
        raise HTTPException(400, "Prázdny súbor")

    pdf_path = DOCS_DIR / f"{token}.pdf"
    pdf_path.write_bytes(content)

    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise HTTPException(400, f"Neplatný PDF súbor: {e}")

    page_count = len(doc)
    sig_position = None

    # 1. Find dotted signature line in text
    for page_num in range(page_count):
        page = doc[page_num]
        page_rect = page.rect
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                txt = "".join(s["text"] for s in line["spans"]).strip()
                if (txt.count(".") > 10 or txt.count("_") > 10) and len(txt) > 10:
                    bbox = line["bbox"]
                    sig_position = {
                        "page": page_num,
                        "x": bbox[0], "y": bbox[1] - 35,
                        "width": min(bbox[2] - bbox[0], 180), "height": 30,
                        "page_width": page_rect.width, "page_height": page_rect.height,
                    }

    # 2. AI fallback on last page
    if sig_position is None:
        try:
            import anthropic as _anth
            last_page = doc[page_count - 1]
            pix = last_page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            client = _anth.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
            resp = client.messages.create(
                model="claude-sonnet-4-5", max_tokens=200,
                messages=[{"role":"user","content":[
                    {"type":"image","source":{"type":"base64","media_type":"image/png","data":img_b64}},
                    {"type":"text","text":'Najdi podpisovu ciaru. Vrat IBA JSON: {"x":0.0,"y":0.0,"width":0.0,"height":0.0} relativne suradnice 0-1. Bez textu.'}
                ]}]
            )
            rel = json.loads(resp.content[0].text.strip().replace("```json","").replace("```",""))
            pr = last_page.rect
            sig_position = {
                "page": page_count-1,
                "x": rel["x"]*pr.width, "y": rel["y"]*pr.height,
                "width": rel["width"]*pr.width, "height": rel["height"]*pr.height,
                "page_width": pr.width, "page_height": pr.height,
            }
        except Exception as e:
            print(f"[podpis] AI detection error: {e}")

    # 3. Fallback bottom right
    if sig_position is None:
        pr = doc[page_count-1].rect
        sig_position = {"page":page_count-1,"x":pr.width*0.5,"y":pr.height*0.75,
                        "width":180,"height":30,"page_width":pr.width,"page_height":pr.height}

    doc.close()

    created = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    doc_data = {
        "token": token, "filename": file.filename, "page_count": page_count,
        "sig_position": sig_position, "signed": False, "signature": None,
        "created": created,
    }
    save_doc(token, doc_data, to_gist=False)

    # Save doc + original PDF to storage in background
    _pdf_bytes = content
    async def _save_all():
        try:
            # Save original PDF to GitHub repo storage
            gh_save(f"pdfs/{token}/original.pdf", _pdf_bytes, "upload")
            # Save doc metadata to Gist
            _gist_patch({
                f"pd_doc_{token}.json": json.dumps(doc_data, ensure_ascii=False, indent=2),
            })
            # Update index
            index = load_index()
            index.insert(0, {"token":token,"filename":file.filename,"created":created,"signed":False})
            save_index(index[:50])
        except Exception as e:
            print(f"[podpis] save_all error: {e}")
    asyncio.create_task(_save_all())

    return {"token": token, "sig_position": sig_position, "page_count": page_count}

# ── PAGE IMAGE ─────────────────────────────────────────────────────────────────
@router.get("/api/podpis/doc/{token}/page/{page_num}")
def get_page_image(token: str, page_num: int):
    try:
        import fitz
    except ImportError:
        raise HTTPException(500, "PyMuPDF nie je nainštalovaný")

    pdf_path = DOCS_DIR / f"{token}.pdf"
    if not pdf_path.exists():
        try:
            b64 = _gist_get()["files"].get(f"pd_pdf_{token}.b64",{}).get("content","")
            if b64: pdf_path.write_bytes(base64.b64decode(b64))
        except: pass
    if not pdf_path.exists():
        raise HTTPException(404, "Dokument nenájdený")

    doc = fitz.open(pdf_path)
    if page_num >= len(doc):
        raise HTTPException(404, "Strana nenájdená")
    pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(2, 2))
    img_path = DOCS_DIR / f"{token}_p{page_num}.png"
    pix.save(str(img_path))
    doc.close()
    return FileResponse(img_path, media_type="image/png")

# ── DOC INFO ──────────────────────────────────────────────────────────────────
@router.get("/api/podpis/documents")
def list_documents():
    return load_index()

@router.get("/api/podpis/doc/{token}")
def get_doc(token: str):
    d = load_doc(token)
    if not d: raise HTTPException(404, "Dokument nenájdený")
    return d

@router.post("/api/podpis/doc/{token}/position")
async def update_position(token: str, request: Request):
    d = load_doc(token)
    if not d: raise HTTPException(404, "Dokument nenájdený")
    body = await request.json()
    d["sig_position"] = body.get("sig_position", d["sig_position"])
    save_doc(token, d, to_gist=False)
    return {"ok": True}

# ── SIGN ───────────────────────────────────────────────────────────────────────
@router.post("/api/podpis/doc/{token}/sign")
async def submit_signature(token: str, request: Request):
    try:
        import fitz
    except ImportError:
        raise HTTPException(500, "PyMuPDF nie je nainštalovaný")

    d = load_doc(token)
    if not d: raise HTTPException(404, "Dokument nenájdený")

    body = await request.json()
    sig_data = body.get("signature", "")
    if not sig_data: raise HTTPException(400, "Chýba podpis")

    pdf_path    = DOCS_DIR / f"{token}.pdf"
    signed_path = DOCS_DIR / f"{token}_signed.pdf"

    sig_b64  = sig_data.split(",")[-1] if "," in sig_data else sig_data
    sig_bytes = base64.b64decode(sig_b64)

    pdf_doc = fitz.open(pdf_path)
    pos = d["sig_position"]
    rect = fitz.Rect(pos["x"], pos["y"], pos["x"]+pos["width"], pos["y"]+pos["height"])
    pdf_doc[pos["page"]].insert_image(rect, stream=sig_bytes)
    pdf_doc.save(str(signed_path))
    pdf_doc.close()

    d["signature"] = sig_data
    d["signed"]    = True
    d["signed_at"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    d["final_pdf"] = str(signed_path)
    save_doc(token, d, to_gist=False)

    async def _persist():
        try:
            # Save signed PDF to GitHub repo storage
            if signed_path.exists():
                gh_save(f"pdfs/{token}/signed.pdf", signed_path.read_bytes(), "signed")
            # Save doc metadata to Gist
            _gist_patch({
                f"pd_doc_{token}.json": json.dumps(d, ensure_ascii=False, indent=2),
            })
            # Update index
            index = load_index()
            for e in index:
                if e["token"] == token:
                    e["signed"] = True
                    break
            save_index(index)
        except Exception as e:
            print(f"[podpis] persist error: {e}")
    asyncio.create_task(_persist())

    return {"ok": True, "token": token}

# ── DOWNLOAD ───────────────────────────────────────────────────────────────────
@router.get("/api/podpis/doc/{token}/download")
async def download_signed(token: str):
    try:
        import fitz
    except ImportError:
        raise HTTPException(500, "PyMuPDF nie je nainštalovaný")

    d = load_doc(token)
    if not d: raise HTTPException(404, "Dokument nenájdený")
    if not d.get("signed"): raise HTTPException(400, "Dokument nie je podpísaný")

    signed_path = DOCS_DIR / f"{token}_signed.pdf"
    if not signed_path.exists():
        try:
            b64 = _gist_get()["files"].get(f"pd_signed_{token}.b64",{}).get("content","")
            if b64: signed_path.write_bytes(base64.b64decode(b64))
        except Exception as e:
            print(f"[podpis] restore error: {e}")

    if not signed_path.exists():
        # Try to restore signed PDF from GitHub repo storage
        signed_bytes = gh_load(f"pdfs/{token}/signed.pdf")
        if signed_bytes:
            signed_path.write_bytes(signed_bytes)
        else:
            # Regenerate: load original PDF + signature
            pdf_path = DOCS_DIR / f"{token}.pdf"
            if not pdf_path.exists():
                orig_bytes = gh_load(f"pdfs/{token}/original.pdf")
                if orig_bytes:
                    pdf_path.write_bytes(orig_bytes)
            if not pdf_path.exists():
                raise HTTPException(404, "Dokument nenájdený — nahrajte a podpíšte znovu")
            sig_b64 = None
            if d.get("signature"):
                sig_b64 = d["signature"].split(",")[-1] if "," in d["signature"] else d["signature"]
            if not sig_b64:
                raise HTTPException(404, "Podpis nenájdený — podpíšte dokument znovu")
            sig_bytes = base64.b64decode(sig_b64)
            pos = d["sig_position"]
            pdf_doc = fitz.open(pdf_path)
            rect = fitz.Rect(pos["x"],pos["y"],pos["x"]+pos["width"],pos["y"]+pos["height"])
            pdf_doc[pos["page"]].insert_image(rect, stream=sig_bytes)
            pdf_doc.save(str(signed_path))
            pdf_doc.close()

    name = d.get("filename","dokument").replace(".pdf","")
    return FileResponse(str(signed_path), media_type="application/pdf", filename=f"{name}_podpisany.pdf")

# ── DELETE ──────────────────────────────────────────────────────────────────────
@router.delete("/api/podpis/doc/{token}")
async def delete_doc(token: str):
    for suffix in ["",  "_signed"]:
        f = DOCS_DIR / f"{token}{suffix}.pdf"
        if f.exists(): f.unlink()
    f = DOCS_DIR / f"{token}.json"
    if f.exists(): f.unlink()
    for f in DOCS_DIR.glob(f"{token}_p*.png"):
        f.unlink()
    index = load_index()
    save_index([e for e in index if e["token"] != token])
    async def _del():
        try:
            _gist_patch({f"pd_doc_{token}.json": None})
            gh_delete(f"pdfs/{token}/original.pdf")
            gh_delete(f"pdfs/{token}/signed.pdf")
        except: pass
    asyncio.create_task(_del())
    return {"ok": True}

# ── PERSIST PDF ────────────────────────────────────────────────────────────────
@router.post("/api/podpis/doc/{token}/persist")
async def persist_pdf(token: str):
    pdf_path = DOCS_DIR / f"{token}.pdf"
    if not pdf_path.exists():
        raise HTTPException(404, "PDF nenájdený")
    async def _save():
        try:
            _gist_patch({f"pd_pdf_{token}.b64": base64.b64encode(pdf_path.read_bytes()).decode()})
        except Exception as e:
            print(f"[podpis] persist pdf error: {e}")
    asyncio.create_task(_save())
    return {"ok": True}

# ── SIGN PAGE ──────────────────────────────────────────────────────────────────
@router.get("/podpis/sign/{token}")
def podpis_sign_page(token: str):
    return FileResponse(BASE / "static" / "podpis_sign.html")
