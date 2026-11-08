from src.fetcher import get_or_create_roi

# Valittu ICEYE STAC -kohde
STAC_URL = "https://iceye-open-data-catalog.s3.amazonaws.com/stac-items/2025/05/ICEYE_6MC5KR_20250526T033241Z_4770346_X31_SLEDF.json"

def main():
    print("=== SAR DARK VESSEL ANALYZER - VAIHE 1 (FETCHER) ===")
    # Aseta force_reload=True, jos haluat valita uuden laivan kuvasta
    roi_img, meta = get_or_create_roi(STAC_URL, force_reload=False)

    print("\n--- LADATUN LEIKKEEN TIEDOT ---")
    print(f"  Kohde-ID               : {meta['item_id']}")
    print(f"  Satelliitti & Tila     : {meta['platform']} ({meta['instrument_mode']})")
    print(f"  Katselukulma (theta)   : {meta['incidence_angle_deg']}°")
    print(f"  Kiertoradan suunta     : {meta['orbit_state']}")
    print(f"  Efektiivinen pikselikoko: {meta['effective_pixel_m']} m/px")
    print(f"  Leikkeen mitat         : {roi_img.shape[1]} x {roi_img.shape[0]} px")

if __name__ == "__main__":
    main()
