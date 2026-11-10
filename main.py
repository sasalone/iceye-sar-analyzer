"""Pääohjelma: SAR Dark Vessel Kinematics & Wake Analyzer."""

import os
import cv2
from src.fetcher import get_or_create_roi
from src.detector import detect_and_segment_ship, render_segmented_ship
from src.annotator import get_or_create_wake_annotation

STAC_URL = (
    "https://iceye-open-data-catalog.s3.amazonaws.com/"
    "stac-items/2025/05/ICEYE_6MC5KR_20250526T033241Z_4770346_X31_SLEDF.json"
)


def main():
    """Suorittaa vaiheet 1-3: haku, laivan segmentointi ja perävanan piirto."""
    print("=== VAIHE 1: KUVAN JA METATIETOJEN HAKU (FETCHER) ===")
    roi_img, meta = get_or_create_roi(STAC_URL, force_reload=False)

    print("\n=== VAIHE 2 & 3: LAIVAN TUNNISTUS JA VÄRITYS (DETECTOR) ===")
    ship_data = detect_and_segment_ship(
        roi_img, pixel_res_m=meta["effective_pixel_m"]
    )
    print(f"  Laivan keskipiste (px) : {ship_data['center_xy']}")
    print(f"  Arvioitu koko          : {ship_data['length_m']}m x {ship_data['width_m']}m")

    segmented_img = render_segmented_ship(roi_img, ship_data)
    cv2.imwrite(os.path.join("data", "step2_segmented_ship.png"), segmented_img)

    print("\n=== VAIHE 4: PERÄVANAN MERKITSEMINEN (ANNOTATOR) ===")
    # Aseta force_reannotate=True, jos haluat piirtää perävanan uudelleen
    wake_data = get_or_create_wake_annotation(
        segmented_img, ship_data, force_reannotate=False
    )

    print(f"  Perävanan kärki (px)   : {wake_data['apex_xy']}")
    print(f"  Perävanan häntä (px)   : {wake_data['tail_xy']}")


if __name__ == "__main__":
    main()
