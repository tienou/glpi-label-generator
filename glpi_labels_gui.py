#!/usr/bin/env python3
"""
GLPI Inventory Label Generator - Genesienne Groupe
Application GUI avec CustomTkinter
"""

import customtkinter as ctk
import requests, qrcode, io, os, sys, json, threading
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor

# === PATHS ===
def get_config_dir():
    """Config in %APPDATA%/GLPI_Labels/ so it survives exe updates."""
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        d = os.path.join(appdata, "GLPI_Labels")
    else:
        d = os.path.join(os.path.expanduser("~"), ".glpi_labels")
    os.makedirs(d, exist_ok=True)
    return d

def get_app_dir():
    """Dossier de l'exe ou du script"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_DIR = get_config_dir()
CONFIG_PATH = os.path.join(CONFIG_DIR, "glpi_config.json")

# === LABEL LAYOUTS PER TAPE SIZE ===
TAPE_SIZES = {
    "36mm": {"label_w": 80, "label_h": 36, "qr_size": 26, "font_name": 9, "font_type": 5.5, "font_sn": 6.5, "font_loc": 6, "font_inv": 5.5, "logo_h": 12},
    "25mm": {"label_w": 70, "label_h": 25, "qr_size": 18, "font_name": 7.5, "font_type": 5, "font_sn": 5.5, "font_loc": 5, "font_inv": 4.5, "logo_h": 8},
    "50mm": {"label_w": 90, "label_h": 50, "qr_size": 36, "font_name": 11, "font_type": 7, "font_sn": 8, "font_loc": 7, "font_inv": 6.5, "logo_h": 16},
}
MARGIN_X = 10 * mm
MARGIN_Y = 10 * mm
GAP_Y = 4 * mm

ASSET_TYPES = {
    "Computer": {"form": "front/computer.form.php"},
    "Monitor":  {"form": "front/monitor.form.php"},
}

# === TRANSLATIONS ===
LANGS = {
    "Francais": "fr",
    "English": "en",
    "Espanol": "es",
    "Deutsch": "de",
}

T = {
    # Window titles
    "app_title":        {"fr": "GLPI Label Generator - Genesienne Groupe", "en": "GLPI Label Generator - Genesienne Groupe", "es": "GLPI Label Generator - Genesienne Groupe", "de": "GLPI Label Generator - Genesienne Groupe"},
    "settings_title":   {"fr": "Parametres", "en": "Settings", "es": "Ajustes", "de": "Einstellungen"},
    # Header
    "settings_btn":     {"fr": "Parametres", "en": "Settings", "es": "Ajustes", "de": "Einstellungen"},
    "connected":        {"fr": "Connecte", "en": "Connected", "es": "Conectado", "de": "Verbunden"},
    "demo_mode":        {"fr": "Mode demo", "en": "Demo mode", "es": "Modo demo", "de": "Demomodus"},
    # Settings window
    "glpi_config":      {"fr": "Configuration GLPI", "en": "GLPI Configuration", "es": "Configuracion GLPI", "de": "GLPI-Konfiguration"},
    "url_label":        {"fr": "URL GLPI :", "en": "GLPI URL:", "es": "URL GLPI:", "de": "GLPI-URL:"},
    "app_token_label":  {"fr": "App Token :", "en": "App Token:", "es": "App Token:", "de": "App-Token:"},
    "user_token_label": {"fr": "User Token :", "en": "User Token:", "es": "User Token:", "de": "User-Token:"},
    "logo_label":       {"fr": "Logo :", "en": "Logo:", "es": "Logo:", "de": "Logo:"},
    "logo_placeholder": {"fr": "Chemin vers le logo (optionnel)", "en": "Path to logo (optional)", "es": "Ruta al logo (opcional)", "de": "Pfad zum Logo (optional)"},
    "choose_logo":      {"fr": "Choisir le logo", "en": "Choose logo", "es": "Elegir logo", "de": "Logo wahlen"},
    "language_label":   {"fr": "Langue :", "en": "Language:", "es": "Idioma:", "de": "Sprache:"},
    "save_btn":         {"fr": "Sauvegarder", "en": "Save", "es": "Guardar", "de": "Speichern"},
    "cancel_btn":       {"fr": "Annuler", "en": "Cancel", "es": "Cancelar", "de": "Abbrechen"},
    "saved":            {"fr": "Sauvegarde !", "en": "Saved!", "es": "Guardado!", "de": "Gespeichert!"},
    # Filters
    "filters":          {"fr": "Filtres", "en": "Filters", "es": "Filtros", "de": "Filter"},
    "type_label":       {"fr": "Type :", "en": "Type:", "es": "Tipo:", "de": "Typ:"},
    "type_all":         {"fr": "Tous", "en": "All", "es": "Todos", "de": "Alle"},
    "ids_label":        {"fr": "IDs :", "en": "IDs:", "es": "IDs:", "de": "IDs:"},
    "location_label":   {"fr": "Lieu :", "en": "Location:", "es": "Lugar:", "de": "Standort:"},
    "location_ph":      {"fr": "Filtrer par lieu (contient)", "en": "Filter by location (contains)", "es": "Filtrar por lugar (contiene)", "de": "Nach Standort filtern (enthalt)"},
    "name_label":       {"fr": "Nom :", "en": "Name:", "es": "Nombre:", "de": "Name:"},
    "name_ph":          {"fr": "Filtrer par nom (contient)", "en": "Filter by name (contains)", "es": "Filtrar por nombre (contiene)", "de": "Nach Name filtern (enthalt)"},
    # Buttons
    "list_assets":      {"fr": "Lister les assets", "en": "List assets", "es": "Listar activos", "de": "Assets auflisten"},
    "generate_pdf":     {"fr": "Generer le PDF", "en": "Generate PDF", "es": "Generar PDF", "de": "PDF erstellen"},
    # Messages
    "loading":          {"fr": "Chargement...", "en": "Loading...", "es": "Cargando...", "de": "Laden..."},
    "demo_msg":         {"fr": "[DEMO] Utilisation des donnees fictives (tokens non configures)", "en": "[DEMO] Using dummy data (tokens not configured)", "es": "[DEMO] Usando datos ficticios (tokens no configurados)", "de": "[DEMO] Verwendung von Testdaten (Tokens nicht konfiguriert)"},
    "connecting":       {"fr": "Connexion a", "en": "Connecting to", "es": "Conectando a", "de": "Verbindung zu"},
    "session_ok":       {"fr": "[OK] Session GLPI ouverte", "en": "[OK] GLPI session opened", "es": "[OK] Sesion GLPI abierta", "de": "[OK] GLPI-Sitzung geoeffnet"},
    "session_closed":   {"fr": "[OK] Session GLPI fermee", "en": "[OK] GLPI session closed", "es": "[OK] Sesion GLPI cerrada", "de": "[OK] GLPI-Sitzung geschlossen"},
    "found":            {"fr": "trouves", "en": "found", "es": "encontrados", "de": "gefunden"},
    "not_found":        {"fr": "non trouve", "en": "not found", "es": "no encontrado", "de": "nicht gefunden"},
    "no_match":         {"fr": "[!] Aucun asset ne correspond aux filtres", "en": "[!] No assets match the filters", "es": "[!] Ningun activo coincide con los filtros", "de": "[!] Keine Assets entsprechen den Filtern"},
    "invalid_ids":      {"fr": "[!] Format IDs invalide (ex: 3,5,8)", "en": "[!] Invalid IDs format (e.g. 3,5,8)", "es": "[!] Formato de IDs invalido (ej: 3,5,8)", "de": "[!] Ungultiges ID-Format (z.B. 3,5,8)"},
    "error":            {"fr": "[ERREUR]", "en": "[ERROR]", "es": "[ERROR]", "de": "[FEHLER]"},
    "assets_count":     {"fr": "asset(s)", "en": "asset(s)", "es": "activo(s)", "de": "Asset(s)"},
    "total":            {"fr": "Total", "en": "Total", "es": "Total", "de": "Gesamt"},
    "save_pdf_title":   {"fr": "Enregistrer le PDF", "en": "Save PDF", "es": "Guardar PDF", "de": "PDF speichern"},
    "pdf_generating":   {"fr": "[PDF] Generation de", "en": "[PDF] Generating", "es": "[PDF] Generando", "de": "[PDF] Erstelle"},
    "labels":           {"fr": "etiquette(s)", "en": "label(s)", "es": "etiqueta(s)", "de": "Etikett(en)"},
    "pdf_saved":        {"fr": "[OK] PDF sauvegarde:", "en": "[OK] PDF saved:", "es": "[OK] PDF guardado:", "de": "[OK] PDF gespeichert:"},
    "pdf_cancelled":    {"fr": "[!] Generation annulee", "en": "[!] Generation cancelled", "es": "[!] Generacion cancelada", "de": "[!] Erstellung abgebrochen"},
    "labels_generated": {"fr": "etiquette(s) generees", "en": "label(s) generated", "es": "etiqueta(s) generadas", "de": "Etikett(en) erstellt"},
    # Asset types
    "computer":         {"fr": "Ordinateur", "en": "Computer", "es": "Ordenador", "de": "Computer"},
    "monitor":          {"fr": "Ecran", "en": "Monitor", "es": "Monitor", "de": "Monitor"},
    # Table headers
    "col_type":         {"fr": "Type", "en": "Type", "es": "Tipo", "de": "Typ"},
    "col_name":         {"fr": "Nom", "en": "Name", "es": "Nombre", "de": "Name"},
    "col_location":     {"fr": "Lieu", "en": "Location", "es": "Lugar", "de": "Standort"},
    "no_name":          {"fr": "Sans nom", "en": "No name", "es": "Sin nombre", "de": "Ohne Name"},
    "auth_bad_request": {"fr": "Echec authentification (400). Verifiez App Token et User Token dans Parametres.", "en": "Authentication failed (400). Check App Token and User Token in Settings.", "es": "Error de autenticacion (400). Verifique App Token y User Token en Ajustes.", "de": "Authentifizierung fehlgeschlagen (400). Prufen Sie App Token und User Token in Einstellungen."},
    "auth_unauthorized":{"fr": "Token invalide ou expire (401). Regenerez vos tokens dans GLPI.", "en": "Invalid or expired token (401). Regenerate your tokens in GLPI.", "es": "Token invalido o expirado (401). Regenere sus tokens en GLPI.", "de": "Ungueltiger oder abgelaufener Token (401). Erneuern Sie Ihre Tokens in GLPI."},
    "connection_failed":{"fr": "Impossible de se connecter au serveur. Verifiez l'URL GLPI.", "en": "Cannot connect to server. Check the GLPI URL.", "es": "No se puede conectar al servidor. Verifique la URL GLPI.", "de": "Verbindung zum Server nicht moeglich. Pruefen Sie die GLPI-URL."},
    "tape_size_label":  {"fr": "Ruban :", "en": "Tape:", "es": "Cinta:", "de": "Band:"},
    "color_mode_label": {"fr": "Couleur :", "en": "Color:", "es": "Color:", "de": "Farbe:"},
    "color_bw":         {"fr": "Noir & Blanc", "en": "Black & White", "es": "Blanco y Negro", "de": "Schwarz & Weiss"},
    "color_mono":       {"fr": "Monochrome", "en": "Monochrome", "es": "Monocromo", "de": "Monochrom"},
    "color_color":      {"fr": "Couleur", "en": "Color", "es": "Color", "de": "Farbe"},
    "color_inverse":    {"fr": "Inverse (blanc sur noir)", "en": "Inverse (white on black)", "es": "Inverso (blanco sobre negro)", "de": "Invertiert (weiss auf schwarz)"},
    "color_inverse_mono":{"fr": "Inverse Mono", "en": "Inverse Mono", "es": "Inverso Mono", "de": "Invertiert Mono"},
    "show_date_label":  {"fr": "Afficher date inventaire", "en": "Show inventory date", "es": "Mostrar fecha inventario", "de": "Inventardatum anzeigen"},
    "owner_label":      {"fr": "Propriete de :", "en": "Property of:", "es": "Propiedad de:", "de": "Eigentum von:"},
    "owner_placeholder":{"fr": "ex: Groupe Genesienne", "en": "e.g. My Company", "es": "ej: Mi Empresa", "de": "z.B. Meine Firma"},
    "owner_prefix":     {"fr": "Propriete de :", "en": "Property of:", "es": "Propiedad de:", "de": "Eigentum von:"},
}

# === CONFIG ===
def _migrate_old_config():
    """Move config from old location (next to exe) to %APPDATA%."""
    old_path = os.path.join(get_app_dir(), "glpi_config.json")
    if os.path.exists(old_path) and not os.path.exists(CONFIG_PATH):
        try:
            import shutil
            shutil.move(old_path, CONFIG_PATH)
        except:
            pass

def load_config():
    _migrate_old_config()
    defaults = {"glpi_url": "", "app_token": "", "user_token": "", "logo_path": "", "lang": "fr", "tape_size": "36mm", "color_mode": "bw", "owner": "", "show_date": True}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)
            defaults.update(saved)
        except:
            pass
    return defaults

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# === GLPI API ===
class GLPI:
    def __init__(self, url, app_token, user_token):
        self.url = url.rstrip("/")
        self.app_token = app_token
        self.user_token = user_token
        self.session = requests.Session()
        self.session.headers["App-Token"] = app_token

    def start(self):
        r = self.session.get(f"{self.url}/apirest.php/initSession",
            headers={"Authorization": f"user_token {self.user_token}"}, timeout=10)
        r.raise_for_status()
        self.session.headers["Session-Token"] = r.json()["session_token"]

    def get_all(self, ep):
        out, start = [], 0
        while True:
            r = self.session.get(f"{self.url}/apirest.php/{ep}",
                params={"range": f"{start}-{start+199}", "sort": "name", "order": "ASC"}, timeout=15)
            if r.status_code not in (200, 206):
                break
            b = r.json()
            if not b:
                break
            out.extend(b)
            if r.status_code == 200:
                break
            start += 200
        return out

    def get_one(self, ep, item_id):
        r = self.session.get(f"{self.url}/apirest.php/{ep}/{item_id}", timeout=10)
        r.raise_for_status()
        return r.json()

    def stop(self):
        try:
            self.session.get(f"{self.url}/apirest.php/killSession", timeout=5)
        except:
            pass
        self.session.close()

# === QR CODE ===
def make_qr(url, inverse=False):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=1)
    q.add_data(url)
    q.make(fit=True)
    fill = "white" if inverse else "black"
    back = "black" if inverse else "white"
    img = q.make_image(fill_color=fill, back_color=back).resize((300, 300))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)

# === DRAW LABEL ===
def draw_label(c, x, y, a, logo_path, tape="36mm", color_mode="bw", owner="", show_date=True):
    ts = TAPE_SIZES.get(tape, TAPE_SIZES["36mm"])
    lw = ts["label_w"] * mm
    lh = ts["label_h"] * mm
    qs = ts["qr_size"] * mm
    inverse = color_mode in ("inverse", "inverse_mono")
    is_color = color_mode == "color"
    is_mono = color_mode in ("mono", "inverse_mono")  # Pure black & white, no grays

    # Background fill for inverse mode
    if inverse:
        c.setFillColor(HexColor("#000000"))
        c.rect(x, y, lw, lh, fill=1, stroke=0)
        c.setStrokeColor(HexColor("#000000") if is_mono else HexColor("#333333"))
    else:
        c.setStrokeColor(HexColor("#000000") if is_mono else HexColor("#CCCCCC"))
    c.setLineWidth(0.5)
    c.rect(x, y, lw, lh)

    sx = x + 3*mm + qs + 2*mm
    c.setStrokeColor(HexColor("#FFFFFF") if (inverse and is_mono) else HexColor("#000000") if is_mono else HexColor("#444444") if inverse else HexColor("#E0E0E0"))
    c.setLineWidth(0.3)
    c.line(sx, y+3*mm, sx, y+lh-3*mm)

    c.drawImage(make_qr(a["url"], inverse=inverse), x+3*mm, y+(lh-qs)/2, qs, qs)

    tx = sx + 3*mm

    # Colors for text - mono modes use only pure black/white
    if is_mono:
        main_color = HexColor("#FFFFFF") if inverse else HexColor("#000000")
        sub_color = main_color
        sn_color = main_color
        loc_color = main_color
        inv_color = main_color
    else:
        main_color = HexColor("#FFFFFF") if inverse else HexColor("#000000")
        sub_color = HexColor("#CCCCCC") if inverse else (HexColor("#666666") if is_color else HexColor("#000000"))
        sn_color = HexColor("#FFFFFF") if inverse else (HexColor("#333333") if is_color else HexColor("#000000"))
        loc_color = HexColor("#AAAAAA") if inverse else (HexColor("#1B3A5C") if is_color else HexColor("#000000"))
        inv_color = HexColor("#888888") if inverse else (HexColor("#999999") if is_color else HexColor("#555555"))

    if logo_path and os.path.exists(logo_path):
        lgh = ts["logo_h"] * mm
        lgw = lgh * 2000/1444
        try:
            from PIL import Image as PILImage, ImageOps
            pil_img = PILImage.open(logo_path)
            # Normalize to RGB + separate alpha (handles P, L, LA, CMYK, RGBA, RGB, etc.)
            has_alpha = pil_img.mode in ("RGBA", "LA", "PA") or (pil_img.mode == "P" and "transparency" in pil_img.info)
            if has_alpha:
                pil_img = pil_img.convert("RGBA")
                alpha = pil_img.split()[3]
            else:
                pil_img = pil_img.convert("RGB")
                alpha = None
            rgb = pil_img.convert("RGB")
            gray = rgb.convert("L")

            if inverse and is_mono:
                # Inverse mono: everything non-white becomes white, white bg becomes transparent
                # Detect near-white pixels as background (threshold > 240)
                mask = gray.point(lambda p: 0 if p > 240 else 255)  # 0=bg, 255=content
                white = PILImage.new("L", gray.size, 255)
                if alpha:
                    final_alpha = PILImage.composite(mask, PILImage.new("L", mask.size, 0), alpha)
                else:
                    final_alpha = mask
                pil_img = PILImage.merge("RGBA", (white, white, white, final_alpha))
            elif inverse:
                # Inverse: everything non-white becomes white, white bg becomes transparent
                mask = gray.point(lambda p: 0 if p > 240 else 255)
                white = PILImage.new("L", gray.size, 255)
                if alpha:
                    final_alpha = PILImage.composite(mask, PILImage.new("L", mask.size, 0), alpha)
                else:
                    final_alpha = mask
                pil_img = PILImage.merge("RGBA", (white, white, white, final_alpha))
            elif is_mono:
                # Mono: everything non-white becomes black, white bg stays white
                bw = gray.point(lambda p: 255 if p > 240 else 0)
                a_ch = alpha if alpha else PILImage.new("L", bw.size, 255)
                pil_img = PILImage.merge("RGBA", (bw, bw, bw, a_ch))
            elif not is_color:
                # B&W: grayscale, preserve transparency
                a_ch = alpha if alpha else PILImage.new("L", gray.size, 255)
                pil_img = PILImage.merge("RGBA", (gray, gray, gray, a_ch))
            else:
                # Color: just ensure RGBA for mask="auto"
                a_ch = alpha if alpha else PILImage.new("L", rgb.size, 255)
                r, g, b = rgb.split()
                pil_img = PILImage.merge("RGBA", (r, g, b, a_ch))
            buf_logo = io.BytesIO()
            pil_img.save(buf_logo, format="PNG")
            buf_logo.seek(0)
            logo_img = ImageReader(buf_logo)
            c.drawImage(logo_img, x+lw-lgw-2*mm, y+lh-lgh-1*mm, lgw, lgh,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass  # Skip logo if unreadable

    # Name
    c.setFont("Helvetica-Bold", ts["font_name"])
    c.setFillColor(main_color)
    max_chars = int(ts["label_w"] * 0.22)
    nm = a["name"][:max_chars]+"..." if len(a["name"]) > max_chars+1 else a["name"]
    c.drawString(tx, y+lh-10*mm, nm)

    # Type
    c.setFont("Helvetica", ts["font_type"])
    c.setFillColor(sub_color)
    c.drawString(tx, y+lh-14*mm, a["type_label"])

    # Serial
    c.setFont("Helvetica-Bold", ts["font_sn"])
    c.setFillColor(sn_color)
    sn = a.get("serial", "N/A") or "N/A"
    c.drawString(tx, y+lh-19.5*mm, f"S/N: {sn[:20]}")

    # Date inventaire
    date_inv = a.get("date_inv", "") or ""
    if date_inv and tape != "25mm" and show_date:
        c.setFont("Helvetica", ts["font_loc"])
        c.setFillColor(sub_color)
        c.drawString(tx, y+lh-24*mm, f"Inv: {date_inv}")

    # Location
    loc = a.get("location", "") or ""
    if loc:
        loc_y = y+lh-28*mm if (date_inv and tape != "25mm" and show_date) else y+lh-24*mm
        c.setFont("Helvetica-Oblique" if not is_color else "Helvetica", ts["font_loc"])
        c.setFillColor(loc_color)
        c.drawString(tx, loc_y, loc[:20])

    # Bottom line: owner and/or inventory number
    bottom_y = y + 3*mm
    if owner:
        c.setFont("Helvetica-Bold", ts["font_inv"])
        c.setFillColor(main_color)
        c.drawString(tx, bottom_y, owner)

    inv = a.get("otherserial", "") or ""
    if inv and tape != "25mm":
        c.setFont("Helvetica", ts["font_inv"])
        c.setFillColor(inv_color)
        inv_x = tx if not owner else x + lw - 3*mm - c.stringWidth(f"Inv: {inv}", "Helvetica", ts["font_inv"])
        c.drawString(inv_x, bottom_y, f"Inv: {inv}")

    c.setFillColor(HexColor("#000000"))

# === GENERATE PDF ===
def make_pdf(assets, path, logo_path, tape="36mm", color_mode="bw", owner="", show_date=True):
    ts = TAPE_SIZES.get(tape, TAPE_SIZES["36mm"])
    lw = ts["label_w"] * mm
    lh = ts["label_h"] * mm

    c = canvas.Canvas(path, pagesize=A4)
    pw, ph = A4
    cols = int((pw - 2*MARGIN_X) // lw)
    rows = int((ph - 2*MARGIN_Y) // (lh + GAP_Y))
    per_page = cols * rows

    for i, a in enumerate(assets):
        pi = i % per_page
        if i > 0 and pi == 0:
            c.showPage()
        col, row = pi % cols, pi // cols
        draw_label(c, MARGIN_X + col*lw, ph - MARGIN_Y - (row+1)*(lh+GAP_Y), a, logo_path, tape, color_mode, owner, show_date)
    c.save()
    return len(assets)

# === ITEM TO ASSET ===
def item_to_asset(item, type_key, glpi_url, app=None):
    at = ASSET_TYPES[type_key]
    type_label = app._asset_type_label(type_key) if app else type_key
    no_name = app.t("no_name") if app else "Sans nom"
    # Extract year from date_creation (format: "2023-05-12 10:30:00")
    date_raw = item.get("date_creation", "") or ""
    date_inv = date_raw[:10] if date_raw else ""  # "2023-05-12"
    return {
        "id": item["id"],
        "name": item.get("name", no_name),
        "serial": item.get("serial", ""),
        "otherserial": item.get("otherserial", ""),
        "type_label": type_label,
        "location": item.get("completename", item.get("locations_name", "")),
        "date_inv": date_inv,
        "url": f"{glpi_url}/{at['form']}?id={item['id']}",
    }

# === DEMO DATA ===
def get_demo_data(glpi_url="https://genesienne.fr33.glpi-network.cloud", app=None):
    computer = app._asset_type_label("Computer") if app else "Ordinateur"
    monitor = app._asset_type_label("Monitor") if app else "Ecran"
    return [
        {"id":3,"name":"Automatisme-2","serial":"JXY51X2","type_label":computer,
         "location":"Andrezieux","otherserial":"","date_inv":"2021-03-15",
         "url":f"{glpi_url}/front/computer.form.php?id=3"},
        {"id":5,"name":"PC-BUREAU-DG","serial":"ABC123DEF456","type_label":computer,
         "location":"Chambon","otherserial":"INV-2024-001","date_inv":"2024-01-10",
         "url":f"{glpi_url}/front/computer.form.php?id=5"},
        {"id":12,"name":"DELL-U2722D","serial":"CN0F5XYZ789","type_label":monitor,
         "location":"Chambon","otherserial":"INV-2024-012","date_inv":"2023-06-22",
         "url":f"{glpi_url}/front/monitor.form.php?id=12"},
        {"id":8,"name":"PC-ATELIER-01","serial":"HJK789LMN012","type_label":computer,
         "location":"Sicaf","otherserial":"","date_inv":"2019-11-05",
         "url":f"{glpi_url}/front/computer.form.php?id=8"},
        {"id":15,"name":"ECRAN-COMPTA-01","serial":"MNO456PQR789","type_label":monitor,
         "location":"Andrezieux","otherserial":"INV-2024-015","date_inv":"2024-02-18",
         "url":f"{glpi_url}/front/monitor.form.php?id=15"},
        {"id":22,"name":"PC-DUNKERQUE-01","serial":"RST012UVW345","type_label":computer,
         "location":"Dunkerque","otherserial":"","date_inv":"2022-09-01",
         "url":f"{glpi_url}/front/computer.form.php?id=22"},
        {"id":7,"name":"PRECISION-7730","serial":"9XK4W53","type_label":computer,
         "location":"Chambon","otherserial":"INV-2024-003","date_inv":"2020-07-14",
         "url":f"{glpi_url}/front/computer.form.php?id=7"},
        {"id":20,"name":"DELL-P2422H","serial":"FN0R2ABC123","type_label":monitor,
         "location":"Dunkerque","otherserial":"","date_inv":"2023-11-30",
         "url":f"{glpi_url}/front/monitor.form.php?id=20"},
    ]

# === GUI APP ===
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GLPI Label Generator - Genesienne Groupe")
        self.geometry("750x700")
        self.minsize(650, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.cfg = load_config()
        self.lang = self.cfg.get("lang", "fr")
        self.assets = []

        self._build_ui()

    def t(self, key):
        """Translate a key to the current language."""
        entry = T.get(key, {})
        return entry.get(self.lang, entry.get("en", key))

    def _asset_type_label(self, type_key):
        """Get translated label for an asset type."""
        mapping = {"Computer": "computer", "Monitor": "monitor"}
        return self.t(mapping.get(type_key, type_key))

    def _build_ui(self):
        # Main scrollable frame
        self.main_frame = ctk.CTkScrollableFrame(self, label_text="")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === HEADER ===
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="GLPI Label Generator",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Genesienne Groupe",
                     font=ctk.CTkFont(size=14), text_color="#888888").pack(side="left", padx=(10, 0))

        # Config status + settings button (right side of header)
        self.lbl_config_status = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=12))
        self.lbl_config_status.pack(side="right", padx=(10, 0))
        self.btn_settings = ctk.CTkButton(header, text=self.t("settings_btn"), width=110, height=30,
                      fg_color="#555555", hover_color="#666666",
                      command=self._open_settings)
        self.btn_settings.pack(side="right")
        self._update_config_status()

        # === FILTERS SECTION ===
        flt_frame = ctk.CTkFrame(self.main_frame)
        flt_frame.pack(fill="x", pady=(0, 10))
        self.lbl_filters_title = ctk.CTkLabel(flt_frame, text=f"  {self.t('filters')}",
                     font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_filters_title.pack(anchor="w", padx=10, pady=(10, 5))

        fgrid = ctk.CTkFrame(flt_frame, fg_color="transparent")
        fgrid.pack(fill="x", padx=15, pady=(0, 10))
        fgrid.columnconfigure(1, weight=1)
        fgrid.columnconfigure(3, weight=1)

        self.lbl_type = ctk.CTkLabel(fgrid, text=self.t("type_label"))
        self.lbl_type.grid(row=0, column=0, sticky="w", pady=3)
        self.combo_type = ctk.CTkComboBox(fgrid, values=[self.t("type_all"), "Computer", "Monitor"],
                                          state="readonly", width=150)
        self.combo_type.set(self.t("type_all"))
        self.combo_type.grid(row=0, column=1, sticky="w", padx=(10, 20), pady=3)

        self.lbl_ids = ctk.CTkLabel(fgrid, text=self.t("ids_label"))
        self.lbl_ids.grid(row=0, column=2, sticky="w", pady=3)
        self.entry_ids = ctk.CTkEntry(fgrid, placeholder_text="ex: 3,5,8")
        self.entry_ids.grid(row=0, column=3, sticky="ew", padx=(10, 0), pady=3)

        self.lbl_lieu = ctk.CTkLabel(fgrid, text=self.t("location_label"))
        self.lbl_lieu.grid(row=1, column=0, sticky="w", pady=3)
        self.entry_lieu = ctk.CTkEntry(fgrid, placeholder_text=self.t("location_ph"))
        self.entry_lieu.grid(row=1, column=1, sticky="ew", padx=(10, 20), pady=3)

        self.lbl_nom = ctk.CTkLabel(fgrid, text=self.t("name_label"))
        self.lbl_nom.grid(row=1, column=2, sticky="w", pady=3)
        self.entry_nom = ctk.CTkEntry(fgrid, placeholder_text=self.t("name_ph"))
        self.entry_nom.grid(row=1, column=3, sticky="ew", padx=(10, 0), pady=3)

        # === ACTION BUTTONS ===
        act_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        act_frame.pack(fill="x", pady=(0, 10))

        self.btn_list = ctk.CTkButton(act_frame, text=self.t("list_assets"), command=self._list_assets,
                                      font=ctk.CTkFont(size=14), height=40, width=200)
        self.btn_list.pack(side="left", padx=(0, 10))

        self.btn_pdf = ctk.CTkButton(act_frame, text=self.t("generate_pdf"), command=self._generate_pdf,
                                     font=ctk.CTkFont(size=14, weight="bold"), height=40, width=200,
                                     fg_color="#1565C0", hover_color="#0D47A1")
        self.btn_pdf.pack(side="left", padx=(0, 10))

        self.lbl_count = ctk.CTkLabel(act_frame, text="", font=ctk.CTkFont(size=13))
        self.lbl_count.pack(side="left", padx=10)

        # === LOG / RESULTS ===
        self.log_box = ctk.CTkTextbox(self.main_frame, height=250, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.pack(fill="both", expand=True, pady=(0, 5))

    def _refresh_ui_texts(self):
        """Refresh all UI texts after language change."""
        self.title(self.t("app_title"))
        self.btn_settings.configure(text=self.t("settings_btn"))
        self._update_config_status()
        self.lbl_filters_title.configure(text=f"  {self.t('filters')}")
        self.lbl_type.configure(text=self.t("type_label"))
        self.combo_type.configure(values=[self.t("type_all"), "Computer", "Monitor"])
        self.combo_type.set(self.t("type_all"))
        self.lbl_ids.configure(text=self.t("ids_label"))
        self.lbl_lieu.configure(text=self.t("location_label"))
        self.entry_lieu.configure(placeholder_text=self.t("location_ph"))
        self.lbl_nom.configure(text=self.t("name_label"))
        self.entry_nom.configure(placeholder_text=self.t("name_ph"))
        self.btn_list.configure(text=self.t("list_assets"))
        self.btn_pdf.configure(text=self.t("generate_pdf"))

    def _update_config_status(self):
        """Update the config status indicator in the header."""
        if self.cfg.get("app_token") and self.cfg.get("user_token"):
            url = self.cfg.get("glpi_url", "")
            short = url.replace("https://", "").replace("http://", "")[:30]
            self.lbl_config_status.configure(text=f"{self.t('connected')}: {short}", text_color="#4CAF50")
        else:
            self.lbl_config_status.configure(text=self.t("demo_mode"), text_color="#FF9800")

    def _get_config_from_ui(self):
        return dict(self.cfg)

    def _open_settings(self):
        """Open settings in a separate window."""
        win = ctk.CTkToplevel(self)
        win.title(self.t("settings_title"))
        win.geometry("550x560")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        # Center on parent
        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 550) // 2
        y = self.winfo_y() + (self.winfo_height() - 560) // 2
        win.geometry(f"+{x}+{y}")

        ctk.CTkLabel(win, text=self.t("glpi_config"),
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 15))

        grid = ctk.CTkFrame(win, fg_color="transparent")
        grid.pack(fill="x", padx=25)
        grid.columnconfigure(1, weight=1)

        ctk.CTkLabel(grid, text=self.t("url_label")).grid(row=0, column=0, sticky="w", pady=6)
        e_url = ctk.CTkEntry(grid, placeholder_text="https://votre-instance.glpi-network.cloud")
        e_url.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=6, columnspan=2)
        e_url.insert(0, self.cfg.get("glpi_url", ""))

        ctk.CTkLabel(grid, text=self.t("app_token_label")).grid(row=1, column=0, sticky="w", pady=6)
        e_app = ctk.CTkEntry(grid, placeholder_text="App Token GLPI")
        e_app.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=6, columnspan=2)
        e_app.insert(0, self.cfg.get("app_token", ""))

        ctk.CTkLabel(grid, text=self.t("user_token_label")).grid(row=2, column=0, sticky="w", pady=6)
        e_user = ctk.CTkEntry(grid, placeholder_text="User Token GLPI")
        e_user.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=6, columnspan=2)
        e_user.insert(0, self.cfg.get("user_token", ""))

        ctk.CTkLabel(grid, text=self.t("logo_label")).grid(row=3, column=0, sticky="w", pady=6)
        e_logo = ctk.CTkEntry(grid, placeholder_text=self.t("logo_placeholder"))
        e_logo.grid(row=3, column=1, sticky="ew", padx=(10, 5), pady=6)
        e_logo.insert(0, self.cfg.get("logo_path", ""))

        def browse_logo():
            path = filedialog.askopenfilename(
                parent=win, title=self.t("choose_logo"),
                filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("Tous/*", "*.*")])
            if path:
                # Copy logo to AppData so it persists
                import shutil
                ext = os.path.splitext(path)[1]
                dest = os.path.join(CONFIG_DIR, f"logo{ext}")
                try:
                    shutil.copy2(path, dest)
                    path = dest
                except Exception:
                    pass  # Fallback to original path
                e_logo.delete(0, "end")
                e_logo.insert(0, path)

        ctk.CTkButton(grid, text="...", width=40, command=browse_logo).grid(row=3, column=2, pady=6)

        # Tape size selector
        ctk.CTkLabel(grid, text=self.t("tape_size_label")).grid(row=4, column=0, sticky="w", pady=6)
        tape_values = list(TAPE_SIZES.keys())
        combo_tape = ctk.CTkComboBox(grid, values=tape_values, state="readonly", width=180)
        combo_tape.set(self.cfg.get("tape_size", "36mm"))
        combo_tape.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=6)

        # Color mode
        ctk.CTkLabel(grid, text=self.t("color_mode_label")).grid(row=5, column=0, sticky="w", pady=6)
        color_values = [self.t("color_bw"), self.t("color_mono"), self.t("color_color"), self.t("color_inverse"), self.t("color_inverse_mono")]
        color_map = {"bw": self.t("color_bw"), "mono": self.t("color_mono"), "color": self.t("color_color"), "inverse": self.t("color_inverse"), "inverse_mono": self.t("color_inverse_mono")}
        # Backward compat: old bool config
        old_color = self.cfg.get("color")
        if isinstance(old_color, bool):
            current_mode = "color" if old_color else "bw"
        else:
            current_mode = self.cfg.get("color_mode", "bw")
        combo_color = ctk.CTkComboBox(grid, values=color_values, state="readonly", width=250)
        combo_color.set(color_map.get(current_mode, self.t("color_bw")))
        combo_color.grid(row=5, column=1, sticky="w", padx=(10, 0), pady=6)

        # Show inventory date checkbox
        chk_date_var = ctk.BooleanVar(value=self.cfg.get("show_date", True))
        chk_date = ctk.CTkCheckBox(grid, text=self.t("show_date_label"), variable=chk_date_var)
        chk_date.grid(row=6, column=0, columnspan=3, sticky="w", pady=6)

        # Owner text
        ctk.CTkLabel(grid, text=self.t("owner_label")).grid(row=7, column=0, sticky="w", pady=6)
        e_owner = ctk.CTkEntry(grid, placeholder_text=self.t("owner_placeholder"))
        e_owner.grid(row=7, column=1, sticky="ew", padx=(10, 0), pady=6, columnspan=2)
        e_owner.insert(0, self.cfg.get("owner", ""))

        # Language selector
        ctk.CTkLabel(grid, text=self.t("language_label")).grid(row=8, column=0, sticky="w", pady=6)
        lang_names = list(LANGS.keys())
        combo_lang = ctk.CTkComboBox(grid, values=lang_names, state="readonly", width=180)
        current_name = next((k for k, v in LANGS.items() if v == self.lang), "Francais")
        combo_lang.set(current_name)
        combo_lang.grid(row=8, column=1, sticky="w", padx=(10, 0), pady=6)

        # Buttons
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(25, 20))

        lbl_status = ctk.CTkLabel(btn_frame, text="", text_color="#4CAF50")
        lbl_status.pack(side="left")

        def do_save():
            new_lang = LANGS.get(combo_lang.get(), "fr")
            # Resolve color mode from combo
            rev_map = {self.t("color_bw"): "bw", self.t("color_mono"): "mono", self.t("color_color"): "color", self.t("color_inverse"): "inverse", self.t("color_inverse_mono"): "inverse_mono"}
            sel_mode = rev_map.get(combo_color.get(), "bw")
            self.cfg = {
                "glpi_url": e_url.get().strip().rstrip("/"),
                "app_token": e_app.get().strip(),
                "user_token": e_user.get().strip(),
                "logo_path": e_logo.get().strip(),
                "lang": new_lang,
                "tape_size": combo_tape.get(),
                "color_mode": sel_mode,
                "owner": e_owner.get().strip(),
                "show_date": chk_date_var.get(),
            }
            save_config(self.cfg)
            self.lang = new_lang
            self._update_config_status()
            self._refresh_ui_texts()
            lbl_status.configure(text=self.t("saved"))
            win.after(1000, win.destroy)

        ctk.CTkButton(btn_frame, text=self.t("cancel_btn"), width=100,
                      fg_color="#555555", hover_color="#666666",
                      command=win.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_frame, text=self.t("save_btn"), width=130,
                      fg_color="#2B7A2B", hover_color="#1F5C1F",
                      command=do_save).pack(side="right")

    def _log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def _clear_log(self):
        self.log_box.delete("1.0", "end")

    def _is_demo_mode(self):
        return not self.cfg.get("app_token") or not self.cfg.get("user_token")

    def _get_filters(self):
        type_val = self.combo_type.get()
        type_all = self.t("type_all")
        return {
            "type": type_val if type_val != type_all else None,
            "ids": self.entry_ids.get().strip(),
            "lieu": self.entry_lieu.get().strip(),
            "nom": self.entry_nom.get().strip(),
        }

    def _apply_filters(self, assets, filters):
        result = list(assets)
        if filters["type"]:
            tl = self._asset_type_label(filters["type"])
            result = [a for a in result if a["type_label"] == tl]
        if filters["ids"]:
            try:
                ids = [int(x.strip()) for x in filters["ids"].split(",") if x.strip()]
                result = [a for a in result if a["id"] in ids]
            except ValueError:
                self._log(self.t("invalid_ids"))
        if filters["lieu"]:
            result = [a for a in result if filters["lieu"].lower() in (a.get("location", "") or "").lower()]
        if filters["nom"]:
            result = [a for a in result if filters["nom"].lower() in (a.get("name", "") or "").lower()]
        result.sort(key=lambda a: a["name"])
        return result

    def _fetch_assets(self, filters):
        """Fetch assets from GLPI API or demo data. Returns list of assets."""
        cfg = self._get_config_from_ui()

        if self._is_demo_mode():
            self._log(self.t("demo_msg"))
            url = cfg["glpi_url"] or "https://genesienne.fr33.glpi-network.cloud"
            return get_demo_data(url, self)

        # Production mode
        self._log(f"{self.t('connecting')} {cfg['glpi_url']}...")
        g = GLPI(cfg["glpi_url"], cfg["app_token"], cfg["user_token"])
        connected = False
        try:
            g.start()
            connected = True
            self._log(self.t("session_ok"))

            types_to_fetch = [filters["type"]] if filters["type"] else list(ASSET_TYPES.keys())

            if filters["ids"]:
                ids = [int(x.strip()) for x in filters["ids"].split(",") if x.strip()]
                assets = []
                for item_id in ids:
                    found = False
                    for type_key in types_to_fetch:
                        try:
                            item = g.get_one(type_key, item_id)
                            assets.append(item_to_asset(item, type_key, cfg["glpi_url"], self))
                            self._log(f"  [OK] {type_key} #{item_id}: {item.get('name', '?')}")
                            found = True
                            break
                        except:
                            continue
                    if not found:
                        self._log(f"  [!] ID {item_id} {self.t('not_found')}")
                return assets
            else:
                # Fetch types in parallel
                def fetch_type(type_key):
                    items = g.get_all(type_key)
                    self._log(f"  {type_key}: {len(items)} {self.t('found')}")
                    return [(item, type_key) for item in items]

                assets = []
                with ThreadPoolExecutor(max_workers=len(types_to_fetch)) as pool:
                    results = pool.map(fetch_type, types_to_fetch)
                    for batch in results:
                        for item, type_key in batch:
                            assets.append(item_to_asset(item, type_key, cfg["glpi_url"], self))
                return assets
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            if status == 400:
                self._log(f"\n{self.t('error')} {self.t('auth_bad_request')}")
            elif status == 401:
                self._log(f"\n{self.t('error')} {self.t('auth_unauthorized')}")
            else:
                self._log(f"\n{self.t('error')} HTTP {status}: {e}")
            raise
        except requests.exceptions.ConnectionError:
            self._log(f"\n{self.t('error')} {self.t('connection_failed')}")
            raise
        finally:
            if connected:
                g.stop()
                self._log(self.t("session_closed"))

    def _display_assets(self, assets):
        """Display assets in the log box as a table."""
        self._log(f"\n{'ID':>5}  {self.t('col_type'):<12} {self.t('col_name'):<22} {'S/N':<18} {self.t('col_location')}")
        self._log("-" * 75)
        for a in assets:
            sn = (a.get("serial", "") or "N/A")[:16]
            loc = (a.get("location", "") or "")[:18]
            self._log(f"{a['id']:>5}  {a['type_label']:<12} {a['name']:<22} {sn:<18} {loc}")
        self._log(f"\n  {self.t('total')}: {len(assets)} {self.t('assets_count')}")

    def _set_buttons_state(self, state):
        self.btn_list.configure(state=state)
        self.btn_pdf.configure(state=state)

    def _list_assets(self):
        """List assets in the log box."""
        self._clear_log()
        self._set_buttons_state("disabled")
        self.lbl_count.configure(text=self.t("loading"))

        def worker():
            try:
                filters = self._get_filters()
                raw = self._fetch_assets(filters)
                self.assets = self._apply_filters(raw, filters)

                if not self.assets:
                    self._log(f"\n{self.t('no_match')}")
                    self.after(0, lambda: self.lbl_count.configure(text=f"0 {self.t('assets_count')}"))
                else:
                    self._display_assets(self.assets)
                    self.after(0, lambda c=len(self.assets): self.lbl_count.configure(text=f"{c} {self.t('assets_count')}"))
            except Exception as e:
                self._log(f"\n{self.t('error')} {e}")
                self.after(0, lambda: self.lbl_count.configure(text=self.t("error")))
            finally:
                self.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _generate_pdf(self):
        """Generate PDF with labels."""
        self._clear_log()
        self._set_buttons_state("disabled")
        self.lbl_count.configure(text=self.t("loading"))

        def worker():
            try:
                filters = self._get_filters()
                raw = self._fetch_assets(filters)
                self.assets = self._apply_filters(raw, filters)

                if not self.assets:
                    self._log(f"\n{self.t('no_match')}")
                    self.after(0, lambda: self.lbl_count.configure(text=f"0 {self.t('assets_count')}"))
                    self.after(0, lambda: self._set_buttons_state("normal"))
                    return

                self._display_assets(self.assets)

                # Generate to temp file and open directly
                import tempfile, time, glob
                tmp_dir = tempfile.gettempdir()
                # Clean old generated PDFs (ignore locked files)
                for old in glob.glob(os.path.join(tmp_dir, "glpi_etiquettes_*.pdf")):
                    try:
                        os.remove(old)
                    except:
                        pass
                path = os.path.join(tmp_dir, f"glpi_etiquettes_{int(time.time())}.pdf")
                cfg = self._get_config_from_ui()
                logo = cfg.get("logo_path", "")
                self._log(f"\n{self.t('pdf_generating')} {len(self.assets)} {self.t('labels')}...")
                tape = cfg.get("tape_size", "36mm")
                # Backward compat: old bool config
                old_color = cfg.get("color")
                if isinstance(old_color, bool):
                    color_mode = "color" if old_color else "bw"
                else:
                    color_mode = cfg.get("color_mode", "bw")
                raw_owner = cfg.get("owner", "")
                owner = f"{self.t('owner_prefix')} {raw_owner}" if raw_owner else ""
                show_date = cfg.get("show_date", True)
                make_pdf(self.assets, path, logo, tape, color_mode, owner, show_date)
                self._log(f"{self.t('pdf_saved')} {path}")
                self.after(0, lambda: self.lbl_count.configure(
                    text=f"{len(self.assets)} {self.t('labels_generated')}"))

                try:
                    if sys.platform == "win32":
                        os.startfile(path)
                    elif sys.platform == "darwin":
                        os.system(f'open "{path}"')
                    else:
                        os.system(f'xdg-open "{path}"')
                except Exception as e:
                    self._log(f"\n{self.t('error')} {e}")

            except Exception as e:
                self._log(f"\n{self.t('error')} {e}")
                self.after(0, lambda: self.lbl_count.configure(text=self.t("error")))
            finally:
                self.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
