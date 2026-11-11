"""Pääohjelma: SAR Dark Vessel Kinematics & Wake Analyzer."""

import os
import cv2
from src.fetcher import get_or_create_roi
from src.detector import detect_and_segment_ship, render_segmented_ship
from src.annotator import get_or_create_wake_annotation
from src.physics import calculate_vessel_kinematics, save_kinematics_report
from src.visualizer import create_final_report_image

STAC_URL = (
    "https://iceye-open-data-catalog.s3.amazonaws.com/"
    "stac-items/2025/05/ICEYE_6MC5KR_20250526T033241Z_4770346_X31_SLEDF.json"
)


def main():
    """Suorittaa koko analyysiputken vaiheista 1-6."""
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
    wake_data = get_or_create_wake_annotation(
        segmented_img, ship_data, force_reannotate=False
    )

    print("\n=== VAIHE 5: DOPPLER-FYSIIKKA JA KINEMATIIKKA (PHYSICS) ===")
    kinematics = calculate_vessel_kinematics(meta, ship_data, wake_data)
    save_kinematics_report(kinematics)

    print(f"  Kuvaustila (Mode)      : {kinematics['imaging_mode']}")
    print(f"  Etäisyys (Slant Range) : {kinematics['slant_range_km']} km")
    print(
        f"  Atsimuuttisiirtymä     : {kinematics['azimuth_shift_m']} m "
        f"({kinematics['azimuth_shift_px']} px)"
    )
    print(f"  Säteittäinen nopeus Vr : {kinematics['radial_velocity_ms']} m/s")
    print(f"  Kulkusuunta (Heading)  : {kinematics['heading_deg']}°")
    print(
        f"  ARVIOITU NOPEUS        : {kinematics['speed_knots']} solmua "
        f"({kinematics['speed_kmh']} km/h)"
    )

    print("\n=== VAIHE 6: VALMIS ANALYYSIKUVA (VISUALIZER) ===")
    create_final_report_image(meta, ship_data, wake_data, kinematics)


if __name__ == "__main__":
    main()
