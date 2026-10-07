"""Builds the throwaway installation, then runs every check section in order.

The order below IS the suite: sections are not independent — one installs what
the next one reads — so it is written out here rather than discovered, and a
section's module membership says what it is about, never when it runs.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from discovery import Refuse, scan_all

from lib.constants import _RUNTIME
from lib.pathlinks import _forbid_local_bin, bin_dir

from .context import Ctx
from .fixture import _fixture
from . import (test_agents, test_cli, test_discovery, test_doctor_ownership, test_guidance, test_guidance_walk,
               test_hub, test_install, test_interactive, test_layout, test_link_paths,
               test_ownership, test_parts, test_pathlinks, test_settings,
               test_surface, test_files, test_files_key, test_ux_contract, test_packs,
               test_providers, test_subagents, test_component_merge,
               test_listing_types)

ORDER = [
    test_layout.repo_root_is_the_repo,
    test_discovery.scan,
    test_discovery.depth_two_is_the_marker,
    test_discovery.three_harnesses,
    test_discovery.predecessor_sweep_cannot_reach,
    test_files.schema_and_frontmatter,
    test_files.component_sections,
    test_files.legacy_names,
    test_files.translations,
    test_agents.installed_agents,
    test_agents.agent_ignore_file,
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
    test_hub.hub_alias,
    test_hub.hub_book_key_rewrite,
    test_ownership.the_marker_is_ownership,
    test_ownership.gitignore_block,
    test_settings.installation_settings,
    test_settings.file_selection_sync,
    test_settings.rule_channels,
    test_files_key.old_key_read_and_rewritten,
    test_link_paths.links_rewritten_on_copy,
    test_parts.vanished_component_removable,
    test_parts.part_level_install_remove,
    test_parts.part_level_claim_release,
    test_parts.vanished_component_part_rm,
    test_parts.v1_to_v2_upgrade,
    test_parts.legacy_records_gain_selection_fields_on_write,
    test_packs.packs,
    test_subagents.sub_agents,
    test_listing_types.listing_types,
    test_cli.parser_selectors_index,
    test_cli.result_classes,
    test_cli.cli_defects,
    test_pathlinks.path_links,
    test_component_merge.record_rewrite,
    test_component_merge.update_after_rewrite,
    test_doctor_ownership.doctor_ownership,
    test_surface.ls_li_doctor,
    test_providers.provider_accounts,
    test_ux_contract.public_contract,
    test_ux_contract.result_screens,
    test_install.uninstall,
]


def selftest() -> int:
    ctx = Ctx()
    real_bin = Path.home() / ".rbtv" / "bin"

    def bin_listing() -> tuple:
        if not real_bin.is_dir():
            return (False, ())
        entries = []
        for p in real_bin.iterdir():
            kind = "link" if p.is_symlink() else "file" if p.is_file() else "dir"
            body = (os.fsencode(os.readlink(p)) if kind == "link" else
                    p.read_bytes() if kind == "file" else b"")
            entries.append((p.name, kind, body))
        return (True, tuple(sorted(entries)))

    before_bin = bin_listing()
    real_owners = real_bin.parent / "path-owners.json"
    before_owners = real_owners.read_bytes() if real_owners.exists() else None
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
        mirror = tmp / "mirror"
        _fixture(tree, mirror)
        target = tmp / "installation"
        target.mkdir()
        catalog, shadowed = scan_all(mirror, tree)

        ctx.tmp, ctx.tree, ctx.target = tmp, tree, target
        ctx.mirror = mirror
        ctx.shadowed = shadowed
        ctx.keep({"catalog": catalog})
        for section in ORDER:
            section(ctx)

        ctx.check("L-real-bin-untouched — selftest leaves ~/.rbtv/bin "
                  "byte-identical", bin_listing() == before_bin)
        ctx.check("L-real-owners-untouched — selftest leaves shared ownership "
                  "byte-identical", (real_owners.read_bytes()
                                     if real_owners.exists() else None)
                  == before_owners)

        _RUNTIME["bin"] = None
        _RUNTIME["rc"] = None
        _RUNTIME["local"] = None

    print(f"\nselftest: {'PASS' if ctx.ok else 'FAIL'}")
    return 0 if ctx.ok else 1
