"""Moduuli 3: Interaktiivinen työkalu perävanan merkitsemiseen."""

import os
import json
import numpy as np
import cv2


class WakeAnnotator:
    """Käsittelee hiiren klikkaukset ja piirtää perävanavektorin."""

    def __init__(self, base_canvas: np.ndarray, ship_center_up: tuple[int, int]):
        self.base_canvas = base_canvas.copy()
        self.display_canvas = base_canvas.copy()
        self.ship_center_up = ship_center_up
        self.points: list[tuple[int, int]] = []
        self.win_name = (
            "Moduuli 3 (Annotator): 1) Vanan karki  2) Vanan hanta "
            "| 'R'=Alusta, ENTER=Valmis"
        )

    def mouse_callback(self, event: int, x: int, y: int, _flags: int, _param):
        """Tallentaa kaksi klikkausta: kärjen ja hännän."""
        if event == cv2.EVENT_LBUTTONDOWN and len(self.points) < 2:
            self.points.append((x, y))
            self.redraw(show_ui_prompt=True)

    def redraw(self, show_ui_prompt: bool = True):
        """Päivittää vektorit ja piirtää ohjepalkin."""
        self.display_canvas = self.base_canvas.copy()
        height, width = self.display_canvas.shape[:2]

        cyan = (255, 240, 0)
        green = (80, 255, 0)
        amber = (0, 180, 255)

        # 1. piste: Perävanan kärki + Doppler-siirtymävektori
        if len(self.points) >= 1:
            ax, ay = self.points[0]
            cv2.circle(
                self.display_canvas, (ax, ay), 6, green, 2, lineType=cv2.LINE_AA
            )
            cv2.putText(
                self.display_canvas,
                "TRUE POS (Apex)",
                (ax + 10, ay + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                green,
                1,
                cv2.LINE_AA,
            )
            cv2.arrowedLine(
                self.display_canvas,
                (ax, ay),
                self.ship_center_up,
                amber,
                2,
                cv2.LINE_AA,
                tipLength=0.08,
            )

        # 2. piste: Perävanan häntä + Kulkusuuntanuoli
        if len(self.points) == 2:
            ax, ay = self.points[0]
            tx, ty = self.points[1]
            cv2.circle(
                self.display_canvas, (tx, ty), 4, cyan, -1, lineType=cv2.LINE_AA
            )
            cv2.line(
                self.display_canvas,
                (ax, ay),
                (tx, ty),
                cyan,
                2,
                lineType=cv2.LINE_AA,
            )

            dx = ax - tx
            dy = ay - ty
            norm = max(float(np.hypot(dx, dy)), 1.0)
            hx = int(ax + (dx / norm) * 55)
            hy = int(ay + (dy / norm) * 55)
            cv2.arrowedLine(
                self.display_canvas,
                (ax, ay),
                (hx, hy),
                green,
                2,
                cv2.LINE_AA,
                tipLength=0.25,
            )

        # Piirretään ohjepalkki
        if show_ui_prompt:
            cv2.rectangle(
                self.display_canvas,
                (0, height - 34),
                (width, height),
                (15, 20, 25),
                -1,
            )
            prompts = [
                "KLIKKAA 1/2: Peravanan KARKI (Laivan todellinen paikka)",
                "KLIKKAA 2/2: Peravanan HANTA (Mihin suuntaan vana jatkuu)",
                "VALMIS! Paina ENTER jatkaaksesi tai 'R' piirtaaksesi uudelleen",
            ]
            msg = prompts[len(self.points)]
            cv2.putText(
                self.display_canvas,
                msg,
                (12, height - 11),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                cyan,
                1,
                cv2.LINE_AA,
            )
            cv2.imshow(self.win_name, self.display_canvas)


def get_or_create_wake_annotation(
    segmented_canvas: np.ndarray,
    ship_data: dict,
    data_dir: str = "data",
    force_reannotate: bool = False,
) -> dict:
    """
    Lataa perävanan pisteet välimuistista tai avaa interaktiivisen ikkunan,
    jossa käyttäjä klikkaa perävanan kärjen ja hännän.
    """
    os.makedirs(data_dir, exist_ok=True)
    annot_path = os.path.join(data_dir, "wake_annotation.json")
    img_out_path = os.path.join(data_dir, "step3_annotated_wake.png")

    if not force_reannotate and os.path.exists(annot_path):
        print(f"[Annotator] Ladataan perävanan pisteet välimuistista ({annot_path})...")
        with open(annot_path, "r", encoding="utf-8") as file_obj:
            return json.load(file_obj)

    scale = float(ship_data["scale_factor"])
    ship_center_up = tuple(ship_data["upscaled_center_xy"])

    annotator = WakeAnnotator(segmented_canvas, ship_center_up)
    cv2.namedWindow(annotator.win_name, cv2.WINDOW_NORMAL)
    height, width = segmented_canvas.shape[:2]
    cv2.resizeWindow(annotator.win_name, max(700, width), max(700, height))
    cv2.setMouseCallback(annotator.win_name, annotator.mouse_callback)
    annotator.redraw(show_ui_prompt=True)

    print("\n>>> OHJE (Moduuli 3): <<<")
    print("  1. Klikkaa PERÄVANAN KÄRKEÄ (kohta, josta vana alkaa).")
    print("  2. Klikkaa PERÄVANAN HÄNTÄÄ (mihin vana jatkuu).")
    print("  Paina 'R' valitaksesi pisteet uudelleen tai ENTER hyväksyäksesi.")

    while True:
        key = cv2.waitKey(20) & 0xFF
        if key in (13, 32) and len(annotator.points) == 2:
            break
        if key == 27:
            cv2.destroyAllWindows()
            raise RuntimeError("Perävanan merkitseminen keskeytettiin (ESC).")
        if key in (ord("r"), ord("R")):
            annotator.points = []
            annotator.redraw(show_ui_prompt=True)

    cv2.destroyAllWindows()

    # Renderöidään puhdas kuva ilman alareunan ohjepalkkia tallennusta varten
    annotator.redraw(show_ui_prompt=False)

    apex_up = annotator.points[0]
    tail_up = annotator.points[1]

    apex_orig = [round(apex_up[0] / scale, 2), round(apex_up[1] / scale, 2)]
    tail_orig = [round(tail_up[0] / scale, 2), round(tail_up[1] / scale, 2)]

    wake_data = {
        "apex_xy": apex_orig,
        "tail_xy": tail_orig,
        "upscaled_apex_xy": list(apex_up),
        "upscaled_tail_xy": list(tail_up),
    }

    with open(annot_path, "w", encoding="utf-8") as file_obj:
        json.dump(wake_data, file_obj, indent=4)

    cv2.imwrite(img_out_path, annotator.display_canvas)
    print(f"[Annotator] Tallennettu perävanan koordinaatit -> {annot_path}")
    print(f"[Annotator] Tallennettu visualisointi -> {img_out_path}")

    return wake_data
