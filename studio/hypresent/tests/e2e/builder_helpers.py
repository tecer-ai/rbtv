"""Shared helpers for builder e2e suites (stdlib + playwright only)."""
import json
import os
import shutil
import tempfile

import conftest_helpers as H

HERE = os.path.dirname(os.path.abspath(__file__))
BUILDER_LIB = os.path.join(HERE, "fixtures", "builder-lib")
ENGINE_SRC = os.path.join(BUILDER_LIB, "assemble.py")
ARCHIVE_SRC = os.path.join(BUILDER_LIB, "archive.py")


def set_fake_folder(base, path_or_none):
    """Install the server-side fake folder dialog launcher (requires HYP_TEST_DIALOG=1)."""
    return H.post_json(base, "/api/_test/set-folder-dialog", {"path": path_or_none})


def e2e_lib_path():
    """Absolute path to the committed builder-lib fixture."""
    return BUILDER_LIB


def make_temp_library():
    """Copy builder-lib (and any sibling extra-root) into a fresh tempdir.
    Ensure the engine is present at {tmp}/builder-lib/assemble.py.
    Return the temp library abs path.
    """
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "builder-lib")
    shutil.copytree(BUILDER_LIB, dst)
    # Ensure the vendored engine is fresh
    engine_dst = os.path.join(dst, "assemble.py")
    shutil.copy(ENGINE_SRC, engine_dst)
    if os.path.exists(ARCHIVE_SRC):
        shutil.copy(ARCHIVE_SRC, os.path.join(dst, "archive.py"))
    return dst


def make_overcap_library(min_slides=30):
    """Copy builder-lib to a temp dir and synthesize duplicate slides until >= min_slides.
    Returns the temp library abs path."""
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "builder-lib")
    shutil.copytree(BUILDER_LIB, dst)
    # Ensure the vendored engine is fresh
    engine_dst = os.path.join(dst, "assemble.py")
    if not os.path.exists(engine_dst):
        shutil.copy(ENGINE_SRC, engine_dst)

    # Read library.json for valid sections
    with open(os.path.join(dst, "library.json"), "r", encoding="utf-8") as f:
        lib_data = json.load(f)
    sections = lib_data.get("sections", [])

    # Read existing manifest
    manifest_path = os.path.join(dst, "manifest.md")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = f.read()

    # Find the template row to duplicate (simplest: intro-e2e, no assets)
    lines = manifest.splitlines()
    template_row = None
    template_cells = None
    for line in lines:
        if line.startswith("|") and "intro-e2e" in line and "intro-e2e.en" not in line:
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if len(cells) == 10:
                template_row = line
                template_cells = cells
                break

    if template_cells is None:
        raise RuntimeError("Could not find intro-e2e template row in manifest")

    # Read template fragment
    src_frag = os.path.join(dst, template_cells[1])
    with open(src_frag, "r", encoding="utf-8") as f:
        frag_text = f.read()

    # Count existing slide rows (data rows only, excluding header and separator)
    existing_data_rows = 0
    in_slides = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Slides"):
            in_slides = True
            continue
        if in_slides and stripped.startswith("## "):
            break
        if in_slides and stripped.startswith("|") and not stripped.startswith("| id") and "---" not in stripped:
            existing_data_rows += 1

    # Generate copies
    new_lines = []
    current_count = existing_data_rows
    copy_num = 1
    while current_count < min_slides:
        new_id = f"intro-e2e-pillars-d{copy_num}"
        new_file = f"slides/{new_id}.html"
        new_frag_path = os.path.join(dst, new_file)

        with open(new_frag_path, "w", encoding="utf-8") as f:
            f.write(frag_text)

        new_cells = template_cells[:]
        new_cells[0] = new_id
        new_cells[1] = new_file
        new_cells[3] = f"Introduction copy {copy_num}"
        new_lines.append("| " + " | ".join(new_cells) + " |")

        current_count += 1
        copy_num += 1

    # Insert new rows before ## Assets
    insert_idx = len(lines)
    for i, line in enumerate(lines):
        if line.strip() == "## Assets":
            insert_idx = i
            break

    new_manifest = lines[:insert_idx] + new_lines + lines[insert_idx:]
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_manifest) + "\n")

    return dst


def pick_library_ui(page, base, lib_path):
    """Set fake folder dialog to lib_path, click Pick library, wait for browse-groups children."""
    set_fake_folder(base, lib_path)
    page.click("#pick-library-btn")
    page.wait_for_function(
        """() => {
            const el = document.getElementById('browse-groups');
            return el && el.children.length > 0;
        }""",
        timeout=10000,
    )
