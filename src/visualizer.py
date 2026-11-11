"""Moduuli 5: Lopullisen taktisen tilannekuvan ja telemetriapaneelin koonti."""

import os
import numpy as np
import cv2


def _draw_map_vectors(
    canvas: np.ndarray, ship_data: dict, wake_data: dict
) -> np.ndarray:
    """Piirtää laivan segmentoinnin, perävanan ja suuntavektorit karttapohjaan."""
    overlay = canvas.copy()
    contour = ship_data["upscaled_contour"]
    cx, cy = ship_data["upscaled_center_xy"]
    ax, ay = wake_data["upscaled_apex_xy"]
    tx, ty = wake_data["upscaled_tail_xy"]

    red_fill = (40, 60, 255)
    yellow = (0, 230, 255)
    green = (80, 255, 0)
    cyan = (255, 240, 0)
    amber = (0, 180, 255)

    # 1. Väritetään laiva
    cv2.drawContours(overlay, [contour], -1, red_fill, thickness=cv2.FILLED)
    canvas = cv2.addWeighted(overlay, 0.42, canvas, 0.58, 0)
    cv2.drawContours(canvas, [contour], -1, yellow, thickness=2, lineType=cv2.LINE_AA)
    cv2.circle(canvas, (cx, cy), 4, yellow, -1, lineType=cv2.LINE_AA)

    # 2. Piirretään perävana
    cv2.line(canvas, (ax, ay), (tx, ty), cyan, 2, lineType=cv2.LINE_AA)
    cv2.circle(canvas, (tx, ty), 4, cyan, -1, lineType=cv2.LINE_AA)

    # 3. Piirretään atsimuuttisiirtymä
    cv2.arrowedLine(
        canvas, (ax, ay), (cx, cy), amber, 2, cv2.LINE_AA, tipLength=0.08
    )

    # 4. Piirretään todellinen sijainti ja kulkusuuntanuoli
    cv2.circle(canvas, (ax, ay), 6, green, 2, lineType=cv2.LINE_AA)
    dx, dy = ax - tx, ay - ty
    norm = max(float(np.hypot(dx, dy)), 1.0)
    hx = int(ax + (dx / norm) * 60)
    hy = int(ay + (dy / norm) * 60)
    cv2.arrowedLine(
        canvas, (ax, ay), (hx, hy), green, 2, cv2.LINE_AA, tipLength=0.25
    )

    # Paikalliset pienet selitteet kohteiden viereen
    cv2.putText(
        canvas,
        "DOPPLER GHOST",
        (cx + 12, cy - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        yellow,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "TRUE POS (Apex)",
        (ax + 12, ay + 16),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        green,
        1,
        cv2.LINE_AA,
    )
    return canvas


def _draw_telemetry_panel(
    panel_h: int,
    panel_w: int,
    meta: dict,
    ship_data: dict,
    kinematics: dict,
) -> np.ndarray:
    """Luo oikeanpuoleisen telemetriapaneelin tuloksille."""
    panel = np.full((panel_h, panel_w, 3), (18, 22, 28), dtype=np.uint8)

    cyan = (255, 240, 0)
    green = (80, 255, 0)
    yellow = (0, 230, 255)
    amber = (0, 180, 255)
    white = (230, 230, 230)
    gray = (150, 155, 165)

    # Vasen reunaviiva erottamaan kartta ja paneeli
    cv2.line(panel, (0, 0), (0, panel_h), (60, 75, 90), 2)

    sections = [
        ("SAR TELEMETRY REPORT", cyan, 0.62, 2, 38),
        ("1. SENSOR & ACQUISITION", yellow, 0.48, 1, 80),
        (f"Platform       : {meta['platform']}", white, 0.44, 1, 106),
        (f"Imaging Mode   : {kinematics['imaging_mode']}", white, 0.44, 1, 128),
        (f"Orbit State    : {meta['orbit_state']}", white, 0.44, 1, 150),
        (
            f"Incidence Angle: {meta['incidence_angle_deg']:.1f} deg",
            white,
            0.44,
            1,
            172,
        ),
        (f"Slant Range    : {kinematics['slant_range_km']} km", white, 0.44, 1, 194),
        ("2. VESSEL DIMENSIONS", yellow, 0.48, 1, 240),
        (f"Est. Length    : {ship_data['length_m']} m", white, 0.44, 1, 266),
        (f"Est. Width     : {ship_data['width_m']} m", white, 0.44, 1, 288),
        (f"Radar Footprint: {ship_data['area_m2']} m2", white, 0.44, 1, 310),
        ("3. DOPPLER KINEMATICS", yellow, 0.48, 1, 356),
        (
            f"Azimuth Shift  : {kinematics['azimuth_shift_m']} m "
            f"({kinematics['azimuth_shift_px']} px)",
            amber,
            0.44,
            1,
            382,
        ),
        (
            f"Radial Vel (Vr): {kinematics['radial_velocity_ms']} m/s",
            white,
            0.44,
            1,
            404,
        ),
        (
            f"True Heading   : {kinematics['heading_deg']} deg",
            green,
            0.46,
            1,
            430,
        ),
        (
            f"EST. SPEED     : {kinematics['speed_knots']} kn "
            f"({kinematics['speed_kmh']} km/h)",
            green,
            0.52,
            2,
            462,
        ),
    ]

    for text, color, scale, thickness, y_pos in sections:
        if y_pos < panel_h - 60:
            cv2.putText(
                panel,
                text,
                (20, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale,
                color,
                thickness,
                cv2.LINE_AA,
            )

    # Värikoodien selite alareunaan
    leg_y = panel_h - 45
    cv2.line(panel, (20, leg_y - 15), (panel_w - 20, leg_y - 15), (45, 55, 65), 1)
    cv2.putText(
        panel,
        "Yellow: SAR Ghost | Green: True Pos & Course | Cyan: Wake",
        (20, leg_y + 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.36,
        gray,
        1,
        cv2.LINE_AA,
    )

    return panel


def create_final_report_image(
    meta: dict,
    ship_data: dict,
    wake_data: dict,
    kinematics: dict,
    data_dir: str = "data",
) -> str:
    """
    Yhdistää vektoroidun SAR-kuvan ja telemetriapaneelin yhdeksi
    valmiiksi raporttikuvaksi ja tallentaa sen.
    """
    os.makedirs(data_dir, exist_ok=True)
    upscaled_gray = ship_data["upscaled_gray"]
    map_canvas = cv2.cvtColor(upscaled_gray, cv2.COLOR_GRAY2BGR)

    # Vähintään 520 px korkeus, jotta paneeli mahtuu kokonaan
    map_h, map_w = map_canvas.shape[:2]
    if map_h < 520:
        scale_up = 520.0 / float(map_h)
        new_w, new_h = int(map_w * scale_up), 520
        map_canvas = cv2.resize(
            map_canvas, (new_w, new_h), interpolation=cv2.INTER_CUBIC
        )
        # Päivitetään piirtokoordinaatit vastaamaan uutta korkeutta
        ship_copy = dict(ship_data)
        wake_copy = dict(wake_data)
        ship_copy["upscaled_contour"] = (
            ship_data["upscaled_contour"].astype(np.float32) * scale_up
        ).astype(np.int32)
        ship_copy["upscaled_center_xy"] = (
            int(ship_data["upscaled_center_xy"][0] * scale_up),
            int(ship_data["upscaled_center_xy"][1] * scale_up),
        )
        wake_copy["upscaled_apex_xy"] = [
            int(wake_data["upscaled_apex_xy"][0] * scale_up),
            int(wake_data["upscaled_apex_xy"][1] * scale_up),
        ]
        wake_copy["upscaled_tail_xy"] = [
            int(wake_data["upscaled_tail_xy"][0] * scale_up),
            int(wake_data["upscaled_tail_xy"][1] * scale_up),
        ]
    else:
        ship_copy = ship_data
        wake_copy = wake_data

    annotated_map = _draw_map_vectors(map_canvas, ship_copy, wake_copy)
    final_h = annotated_map.shape[0]
    panel_w = 370

    telemetry_panel = _draw_telemetry_panel(
        final_h, panel_w, meta, ship_data, kinematics
    )
    combined = np.hstack((annotated_map, telemetry_panel))

    out_path = os.path.join(data_dir, "final_sar_analysis.png")
    cv2.imwrite(out_path, combined)
    print(f"[Visualizer] Valmis analyysikuva tallennettu -> {out_path}")

    win_name = "Moduuli 5 (Visualizer): Valmis SAR-analyysi (Paina ENTER sulkeaksesi)"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, combined.shape[1], combined.shape[0])
    cv2.imshow(win_name, combined)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return out_path
