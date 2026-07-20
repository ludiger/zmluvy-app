# Generátor zmlúv — autazababku

## Inštalácia a spustenie

### 1. Požiadavky
- Python 3.10+
- pip

### 2. Inštalácia
```bash
pip install -r requirements.txt
```

### 3. Nastavenie API kľúča
Nastav Anthropic API kľúč (potrebný pre čítanie dokladov):
```bash
# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows
set ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Spustenie
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Aplikácia beží na: **http://localhost:8000**

---

## Funkcie
- ✅ Nahrávanie dokladov (OP predná/zadná, screenshoty)
- ✅ AI automatické vyčítanie údajov z dokladov
- ✅ Vyhľadávanie firiem podľa IČO (ORSR/RPO register)
- ✅ Uloženie predávajúcich a kupujúcich pre opakované použitie
- ✅ Podpora fyzických osôb aj firiem
- ✅ 3 sprostredkovateľské firmy (stability, autazababku, Finlife)
- ✅ Generovanie PDF zmluvy s logom
- ✅ Automatické stiahnutie PDF

## Nasadenie na server (Render.com — zadarmo)
1. Nahraj projekt na GitHub
2. Vytvor nový Web Service na render.com
3. Nastav Environment Variable: `ANTHROPIC_API_KEY`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
