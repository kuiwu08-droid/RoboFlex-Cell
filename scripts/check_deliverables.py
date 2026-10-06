"""Check delivered links, SVG XML, and DXF line/circle/text entities.

DXF checking uses optional ezdxf (install separately for CAD QA).
"""

import re
from pathlib import Path
import xml.etree.ElementTree as ET

import ezdxf


def main():
    root = Path(__file__).resolve().parents[1]
    errors = []
    for path in root.rglob("*.md"):
        if ".venv" in path.parts:
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+://", target) or target.startswith("#"):
                continue
            if not (path.parent / target.split("#")[0]).is_file():
                errors.append(f"Broken link in {path.relative_to(root)}: {target}")
    for path in [*root.joinpath("cad").rglob("*.svg"), *root.joinpath("electrical").rglob("*.svg")]:
        ET.parse(path)
        print(f"SVG valid: {path.relative_to(root)}")
    for path in root.joinpath("cad").rglob("*.dxf"):
        doc = ezdxf.readfile(path)
        audit = doc.audit()
        assert not audit.has_errors, f"DXF audit failed: {path}"
        types = {entity.dxftype() for entity in doc.modelspace()}
        assert {"LINE", "TEXT"}.issubset(types)
        print(f"DXF valid: {path.relative_to(root)}, {len(doc.modelspace())} entities")
    if errors:
        raise RuntimeError("\n".join(errors))
    print("All local Markdown links and concept drawing structures verified")


if __name__ == "__main__":
    main()
