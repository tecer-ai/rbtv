"""Builds the throwaway workspace, then runs every check section in order.

The order below IS the suite: sections are not independent — one installs what
the next one reads — so it is written out here rather than discovered, and a
section's module membership says what it is about, never when it runs.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from discovery import Refuse, scan_all

from lib.constants import _RUNTIME
from lib.pathlinks import _forbid_local_bin, bin_dir

from .context import Ctx
from .fixture import _fixture
from . import (test_cli, test_discovery, test_guidance, test_guidance_walk,
               test_hub, test_install, test_interactive, test_layout,
               test_ownership, test_parts, test_pathlinks, test_settings,
               test_surface)

ORDER = [
    test_layout.repo_root_is_the_repo,
    test_discovery.scan,
    test_discovery.depth_two_is_the_marker,
    test_discovery.three_harnesses,
    test_discovery.predecessor_sweep_cannot_reach,
    test_install.green_arm_all_harnesses,
    test_install.red_unknown_method,
    test_install.red_foreign_collision,
    test_install.harness_filter,
    test_guidance.the_guidance_mirror,
    test_guidance.red_garbage_basis,
    test_guidance.red_foreign_mirror,
    test_guidance.f1_flip_keeps_the_users_file,
    test_guidance.f2_missing_basis_names_recovery,
    test_guidance.f3_uninstall_never_blocked,
    test_guidance.f6_non_utf8_basis,
    test_guidance_walk.r1_recursive_walk,
    test_guidance_walk.r2_flip_protects_every_dir,
    test_guidance_walk.r3_deep_foreign_mirror,
    test_guidance_walk.r4_adoption,
    test_guidance_walk.h_harness_keyed,
    test_guidance_walk.h6_retired_index_cleaned,
    test_guidance_walk.h7_block_never_stacks,
    test_guidance_walk.rf1_forced_read_step_zero,
    test_guidance_walk.rf2_dry_run_reports_the_block,
    test_guidance_walk.rf3_flip_debanners_the_basis,
    test_install.dry_run_prints_the_report_rows,
    test_interactive.guided_flow,
    test_interactive.fumbled_answers_reask,
    test_interactive.zero_width_terminal,
    test_hub.skills_folder_copied_whole,
    test_hub.hub_units,
    test_hub.hub_book_key_rewrite,
    test_ownership.the_marker_is_ownership,
    test_ownership.gitignore_block,
    test_settings.workspace_settings,
    test_parts.vanished_component_removable,
    test_parts.part_level_install_remove,
    test_parts.part_level_claim_release,
    test_parts.vanished_component_part_rm,
    test_parts.v1_to_v2_upgrade,
    test_cli.parser_selectors_index,
    test_pathlinks.path_links,
    test_surface.ls_li_doctor,
    test_install.uninstall,
]


def selftest() -> int:
    ctx = Ctx()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        _RUNTIME["bin"] = tmp / "rbtv-bin"
        _RUNTIME["rc"] = tmp / "fake-bashrc"
        _RUNTIME["local"] = tmp / "fake-local-bin"
        if (bin_dir().resolve() == (Path.home() / ".rbtv" / "bin")
                or not str(bin_dir().resolve()).startswith(str(tmp.resolve()))
                or bin_dir().resolve()
                == (Path.home() / ".local" / "bin").resolve()):
            _RUNTIME["bin"] = None
            _RUNTIME["rc"] = None
            _RUNTIME["local"] = None
            print("FATAL: PATH bin dir was not rebound — refusing to run")
            return 1
        try:
            _forbid_local_bin(Path.home() / ".local" / "bin")
            ctx.check("L-forbid-local-bin — hardcoded ~/.local/bin is refused",
                      False, "no refusal")
        except Refuse as exc:
            ctx.check("L-forbid-local-bin — hardcoded ~/.local/bin is refused",
                      exc.code == "path-forbidden", exc.code)
        tree = tmp / "tree"
        tree.mkdir()
        _fixture(tree)
        target = tmp / "workspace"
        target.mkdir()
        catalog, shadowed = scan_all(tmp / "no-mirror", tree)

        ctx.tmp, ctx.tree, ctx.target = tmp, tree, target
        ctx.shadowed = shadowed
        ctx.keep({"catalog": catalog})
        for section in ORDER:
            section(ctx)

        _RUNTIME["bin"] = None
        _RUNTIME["rc"] = None
        _RUNTIME["local"] = None

    print(f"\nselftest: {'PASS' if ctx.ok else 'FAIL'}")
    return 0 if ctx.ok else 1
