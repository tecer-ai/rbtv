# Where probe runs write. Sourced by probe.sh / run.sh / amend.sh.
#
# NOT inside the product tree. A raw agent transcript quotes the skill files and the fixtures
# verbatim, so run artifacts left under the product tree make the seam validator's
# attestation-boundary grep and m3's zero-destination-literals grep fire on probe output.
# Evidence is not product. Override with RUNS_ROOT.
_default_runs_root() {
  local here="$1"
  printf '%s\n' "$here/../../../../../../../goals/transcript-summarizer-build/seats/skill-unattender/outputs/m4-runs"
}
