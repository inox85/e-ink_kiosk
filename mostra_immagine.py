#!/home/inox/waveshare-env/bin/python3
import json
import sys
import os
import logging
from PIL import Image
import requests


# ── Configurazione ────────────────────────────────────────────
MODELLO         = "epd7in5b_V2"                               # modello display
IMMAGINE_BLACK  = os.path.expanduser("~/e-ink_kiosk/images/immagine_black.png")  # buffer nero
IMMAGINE_RED    = os.path.expanduser("~/e-ink_kiosk/images/immagine_red.png")    # buffer rosso (opzionale)
LIB_PATH        = os.path.expanduser("~/e-ink_kiosk/e-Paper/RaspberryPi_JetsonNano/python/lib")
IMG_SOURCE_LINK = "https://www.fotografofirenze.it/cartelloportawd/show.php"
LOG_LINK        = "https://www.fotografofirenze.it/cartelloportawd/catch_log.php"
# ─────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

def carica_modulo(modello):
    sys.path.insert(0, LIB_PATH)
    try:
        import importlib
        mod = importlib.import_module(f"waveshare_epd.{modello}")
        log.info(f"Modulo '{modello}' caricato correttamente.")
        return mod
    except ModuleNotFoundError:
        log.error(f"Modulo '{modello}' non trovato in {LIB_PATH}")
        log.error("Modelli disponibili:")
        epd_path = os.path.join(LIB_PATH, "waveshare_epd")
        for f in sorted(os.listdir(epd_path)):
            if f.startswith("epd") and f.endswith(".py"):
                log.error(f"  - {f[:-3]}")
        sys.exit(1)

def prepara_immagine(img_path, width, height, nome="immagine"):
    """Carica e prepara un'immagine in formato 1-bit per il display."""
    if not os.path.exists(img_path):
        return None

    log.info(f"Caricamento {nome}: {img_path}")
    img = Image.open(img_path)
    log.info(f"  Dimensioni: {img.size}, Modalità: {img.mode}")

    # Ridimensiona se necessario
    if img.size != (width, height):
        log.info(f"  Ridimensionamento a {width}x{height}...")
        img = img.resize((width, height), Image.LANCZOS)

    # Converti in 1-bit bianco/nero
    img = img.convert("1")
    log.info(f"  Convertita in bianco/nero.")
    return img

def web_log(status, msg):
    url = LOG_LINK
    requests.get(url, params={
        "device": "rpi_porta",
        "status": status,
        "msg": msg
    })

def main():
    # Carica il modulo del display
    #url = "https://www.fotografofirenze.it/cartelloportawd/wd_cartello_black.png"
    log.info("Begin...")

    url = IMG_SOURCE_LINK
    response = requests.get(url)
    print(response.text)

    data = response.json()

    print(data["black"])
    print(data["red"])

    new_black = data["black"] 
    new_red = data["red"]

    actual_black = "" 
    actual_red = ""

    with open("actual_images.json", "r", encoding="utf-8") as file:
        j = json.loads(file.read())
        print(j)
        actual_black = j["black"] 
        actual_red = j["red"]
       
    if actual_black != new_black or actual_red != new_red:

        with open("actual_images.json", "w", encoding="utf-8") as file:
            json.dump(response.text, file, indent=2)
            
        black_image = requests.get(data["black"])

        web_log("ok", "Black image downloaded")
        
        with open(IMMAGINE_BLACK, "wb") as f:
            f.write(black_image.content)

        red_image = requests.get(data["red"])

        web_log("ok", "Red image downloaded")

        with open(IMMAGINE_RED, "wb") as f:
            f.write(red_image.content)
        
        epd_mod = carica_modulo(MODELLO)
        epd = epd_mod.EPD()
        log.info(f"Risoluzione display: {epd.width}x{epd.height}")

        web_log("ok", "Resolution ok")

        # Inizializza e pulisce il display
        log.info("Inizializzazione display...")
        epd.init()

        web_log("ok", "Display init ok")
        #log.info("Pulizia display (potrebbe richiedere qualche secondo)...")
        #epd.Clear()

        # ── Prepara buffer NERO ───────────────────────────────────
        img_black = prepara_immagine(IMMAGINE_BLACK, epd.width, epd.height, "buffer nero")
        if img_black is None:
            log.error(f"Immagine nera non trovata: {IMMAGINE_BLACK}")
            log.error("Copia l'immagine con: scp immagine_black.png inox@raspberrypi.local:~/")
            sys.exit(1)

        # ── Prepara buffer ROSSO ──────────────────────────────────
        img_red = prepara_immagine(IMMAGINE_RED, epd.width, epd.height, "buffer rosso")
        if img_red is None:
            log.info(f"Immagine rossa non trovata: {IMMAGINE_RED} → uso buffer rosso vuoto.")
            img_red = Image.new('1', (epd.width, epd.height), 255)  # bianco = niente rosso

        # ── Invia al display ──────────────────────────────────────
        import inspect
        sig = inspect.signature(epd.display)
        num_params = len(sig.parameters)

        log.info("Invio immagine al display...")
        if num_params >= 2:
            log.info("Display a 3 colori: invio buffer nero + rosso...")
            epd.display(epd.getbuffer(img_black), epd.getbuffer(img_red))
        else:
            log.info("Display a 2 colori: invio solo buffer nero...")
            epd.display(epd.getbuffer(img_black))

        log.info("✓ Immagine visualizzata!")

        web_log("ok", "Image correctly shown!")

        # Metti il display in sleep per preservarlo
        log.info("Display in sleep.")
        epd.sleep()

    else:
        log.info("Image already updated!")

if __name__ == "__main__":
    main()
