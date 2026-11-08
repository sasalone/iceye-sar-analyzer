"""Moduuli 1: STAC-metatietojen ja SAR-kuvaleikkeen (ROI) haku ja välimuistitus."""

import os
import json
import requests
import numpy as np
import cv2
import rasterio
from rasterio.errors import RasterioIOError

os.environ["AWS_NO_SIGN_REQUEST"] = "YES"
os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"


def fetch_stac_metadata(stac_url: str) -> dict:
    """Hakee STAC JSON -tiedoston ja poimii SAR-fysiikkaparametrit sekä kuvalinkit."""
    item_name = stac_url.split("/")[-1]
    print(f"[Fetcher] Haetaan STAC-metatiedot: {item_name} ...")
    resp = requests.get(stac_url, timeout=15)
    resp.raise_for_status()
    item = resp.json()

    props = item.get("properties", {})
    assets = item.get("assets", {})

    pixel_spacing = props.get("sar:pixel_spacing_range") or props.get("gsd") or 1.0
    inc_angle = props.get("view:incidence_angle") or 30.0

    metadata = {
        "item_id": item.get("id", "unknown"),
        "platform": props.get("platform", "ICEYE-X"),
        "instrument_mode": props.get("sar:instrument_mode", "UNKNOWN"),
        "product_type": props.get("sar:product_type", "GRD"),
        "incidence_angle_deg": float(inc_angle),
        "pixel_spacing_m": float(pixel_spacing),
        "orbit_state": props.get("sat:orbit_state", "unknown"),
        "sat_altitude_m": 530000.0, # Iceye-X38 korkeus 530km
        "sat_velocity_ms": 7600.0, # Iceyey-X38 nopeus 7,6km/s
        "stac_url": stac_url,
        "preview_url": None,
        "tif_url": None,
    }

    s3_prefix = "s3://iceye-open-data-catalog/"
    https_prefix = "https://iceye-open-data-catalog.s3.amazonaws.com/"

    for key, asset in assets.items():
        href = asset.get("href", "")
        if href.startswith(s3_prefix):
            href = href.replace(s3_prefix, https_prefix)

        is_img = href.lower().endswith((".png", ".jpg", ".jpeg"))
        if is_img and metadata["preview_url"] is None:
            metadata["preview_url"] = href
        elif href.lower().endswith((".tif", ".tiff")):
            tags = ("GRD", "COG", "VISUAL", "SLEDF")
            if any(k in key.upper() or k in href.upper() for k in tags):
                metadata["tif_url"] = href
            elif metadata["tif_url"] is None:
                metadata["tif_url"] = href

    return metadata


def _load_source_image(metadata: dict) -> tuple[np.ndarray, float]:
    """Lataa esikatselukuvan ja laskee sen efektiivisen pikselikoon (m/px)."""
    preview_url = metadata["preview_url"]
    if not preview_url:
        raise ValueError("STAC-kohteesta ei löytynyt sopivaa kuvaa.")

    file_name = preview_url.split("/")[-1]
    print(f"[Fetcher] Ladataan prosessoitu kuva: {file_name} ...")
    resp = requests.get(preview_url, timeout=20)
    resp.raise_for_status()
    arr = np.frombuffer(resp.content, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)

    scale_factor = 4.0
    if metadata["tif_url"]:
        try:
            with rasterio.open(metadata["tif_url"]) as src:
                scale_factor = src.width / float(img.shape[1])
        except (RasterioIOError, OSError):
            pass

    effective_res_m = round(metadata["pixel_spacing_m"] * scale_factor, 3)
    return img, effective_res_m


def get_or_create_roi(
    stac_url: str, data_dir: str = "data", force_reload: bool = False
) -> tuple[np.ndarray, dict]:
    """Lataa ROI-leikkeen välimuistista tai pyytää käyttäjää rajaamaan sen."""
    os.makedirs(data_dir, exist_ok=True)
    patch_path = os.path.join(data_dir, "roi_patch.png")
    meta_path = os.path.join(data_dir, "roi_metadata.json")

    if not force_reload and os.path.exists(patch_path) and os.path.exists(meta_path):
        print(f"[Fetcher] Ladataan kuvaleike välimuistista ({data_dir}/)...")
        img = cv2.imread(patch_path, cv2.IMREAD_GRAYSCALE)
        with open(meta_path, "r", encoding="utf-8") as file_obj:
            meta = json.load(file_obj)
        return img, meta

    meta = fetch_stac_metadata(stac_url)
    full_img, eff_res_m = _load_source_image(meta)
    meta["effective_pixel_m"] = eff_res_m

    win_name = "Moduuli 1 (Fetcher): Rajaa LAIVA + PERAVANA ja paina ENTER"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    height, width = full_img.shape[:2]
    scale = min(1.0, 850.0 / max(height, width))
    cv2.resizeWindow(win_name, int(width * scale), int(height * scale))

    print("\n>>> OHJE: Maalaa hiirellä laatikko laivan ympärille ja paina ENTER! <<<")
    roi = cv2.selectROI(win_name, full_img, showCrosshair=True)
    cv2.destroyAllWindows()

    rx, ry, rw, rh = [int(v) for v in roi]
    if rw == 0 or rh == 0:
        raise RuntimeError("Aluetta ei valittu. Keskeytetään.")

    crop_img = full_img[ry : ry + rh, rx : rx + rw]
    meta["roi_bbox_px"] = [rx, ry, rw, rh]

    cv2.imwrite(patch_path, crop_img)
    with open(meta_path, "w", encoding="utf-8") as file_obj:
        json.dump(meta, file_obj, indent=4)

    print(f"[Fetcher] Tallennettu kuvaleike ({rw}x{rh} px) -> {patch_path}")
    print(f"[Fetcher] Tallennettu metatiedot -> {meta_path}")
    return crop_img, meta
