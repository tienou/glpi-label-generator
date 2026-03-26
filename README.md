# GLPI Label Generator

Inventory label generator for GLPI with QR codes. Desktop application with modern GUI, compatible with Brother PT-P910BT (36mm tape).

> Generateur d'etiquettes d'inventaire GLPI avec QR codes. Application desktop avec interface graphique moderne.

## Features

- Connects to GLPI API to fetch assets (computers & monitors)
- Generates QR codes linking directly to GLPI asset pages
- Produces PDF labels with: QR code, name, type, serial number, location, inventory number, company logo
- Filters by type, location, name, or specific IDs
- Built-in demo mode with sample data (no GLPI instance required)
- Multi-language support: Francais, English, Espanol, Deutsch
- Persistent configuration (saved between sessions)
- Dark mode interface

## Download

**[Download GLPI_Labels.exe](https://github.com/tienou/glpi-label-generator/releases/latest)** - Portable, no installation required.

## Screenshots

### Main interface
![Main interface](docs/screenshot_main.png)

### Settings
![Settings](docs/screenshot_settings.png)

### Generated PDF labels
![Labels](docs/screenshot_labels.png)

## Quick Start

1. Download `GLPI_Labels.exe` from [Releases](https://github.com/tienou/glpi-label-generator/releases/latest)
2. Run the exe (no installation needed)
3. Click **Settings** to configure your GLPI instance:
   - **GLPI URL**: Your instance URL (e.g. `https://your-instance.glpi-network.cloud`)
   - **App Token**: From GLPI > Setup > General > API > Add API client
   - **User Token**: From GLPI > Your name > Settings > Remote API token
   - **Logo**: Optional company logo for labels
   - **Language**: Choose your preferred language
4. Use filters to select assets, then click **Generate PDF**

## GLPI API Setup

1. **Enable API**: GLPI > Setup > General > API > Enable REST API
2. **Create API client**: Add API Client > copy the App Token
3. **Get User Token**: Your name > Settings > API Token > Regenerate > copy

## Build from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python glpi_labels_gui.py

# Build portable exe
python -m PyInstaller --onefile --windowed --name "GLPI_Labels" \
    --collect-all customtkinter \
    --hidden-import PIL \
    --hidden-import PIL._tkinter_finder \
    glpi_labels_gui.py
```

## CLI Version

A command-line version is also available (`glpi_labels.py`):

```bash
python glpi_labels.py --lieu Dunkerque --type Computer
python glpi_labels.py --id 3,5,8
python glpi_labels.py --list
```

## Label Format

Each label (80x36mm) contains:
- QR code linking to the GLPI asset page
- Asset name
- Asset type (Computer/Monitor)
- Serial number
- Location
- Inventory number
- Company logo (optional)

## Dependencies

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern GUI
- [ReportLab](https://www.reportlab.com/) - PDF generation
- [qrcode](https://github.com/lincolnloop/python-qrcode) - QR code generation
- [Pillow](https://python-pillow.org/) - Image processing
- [Requests](https://requests.readthedocs.io/) - HTTP/API calls

## License

MIT
