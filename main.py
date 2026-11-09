"""Pääohjelma: SAR Dark Vessel Kinematics & Wake Analyzer."""

import os
import cv2
from src.fetcher import get_or_create_roi
from src.detector import detect_and_segment_ship, render_segmented_ship

STAC_URL = (
    "https://iceye-open-data-catalog.s3.amazonaws.com/"
    "stac-items/2025/05/ICEYE_6MC5KR_20250526T033241Z_4770346_X31_SLEDF.json"
)


def main():
    """Suorittaa kuvan haun (Moduuli 1) ja aluksen segmentoinnin (Moduuli 2)."""
    print("=== VAIHE 1: KUVAN JA METATIETOJEN HAKU (FETCHER) ===")
    roi_img, meta = get_or_create_roi(STAC_URL, force_reload=False)

    print("\n=== VAIHE 2 & 3: LAIVAN TUNNISTUS JA VÄRITYS (DETECTOR) ===")
    ship_data = detect_and_segment_ship(
        roi_img, pixel_res_m=meta["effective_pixel_m"]
    )

    print(f"  Laivan keskipiste (px) : {ship_data['center_xy']}")
    print(f"  Arvioitu pituus        : {ship_data['length_m']} m")
    print(f"  Arvioitu leveys        : {ship_data['width_m']} m")
    print(f"  Tutkapinta-ala (RCS)   : {ship_data['area_m2']} m²")

    segmented_img = render_segmented_ship(roi_img, ship_data)
    out_path = os.path.join("data", "step2_segmented_ship.png")
    cv2.imwrite(out_path, segmented_img)
    print(f"[Detector] Tallennettu väritetty laivakuva -> {out_path}")

    win_name = "Moduuli 2 (Detector): Tunnistettu ja varitetty laiva (Paina ENTER sulkeaksesi)"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 700, 700)
    cv2.imshow(win_name, segmented_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
