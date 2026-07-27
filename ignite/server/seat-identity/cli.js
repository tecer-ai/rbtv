'use strict';

// Task 7.11 §4b — the thin CLI over the identity checker.
//
// SCOPE, stated because the boundary is a ruling and not a preference: this is MECHANISM ONLY.
// Task 7.10 builds CMP-13 proper and wires this resolver into the gateway's D15 pluggable
// sender-identity seam (design §7); nothing here touches the gateway. It exists now because the
// pre-registered acceptance bars P4-P7 and P10 probe the command-time gate, and a bar that cannot
// be probed is not a bar — leader's ruling, #155.
//
// ⚠ IT TAKES NO IDENTITY ARGUMENT, AND THAT IS THE FEATURE. There is no `--as`, no `--seat`, no
// env var. Everything it reports is measured from the calling process: its cwd, its /proc
// ancestry, and the run's session log. Add a name-bearing flag here and you have rebuilt the
// exact hole G-111 opened tonight — an asserted identity outranking a verified one.
//
// Exit codes: 0 = identity confirmed. 1 = typed refusal (the code is on stdout as JSON and named
// in the human line on stderr). 2 = usage error.

const { checkIdentity } = require('./identity');

function main(argv) {
  const args = argv.slice(2);
  const json = args.includes('--json');
  const help = args.includes('-h') || args.includes('--help');
  const unknown = args.filter((a) => !['--json', '-h', '--help'].includes(a));

  if (help) {
    process.stdout.write(
      'rbtv-seat-identity — who is sitting in this seat?\n\n' +
      'usage: rbtv-seat-identity [--json]\n\n' +
      'Resolves the calling process\'s seat from its cwd, reads the run-level sessions.csv for the\n' +
      'registered occupant, and matches that (pid, pid-starttime) pair against live /proc ancestry.\n' +
      'Exit 0 = confirmed; exit 1 = typed refusal.\n\n' +
      'It accepts NO identity argument by design: there is no --as and no env override, so an\n' +
      'assertion can never outrank the match.\n',
    );
    return 0;
  }
  if (unknown.length > 0) {
    process.stderr.write(`rbtv-seat-identity: unknown argument(s): ${unknown.join(' ')}\n`);
    return 2;
  }

  const result = checkIdentity();
  if (json) {
    process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  } else if (result.ok) {
    process.stdout.write(
      `seat: ${result.seat}\ngoal: ${result.goal}\nrun: ${result.run}\n` +
      `registered-pid: ${result.registeredPid}\nmatched-ancestor: ${result.matchedAncestor.pid}\n` +
      `permissions: ${result.permissionsSource}\n`,
    );
  } else {
    process.stderr.write(`${result.code}: ${result.message}\n`);
  }
  return result.ok ? 0 : 1;
}

if (require.main === module) process.exit(main(process.argv));

module.exports = { main };
