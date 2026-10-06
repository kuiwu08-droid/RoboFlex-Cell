"""Generate the original concept SVGs and millimetre DXF from one geometry.

No SolidWorks/AutoCAD dependency. These are review sketches, not manufacturing
drawings or certified electrical schematics.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Drawing:
    def __init__(self, title, width=1000, height=700):
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
                    '<rect width="100%" height="100%" fill="#f9fbfc"/>',
                    '<g fill="none" stroke="#243e49" stroke-width="2">']
        self.dxf = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "0", "ENDSEC",
                    "0", "SECTION", "2", "ENTITIES"]
        self.height = height
        self.text(35, 35, title, 20)

    def line(self, x1, y1, x2, y2):
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
        self.dxf.extend(["0", "LINE", "8", "0", "10", str(x1), "20", str(self.height-y1),
                         "11", str(x2), "21", str(self.height-y2)])

    def rect(self, x, y, w, h):
        for points in [(x,y,x+w,y), (x+w,y,x+w,y+h), (x+w,y+h,x,y+h), (x,y+h,x,y)]:
            self.line(*points)

    def circle(self, x, y, r):
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}"/>')
        self.dxf.extend(["0", "CIRCLE", "8", "0", "10", str(x), "20", str(self.height-y), "40", str(r)])

    def text(self, x, y, value, size=14):
        self.svg.append(f'<text x="{x}" y="{y}" fill="#243e49" stroke="none" font-family="Segoe UI,Arial,sans-serif" font-size="{size}">{value}</text>')
        self.dxf.extend(["0", "TEXT", "8", "NOTES", "10", str(x), "20", str(self.height-y),
                         "40", str(size), "1", value])

    def save(self, name):
        target = ROOT / "cad" / "drawings"
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{name}.svg").write_text("\n".join(self.svg + ["</g></svg>"]), encoding="utf-8")
        (target / f"{name}.dxf").write_text("\n".join(self.dxf + ["0", "ENDSEC", "0", "EOF"]) + "\n", encoding="ascii")


def main():
    layout = Drawing("ROBOFLEX CELL / TOP PLAN / CONCEPT / mm", 1100, 850)
    layout.rect(70, 90, 900, 650)
    layout.text(420, 780, "900 x 650 table envelope")
    # Base coordinate X -> right, Y -> up. Drawing offset is (130, 450).
    layout.circle(130, 450, 55)
    layout.text(75, 525, "Robot base (schematic)")
    layout.rect(330, 250, 300, 220)
    layout.text(335, 235, "Calibrated ROI: X 200..500, Y -20..200")
    layout.rect(320, 270, 320, 170)
    layout.text(350, 300, "Conveyor / stopped-part vision")
    layout.rect(490, 480, 60, 50)
    layout.text(470, 558, "Fixture top Z=80")
    for y, label in [(550, "CIRCLE"), (450, "SQUARE"), (350, "RING")]:
        layout.rect(640, y-30, 100, 60)
        layout.text(755, y+5, label + " X540")
    layout.circle(330, 550, 10)
    layout.text(280, 590, "HOME (200,-100,160)")
    layout.line(130, 450, 220, 450)
    layout.line(130, 450, 130, 360)
    layout.text(226, 455, "+X")
    layout.text(122, 350, "+Y")
    layout.text(80, 820, "RF-M-001 | REV A | 2D concept only; robot reach/link collisions not validated", 15)
    layout.save("cell_layout")

    plate = Drawing("RF-M-002 / CAMERA MOUNT PLATE / CONCEPT / mm", 620, 460)
    plate.rect(180, 100, 120, 100)
    for x in (200, 280):
        for y in (120, 180):
            plate.circle(x, y, 4.5)
    plate.line(180, 230, 300, 230)
    plate.line(180, 210, 180, 240)
    plate.line(300, 210, 300, 240)
    plate.text(223, 254, "120")
    plate.line(330, 100, 330, 200)
    plate.text(340, 155, "100")
    plate.text(180, 290, "4 x diameter 9 THRU / hole pitch 80 x 60")
    plate.text(180, 320, "Plate thickness: 8 / aluminium concept")
    plate.text(35, 405, "Camera adapter pattern, stiffness and tolerances require vendor data.")
    plate.save("camera_plate")

    tray = Drawing("RF-M-003 / SAMPLE TRAY / CONCEPT / mm", 650, 440)
    tray.rect(160, 100, 200, 120)
    tray.circle(210, 160, 18)
    tray.rect(243, 143, 34, 34)
    tray.circle(310, 160, 18)
    tray.text(160, 250, "200 x 120 x 15 / pocket depth 6")
    tray.text(160, 280, "Circle &amp; ring pocket diameter 36 / square pocket 34")
    # DXF text is plain text, not XML.
    tray.dxf[-1] = tray.dxf[-1].replace("&amp;", "&")
    tray.text(35, 380, "Nominal parts: circle/ring diameter 28, square 25; confirm actual clearance.")
    tray.save("sample_tray")


if __name__ == "__main__":
    main()
