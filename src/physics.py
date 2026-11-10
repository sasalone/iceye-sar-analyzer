"""Moduuli 4: SAR Doppler -kinematiikka ja aluksen nopeuslaskenta."""

import os
import json
import math


def calculate_vessel_kinematics(
    meta: dict, ship_data: dict, wake_data: dict
) -> dict:
    """
    Laskee aluksen atsimuuttisiirtymän, säteittäisen nopeuden, todellisen
    nopeuden (solmuina ja km/h) sekä kompassisuunnan STAC-metatietojen avulla.
    """
    pixel_res_m = float(meta["effective_pixel_m"])
    inc_deg = float(meta["incidence_angle_deg"])
    inc_rad = math.radians(inc_deg)
    sat_alt_m = float(meta.get("sat_altitude_m", 530000.0))
    sat_vel_ms = float(meta.get("sat_velocity_ms", 7600.0))
    mode = str(meta.get("instrument_mode", "UNKNOWN")).upper()

    # 1. Lasketaan Slant Range (etäisyys satelliitista kohteeseen)
    slant_range_m = sat_alt_m / max(math.cos(inc_rad), 0.1)

    # 2. Lasketaan atsimuuttisiirtymä pikseleinä ja metreinä
    ship_x, ship_y = ship_data["center_xy"]
    apex_x, apex_y = wake_data["apex_xy"]
    tail_x, tail_y = wake_data["tail_xy"]

    shift_px = math.hypot(ship_x - apex_x, ship_y - apex_y)
    shift_m = shift_px * pixel_res_m

    # 3. Lasketaan kulkusuuntavektori
    vec_x = apex_x - tail_x
    vec_y = apex_y - tail_y

    # Kompassisuunta asteina 
    heading_rad = math.atan2(vec_x, -vec_y)
    heading_deg = (math.degrees(heading_rad) + 360.0) % 360.0

    # Kulkukulma suhteessa tutkan katselusuuntaan
    range_angle_rad = math.atan2(vec_y, vec_x)
    cos_phi = max(abs(math.cos(range_angle_rad)), 0.25)

    # 4. SAR Doppler -nopeuslaskenta
    v_radial_ms = (shift_m * sat_vel_ms) / slant_range_m
    v_ground_ms = v_radial_ms / max(math.sin(inc_rad), 0.1)
    true_speed_ms = v_ground_ms / cos_phi

    speed_knots = true_speed_ms * 1.94384
    speed_kmh = true_speed_ms * 3.6

    return {
        "imaging_mode": mode,
        "slant_range_km": round(slant_range_m / 1000.0, 1),
        "azimuth_shift_px": round(shift_px, 1),
        "azimuth_shift_m": round(shift_m, 1),
        "radial_velocity_ms": round(v_radial_ms, 2),
        "true_speed_ms": round(true_speed_ms, 2),
        "speed_knots": round(speed_knots, 1),
        "speed_kmh": round(speed_kmh, 1),
        "heading_deg": round(heading_deg, 1),
    }


def save_kinematics_report(
    kinematics: dict, data_dir: str = "data"
) -> str:
    """Tallentaa lasketut fysiikkatulokset JSON-tiedostoon."""
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "kinematics_results.json")
    with open(out_path, "w", encoding="utf-8") as file_obj:
        json.dump(kinematics, file_obj, indent=4)
    return out_path
