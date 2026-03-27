import re
from pathlib import Path
from bootstrap.core.yaml_parser import read_yaml_field, read_yaml_nested_field

def parse_version(version_str: str):
    """
    Parse a version string like 6.0.0-Beta.4 into a comparable tuple.
    Pre-release: Beta < RC < (no pre-release).
    """
    v = version_str.strip().lstrip("v")
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z]+)\.(\d+))?$', v)
    if not m:
        return (0, 0, 0, "z", 0)

    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre_label = m.group(4).lower() if m.group(4) else ""
    pre_num = int(m.group(5)) if m.group(5) else 0

    label_order = {"beta": 0, "rc": 1, "": 2}
    label_key = label_order.get(pre_label, 0)

    return (major, minor, patch, label_key, pre_num)

def check_bmad_version(rbtv_dir: Path, root: Path) -> dict:
    """Pre-flight BMAD version check."""
    compat_file = rbtv_dir / "bmad-compat.yaml"
    if not compat_file.exists():
        return {"status": "unknown", "message": "bmad-compat.yaml not found — skipping version check"}

    compat_text = compat_file.read_text(encoding="utf-8")
    target_version = read_yaml_field(compat_text, "bmad_target_version")
    min_version = read_yaml_field(compat_text, "bmad_min_version")

    if not target_version:
        return {"status": "unknown", "message": "bmad_target_version not found in bmad-compat.yaml"}

    manifest_file = root / "_bmad" / "_config" / "manifest.yaml"
    if not manifest_file.exists():
        return {
            "status": "unknown",
            "message": (
                f"WARNING: _bmad/_config/manifest.yaml not found at {root}.\n"
                f"         BMAD may not be installed. RBTV expects BMAD {target_version}.\n"
                "         Proceeding — run installer again after BMAD is installed."
            )
        }

    manifest_text = manifest_file.read_text(encoding="utf-8")
    installed_version = read_yaml_nested_field(manifest_text, "installation", "version")
    if not installed_version:
        installed_version = read_yaml_field(manifest_text, "version")

    if not installed_version:
        return {
            "status": "unknown",
            "message": "WARNING: Could not parse BMAD version from manifest.yaml — skipping check"
        }

    installed_v = parse_version(installed_version)
    target_v = parse_version(target_version)
    min_v = parse_version(min_version) if min_version else (0, 0, 0, 0, 0)

    if installed_v == target_v:
        return {
            "status": "ok",
            "message": f"BMAD version {installed_version} matches target — compatible"
        }
    elif installed_v >= min_v:
        return {
            "status": "warn",
            "message": (
                f"WARNING: BMAD {installed_version} differs from RBTV target ({target_version}).\n"
                f"         RBTV was tested against {target_version}. Proceeding — some features may behave differently.\n"
                "         Run tasks/check-bmad-compat.xml to evaluate compatibility before using RBTV."
            )
        }
    else:
        return {
            "status": "strong_warn",
            "message": (
                f"WARNING: BMAD {installed_version} is below RBTV minimum ({min_version}).\n"
                f"         RBTV requires at least {min_version}. Compatibility is not guaranteed.\n"
                "         Run tasks/check-bmad-compat.xml to evaluate compatibility before proceeding."
            )
        }

def print_version_check_result(result: dict) -> None:
    if result["status"] == "ok":
        print(f"  {result['message']}")
    else:
        for line in result["message"].splitlines():
            print(f"  {line}")
