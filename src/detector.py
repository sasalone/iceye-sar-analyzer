"""Moduuli 2: Aluksen alipikselitarkka segmentointi, mittaus ja visualisointi."""

import numpy as np
import cv2


def detect_and_segment_ship(
    roi_gray: np.ndarray,
    pixel_res_m: float = 1.0,
    target_min_width: int = 600,
) -> dict:
    """
    Suurentaa leikkeen alipikselitarkkuuteen, paikantaa aluksen kirkkaan ytimen
    ja laajentaa segmentoinnin kattamaan koko aluksen vaalean rungon.
    """
    orig_h, orig_w = roi_gray.shape[:2]
    scale = max(1.0, target_min_width / float(orig_w))
    up_w, up_h = int(orig_w * scale), int(orig_h * scale)

    # 1. Suurennetaan kuva bikubisella interpoloinnilla sulavia ääriviivoja varten
    norm_img = cv2.normalize(roi_gray, None, 0, 255, cv2.NORM_MINMAX)
    upscaled = cv2.resize(
        norm_img, (up_w, up_h), interpolation=cv2.INTER_CUBIC
    )

    # 2. Säilytetään terävät reunat bilateraalisuodattimella (ei medianBluria)
    denoised = cv2.bilateralFilter(upscaled, d=7, sigmaColor=45, sigmaSpace=45)

    # 3. Vaihe A: Etsitään ensin laivan kirkkain ydin (ankkuripiste), jotta
    # emme vahingossa valitse taustan aaltoja
    core_thresh = max(160.0, float(np.percentile(denoised, 99.0)))
    _, core_mask = cv2.threshold(denoised, core_thresh, 255, cv2.THRESH_BINARY)
    core_contours, _ = cv2.findContours(
        core_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not core_contours:
        raise ValueError("Kuvasta ei löytynyt selkeää laivaheijastusta.")

    best_core = max(core_contours, key=cv2.contourArea)
    moments_core = cv2.moments(best_core)
    core_x = int(moments_core["m10"] / max(moments_core["m00"], 1.0))
    core_y = int(moments_core["m01"] / max(moments_core["m00"], 1.0))

    # 4. Vaihe B: Kynnystetään koko laivan runko (keula ja perä mukaan)
    # Käytetään meritaustan mediaania + keskihajontaa (CFAR-periaate)
    bg_median = float(np.median(denoised))
    bg_std = float(np.std(denoised))
    hull_thresh = min(135.0, max(bg_median + 2.8 * bg_std, 75.0))

    _, hull_mask = cv2.threshold(
        denoised, hull_thresh, 255, cv2.THRESH_BINARY
    )

    # Yhdistetään rungon osat vaakapainotteisella ellipsillä
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 5))
    hull_mask = cv2.morphologyEx(hull_mask, cv2.MORPH_CLOSE, kernel)

    hull_contours, _ = cv2.findContours(
        hull_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )

    # Valitaan se laajempi ääriviiva, jonka sisällä kirkas ydin sijaitsee
    ship_contour = best_core
    for cnt in hull_contours:
        if cv2.pointPolygonTest(cnt, (core_x, core_y), False) >= 0:
            ship_contour = cnt
            break

    # Pehmennetään ääriviivaa kevyesti luonnollisen muodon saamiseksi
    epsilon = 0.008 * cv2.arcLength(ship_contour, True)
    smooth_contour = cv2.approxPolyDP(ship_contour, epsilon, True)

    moments = cv2.moments(smooth_contour)
    center_x = int(moments["m10"] / max(moments["m00"], 1.0))
    center_y = int(moments["m01"] / max(moments["m00"], 1.0))

    # 5. Lasketaan todelliset mitat (jaetaan skaalauskertoimella takaisin)
    rect = cv2.minAreaRect(smooth_contour)
    (_, _), (dim1_up, dim2_up), angle_deg = rect
    length_px = max(dim1_up, dim2_up) / scale
    width_px = min(dim1_up, dim2_up) / scale
    area_px2 = cv2.contourArea(smooth_contour) / (scale ** 2)

    return {
        "center_xy": (int(center_x / scale), int(center_y / scale)),
        "upscaled_center_xy": (center_x, center_y),
        "upscaled_contour": smooth_contour,
        "upscaled_gray": upscaled,
        "scale_factor": scale,
        "length_m": round(length_px * pixel_res_m, 1),
        "width_m": round(width_px * pixel_res_m, 1),
        "area_m2": round(area_px2 * (pixel_res_m ** 2), 1),
        "orientation_deg": round(float(angle_deg), 1),
    }


def render_segmented_ship(
    roi_gray: np.ndarray, ship_data: dict
) -> np.ndarray:
    """
    Piirtää alipikselitarkan visualisoinnin, jossa koko laivan runko
    on väritetty ja ympäröity sulavalla ääriviivalla.
    """
    _ = roi_gray
    upscaled = ship_data["upscaled_gray"]
    new_w = upscaled.shape[1]

    canvas = cv2.cvtColor(upscaled, cv2.COLOR_GRAY2BGR)
    overlay = canvas.copy()

    contour = ship_data["upscaled_contour"]
    cx, cy = ship_data["upscaled_center_xy"]

    fill_color = (40, 60, 255)     # Punainen/oranssi täyttö
    outline_color = (0, 230, 255)  # Keltainen ääriviiva
    center_color = (0, 255, 100)   # Vihreä keskipiste

    # 1. Väritetään laivan runko puoliläpinäkyvästi
    cv2.drawContours(overlay, [contour], -1, fill_color, thickness=cv2.FILLED)
    canvas = cv2.addWeighted(overlay, 0.38, canvas, 0.62, 0)

    # 2. Piirretään ohut ja tarkka ääriviiva koko rungon ympärille
    cv2.drawContours(
        canvas, [contour], -1, outline_color, thickness=2, lineType=cv2.LINE_AA
    )
    cv2.circle(canvas, (cx, cy), 4, center_color, -1, lineType=cv2.LINE_AA)

    # 3. Yläpalkki ja päivitetyt mittatiedot
    cv2.rectangle(canvas, (0, 0), (new_w, 34), (15, 20, 25), -1)
    label = (
        f"SHIP: {ship_data['length_m']}m x {ship_data['width_m']}m "
        f"(RCS: {ship_data['area_m2']} m2)"
    )
    cv2.putText(
        canvas,
        label,
        (12, 23),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        outline_color,
        1,
        cv2.LINE_AA,
    )

    return canvas
