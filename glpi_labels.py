#!/usr/bin/env python3
"""
GLPI Inventory Label Generator - Genesienne Groupe
Compatible with Brother PT-P910BT (36mm tape)
QR codes = same URL as GLPI native QR codes

USAGE:
    Tous les assets (ordinateurs + ecrans):
        python3 glpi_labels.py

    Un seul asset par son ID:
        python3 glpi_labels.py --id 3
        python3 glpi_labels.py --id 3 --type Monitor

    Plusieurs assets par ID:
        python3 glpi_labels.py --id 3,5,8,12

    Filtrer par lieu:
        python3 glpi_labels.py --lieu Andrezieux
        python3 glpi_labels.py --lieu Dunkerque

    Filtrer par type:
        python3 glpi_labels.py --type Computer
        python3 glpi_labels.py --type Monitor

    Filtrer par nom (contient):
        python3 glpi_labels.py --nom ATELIER
        python3 glpi_labels.py --nom DELL

    Combiner les filtres:
        python3 glpi_labels.py --type Computer --lieu Chambon
        python3 glpi_labels.py --type Monitor --nom DELL

    Lister les assets sans generer de PDF:
        python3 glpi_labels.py --list
        python3 glpi_labels.py --list --lieu Sicaf
"""

import requests, qrcode, io, os, sys, argparse, json, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor

# === CONFIGURATION ===
GLPI_URL = "https://genesienne.fr33.glpi-network.cloud"
APP_TOKEN = "REMPLACER_PAR_TON_APP_TOKEN"
USER_TOKEN = "REMPLACER_PAR_TON_USER_TOKEN"
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_genesienne.jpg")

# Label layout (mm)
LABEL_W = 80 * mm
LABEL_H = 36 * mm
QR_SIZE = 26 * mm
MARGIN_X = 10 * mm
MARGIN_Y = 10 * mm
GAP_Y = 4 * mm

ASSET_TYPES = {
    "Computer": {"label": "Ordinateur", "form": "front/computer.form.php"},
    "Monitor":  {"label": "Ecran",      "form": "front/monitor.form.php"},
}

# === API ===
class GLPI:
    SENSITIVE_KEYS = {
        "session_token", "token", "app_token", "user_token",
        "authorization", "app-token", "session-token", "password",
    }

    def __init__(s, rest_debug=False):
        s.tok = None
        s.rest_debug = rest_debug
        s.location_cache = {}
        s.user_cache = {}

    def _sanitize_for_log(s, value):
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                key = str(k).lower()
                if key in s.SENSITIVE_KEYS or "token" in key or "auth" in key:
                    out[k] = "***"
                else:
                    out[k] = s._sanitize_for_log(v)
            return out
        if isinstance(value, list):
            return [s._sanitize_for_log(v) for v in value]
        if isinstance(value, str):
            value = re.sub(r"(?i)(session[_-]?token\s*[=:]\s*)([^,\s\"']+)", r"\1***", value)
            value = re.sub(r"(?i)(authorization\s*[=:]\s*)([^,\s\"']+)", r"\1***", value)
            return value
        return value

    def _log_rest(s, endpoint, status, payload):
        if not s.rest_debug:
            return
        try:
            body = json.dumps(s._sanitize_for_log(payload), ensure_ascii=True)
        except Exception:
            body = str(s._sanitize_for_log(payload))
        print(f"[REST] {endpoint} -> HTTP {status}")
        print(f"       {body}")

    def start(s):
        r = requests.get(f"{GLPI_URL}/apirest.php/initSession",
            headers={"App-Token": APP_TOKEN, "Authorization": f"user_token {USER_TOKEN}"})
        r.raise_for_status()
        body = r.json()
        s._log_rest("initSession", r.status_code, body)
        s.tok = body["session_token"]
        print("[OK] Session GLPI")
    def _h(s): return {"App-Token": APP_TOKEN, "Session-Token": s.tok}

    def get_all(s, ep):
        out, start = [], 0
        while True:
            r = requests.get(f"{GLPI_URL}/apirest.php/{ep}", headers=s._h(),
                params={"range": f"{start}-{start+49}", "sort": "name", "order": "ASC"})
            if r.status_code in (200, 206):
                s._log_rest(f"{ep}?range={start}-{start+49}", r.status_code, r.json())
            else:
                s._log_rest(f"{ep}?range={start}-{start+49}", r.status_code, r.text)
            if r.status_code not in (200, 206): break
            b = r.json()
            if not b: break
            out.extend(b)
            if r.status_code == 200: break
            start += 50
        print(f"  {ep}: {len(out)}"); return out

    def get_one(s, ep, item_id):
        r = requests.get(f"{GLPI_URL}/apirest.php/{ep}/{item_id}", headers=s._h())
        r.raise_for_status()
        body = r.json()
        s._log_rest(f"{ep}/{item_id}", r.status_code, body)
        return body

    def get_location_name(s, location_id):
        if not location_id:
            return ""
        if location_id in s.location_cache:
            return s.location_cache[location_id]
        try:
            item = s.get_one("Location", location_id)
            name = item.get("completename") or item.get("name") or ""
        except Exception:
            name = ""
        s.location_cache[location_id] = name
        return name

    def get_user_name(s, user_id):
        if not user_id:
            return ""
        if user_id in s.user_cache:
            return s.user_cache[user_id]
        try:
            item = s.get_one("User", user_id)
            fullname = f"{(item.get('firstname') or '').strip()} {(item.get('realname') or '').strip()}".strip()
            name = fullname or item.get("name") or ""
        except Exception:
            name = ""
        s.user_cache[user_id] = name
        return name

    def stop(s):
        try:
            r = requests.get(f"{GLPI_URL}/apirest.php/killSession", headers=s._h())
            s._log_rest("killSession", r.status_code, r.text)
        except: pass

# === QR ===
def make_qr(url):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
    q.add_data(url); q.make(fit=True)
    img = q.make_image(fill_color="black", back_color="white").resize((300, 300))
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return ImageReader(buf)

# === LABEL ===
def draw_label(c, x, y, a, logo):
    c.setStrokeColor(HexColor("#CCCCCC")); c.setLineWidth(0.5)
    c.roundRect(x, y, LABEL_W, LABEL_H, 2*mm)
    sx = x + 3*mm + QR_SIZE + 2*mm
    c.setStrokeColor(HexColor("#E0E0E0")); c.setLineWidth(0.3)
    c.line(sx, y+3*mm, sx, y+LABEL_H-3*mm)
    c.drawImage(make_qr(a["url"]), x+3*mm, y+(LABEL_H-QR_SIZE)/2, QR_SIZE, QR_SIZE)
    tx = sx + 3*mm
    if logo and os.path.exists(logo):
        lh = 9*mm; lw = lh * 2000/1444
        c.drawImage(logo, x+LABEL_W-lw-2*mm, y+LABEL_H-lh-1*mm, lw, lh,
                    preserveAspectRatio=True, mask="auto")
    c.setFont("Helvetica-Bold", 9); c.setFillColor(HexColor("#000000"))
    nm = a["name"][:17]+"…" if len(a["name"])>18 else a["name"]
    c.drawString(tx, y+LABEL_H-10*mm, nm)
    c.setFont("Helvetica", 5.5); c.setFillColor(HexColor("#666666"))
    c.drawString(tx, y+LABEL_H-14*mm, a["type_label"])
    c.setFont("Helvetica-Bold", 6.5); c.setFillColor(HexColor("#333333"))
    sn = a.get("serial","N/A") or "N/A"
    c.drawString(tx, y+LABEL_H-19.5*mm, f"S/N: {sn[:20]}")
    loc = a.get("location","") or ""
    if loc:
        c.setFont("Helvetica", 6); c.setFillColor(HexColor("#1B3A5C"))
        c.drawString(tx, y+LABEL_H-24*mm, loc[:20])
    inv = a.get("otherserial","") or ""
    if inv:
        c.setFont("Helvetica", 5.5); c.setFillColor(HexColor("#999999"))
        c.drawString(tx, y+3*mm, f"Inv: {inv}")
    c.setFillColor(HexColor("#000000"))

# === PDF ===
def make_pdf(assets, path, logo):
    c = canvas.Canvas(path, pagesize=A4)
    pw, ph = A4
    cols = int((pw - 2*MARGIN_X) // LABEL_W)
    rows = int((ph - 2*MARGIN_Y) // (LABEL_H + GAP_Y))
    per_page = cols * rows
    pages = -(-len(assets)//per_page)
    print(f"\n[PDF] {cols}x{rows} = {per_page}/page, {len(assets)} etiquette(s), {pages} page(s)")
    for i, a in enumerate(assets):
        pi = i % per_page
        if i > 0 and pi == 0: c.showPage()
        col, row = pi % cols, pi // cols
        draw_label(c, MARGIN_X+col*LABEL_W, ph-MARGIN_Y-(row+1)*(LABEL_H+GAP_Y), a, logo)
    c.save(); print(f"[OK] {path}")

# === ITEM TO ASSET ===
def item_to_asset(item, type_key, glpi=None):
    t = ASSET_TYPES[type_key]
    location = item.get("completename") or item.get("locations_name") or ""
    if not location and glpi is not None:
        raw_loc_id = item.get("locations_id", item.get("location_id", ""))
        try:
            loc_id = int(raw_loc_id)
        except (TypeError, ValueError):
            loc_id = 0
        if loc_id > 0:
            location = glpi.get_location_name(loc_id)

    user_name = item.get("users_name") or item.get("user_name") or ""
    if not user_name and glpi is not None:
        raw_user_id = item.get("users_id", item.get("user_id", ""))
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            user_id = 0
        if user_id > 0:
            user_name = glpi.get_user_name(user_id)

    return {
        "id": item["id"],
        "name": item.get("name", "Sans nom"),
        "serial": item.get("serial", ""),
        "otherserial": item.get("otherserial", ""),
        "type_label": t["label"],
        "location": location,
        "user_name": user_name,
        "url": f"{GLPI_URL}/{t['form']}?id={item['id']}",
    }

# === FILTERS ===
def apply_filters(assets, args):
    filtered = assets
    if args.lieu:
        filtered = [a for a in filtered if args.lieu.lower() in (a.get("location","") or "").lower()]
    if args.nom:
        filtered = [a for a in filtered if args.nom.lower() in (a.get("name","") or "").lower()]
    if args.user:
        filtered = [a for a in filtered if args.user.lower() in (a.get("user_name", "") or "").lower()]
    return filtered

# === LIST MODE ===
def print_asset_list(assets):
    print(f"\n{'ID':>5}  {'Type':<12} {'Nom':<22} {'S/N':<18} {'Lieu':<15} {'Utilisateur':<18}")
    print("-" * 100)
    for a in assets:
        print(f"{a['id']:>5}  {a['type_label']:<12} {a['name']:<22} {(a.get('serial','') or 'N/A'):<18} {(a.get('location','') or ''):<15} {(a.get('user_name','') or ''):<18}")
    print(f"\n  Total: {len(assets)} asset(s)")

# === MAIN ===
def main():
    parser = argparse.ArgumentParser(description="GLPI Label Generator - Genesienne Groupe")
    parser.add_argument("--id", type=str, help="ID(s) d'asset GLPI, separés par des virgules (ex: 3 ou 3,5,8)")
    parser.add_argument("--type", type=str, choices=["Computer", "Monitor"], help="Filtrer par type")
    parser.add_argument("--lieu", type=str, help="Filtrer par lieu (contient)")
    parser.add_argument("--nom", type=str, help="Filtrer par nom (contient)")
    parser.add_argument("--user", type=str, help="Filtrer par utilisateur (contient)")
    parser.add_argument("--rest-debug", action="store_true", help="Afficher les reponses REST sanitisees")
    parser.add_argument("--list", action="store_true", help="Lister les assets sans generer de PDF")
    parser.add_argument("--output", "-o", type=str, help="Nom du fichier PDF de sortie")
    args = parser.parse_args()

    logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None

    # --- DEMO MODE ---
    if "REMPLACER" in APP_TOKEN:
        print("\n" + "="*55)
        print("  CONFIGURATION REQUISE")
        print("="*55)
        print("\n  1. APP_TOKEN: Configuration > Generale > API")
        print("     '+ Ajouter un client API' > copie le jeton")
        print("\n  2. USER_TOKEN: Ton nom > Preferences")
        print("     'Jeton API distant' > Regenerer > copie")
        print("\n" + "="*55)
        print("\n[DEMO] Generation avec donnees fictives...\n")
        demo = [
            {"id":3,"name":"Automatisme-2","serial":"JXY51X2","type_label":"Ordinateur",
             "location":"Andrezieux","user_name":"Admin GLPI","otherserial":"",
             "url":f"{GLPI_URL}/front/computer.form.php?id=3"},
            {"id":5,"name":"PC-BUREAU-DG","serial":"ABC123DEF456","type_label":"Ordinateur",
             "location":"Chambon","user_name":"Marie Durand","otherserial":"INV-2024-001",
             "url":f"{GLPI_URL}/front/computer.form.php?id=5"},
            {"id":12,"name":"DELL-U2722D","serial":"CN0F5XYZ789","type_label":"Ecran",
             "location":"Chambon","user_name":"Atelier","otherserial":"INV-2024-012",
             "url":f"{GLPI_URL}/front/monitor.form.php?id=12"},
            {"id":8,"name":"PC-ATELIER-01","serial":"HJK789LMN012","type_label":"Ordinateur",
             "location":"Sicaf","user_name":"Atelier","otherserial":"",
             "url":f"{GLPI_URL}/front/computer.form.php?id=8"},
            {"id":15,"name":"ECRAN-COMPTA-01","serial":"MNO456PQR789","type_label":"Ecran",
             "location":"Andrezieux","user_name":"Compta","otherserial":"INV-2024-015",
             "url":f"{GLPI_URL}/front/monitor.form.php?id=15"},
            {"id":22,"name":"PC-DUNKERQUE-01","serial":"RST012UVW345","type_label":"Ordinateur",
             "location":"Dunkerque","user_name":"Dunkerque","otherserial":"",
             "url":f"{GLPI_URL}/front/computer.form.php?id=22"},
            {"id":7,"name":"PRECISION-7730","serial":"9XK4W53","type_label":"Ordinateur",
             "location":"Chambon","user_name":"Informatique","otherserial":"INV-2024-003",
             "url":f"{GLPI_URL}/front/computer.form.php?id=7"},
            {"id":20,"name":"DELL-P2422H","serial":"FN0R2ABC123","type_label":"Ecran",
             "location":"Dunkerque","user_name":"Dunkerque","otherserial":"",
             "url":f"{GLPI_URL}/front/monitor.form.php?id=20"},
        ]
        # Apply filters on demo data
        if args.type:
            tl = ASSET_TYPES[args.type]["label"]
            demo = [a for a in demo if a["type_label"] == tl]
        if args.id:
            ids = [int(x.strip()) for x in args.id.split(",")]
            demo = [a for a in demo if a["id"] in ids]
        demo = apply_filters(demo, args)

        if args.list:
            print_asset_list(demo); return
        if not demo:
            print("[!] Aucun asset ne correspond aux filtres"); return
        out = args.output or os.path.join(os.path.dirname(os.path.abspath(__file__)), "glpi_etiquettes_DEMO.pdf")
        make_pdf(demo, out, logo)
        return

    # --- PRODUCTION MODE ---
    print(f"\n  GLPI Label Generator - Genesienne Groupe")
    print(f"  Instance: {GLPI_URL}\n")

    g = GLPI(rest_debug=args.rest_debug)
    try:
        g.start()

        # Determine which types to fetch
        types_to_fetch = [args.type] if args.type else list(ASSET_TYPES.keys())

        # Specific IDs requested
        if args.id:
            ids = [int(x.strip()) for x in args.id.split(",")]
            assets = []
            for item_id in ids:
                found = False
                for type_key in types_to_fetch:
                    try:
                        item = g.get_one(type_key, item_id)
                        assets.append(item_to_asset(item, type_key, g))
                        print(f"  [OK] {type_key} #{item_id}: {item.get('name','?')}")
                        found = True
                        break
                    except:
                        continue
                if not found:
                    print(f"  [!] ID {item_id} non trouve")
        else:
            # Fetch all
            assets = []
            for type_key in types_to_fetch:
                for item in g.get_all(type_key):
                    assets.append(item_to_asset(item, type_key, g))

        # Apply filters
        assets = apply_filters(assets, args)
        assets.sort(key=lambda a: a["name"])

        if not assets:
            print("[!] Aucun asset ne correspond aux filtres"); return

        # List mode
        if args.list:
            print_asset_list(assets); return

        # Generate PDF
        out = args.output or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "glpi_etiquettes.pdf")
        make_pdf(assets, out, logo)

    finally:
        g.stop()


if __name__ == "__main__":
    main()
