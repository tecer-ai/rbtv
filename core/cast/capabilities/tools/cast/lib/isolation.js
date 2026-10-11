'use strict';

// What a harness is passed so that an rbtv agent receives only what its own folder holds: nothing
// from a parent folder, no native memory, and from the harness's account folder what each function
// below names. This file is the one place that knows each harness's switches, walks the agent
// folder's ancestors and reads the agent's own files: cast's launch, `cast resume` and Ignite's
// turn call it.
// Every form of a harness (headless, interactive, resume) accepts every value below, except the
// one Codex option its interactive form refuses.
// Measured on Claude Code 2.1.296, Codex 0.162.0 and OpenCode 1.17.18 (Linux, headless).

const fs = require('fs');
const path = require('path');

// Every environment variable an isolated launch sets, on any harness. A launch removes them from
// the environment it inherited, so a launch made by an agent never keeps that agent's values.
const UNSET = [
  'CLAUDE_CODE_DISABLE_BUNDLED_SKILLS',
  'OPENCODE_DISABLE_PROJECT_CONFIG', 'OPENCODE_DISABLE_EXTERNAL_SKILLS', 'OPENCODE_DISABLE_CLAUDE_CODE',
  'OPENCODE_CONFIG_DIR', 'OPENCODE_CONFIG', 'OPENCODE_CONFIG_CONTENT',
];

// The instruction files Claude Code loads from a folder above the working folder: those at the
// folder's root, and those in its `.claude/`. The user's home folder is such a folder, and its
// `.claude/` is the account folder.
const CLAUDE_FILES = ['CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md', '.claude/CLAUDE.md', '.claude/AGENTS.md', '.claude/rules/**'];

// An `instructions` entry of opencode.json that already names its place: a URL or a home path.
const LOCATED = /^(?:https?:\/\/|~[\\/])/;

// The folders above `home`, nearest first, up to the top-level folder.
function ancestors(home) {
  const list = [];
  for (let dir = home; path.dirname(dir) !== dir;) {
    dir = path.dirname(dir);
    list.push(dir);
  }
  return list;
}

// A JSON file's value, or null when the file is missing or cannot be parsed: an agent folder is
// not required to hold one.
function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^﻿/, '')); } catch { return null; }
}

// Claude Code takes two switches for MCP servers and one settings object. --strict-mcp-config
// stops every MCP server not named on the command line: a parent folder's, the home-level ones and
// the account's. --mcp-config hands the agent's own back, and is passed only when the file exists
// because Claude Code refuses to start on a missing one; an option follows it because it takes
// every value up to the next option. The empty `.git` folder in the agent folder stops the
// parent skills, commands, sub-agents and settings; the settings object stops what it leaves: the
// parents' instruction files and rules, listed by path because every pattern not built from the
// ancestors also removed the agent's own files. Memory is turned off by the setting, not by the
// environment variable, so nothing reaches a launch the agent makes.
// --setting-sources without `user` stops the account folder's settings, hooks, permission rules,
// skills, commands, sub-agents and plugins, and the skills synced from the account; the agent's
// own settings files are the `project` and `local` sources. It does not stop the account folder's
// instruction file and rules when the home folder is above the agent folder: the exclusion list
// does. The variable removes the skills bundled in the program, which no argument does.
function claude(home) {
  const excludes = ancestors(home).flatMap((dir) => CLAUDE_FILES.map((file) => path.join(dir, file)));
  const own = path.join(home, '.mcp.json');
  return {
    argv: ['--strict-mcp-config', ...(fs.existsSync(own) ? ['--mcp-config', own] : []),
      '--setting-sources', 'project,local',
      '--settings', JSON.stringify({ claudeMdExcludes: excludes, autoMemoryEnabled: false })],
    env: { CLAUDE_CODE_DISABLE_BUNDLED_SKILLS: '1' },
  };
}

// Codex looks for a project root above the working folder and loads every `.codex/` on the way:
// with no root marker it stops at the working folder. The agent folder is then trusted by its own
// entry, without which its `.codex/` and, under an untrusted parent, its AGENTS.md are not loaded.
// The agent's own hooks run because every Codex start already carries the option that lets a
// hook run without a stored approval (CODEX_HOOK_TRUST in core.js); no parent hook is loaded.
// From the account folder: --disable plugins stops its plugins, their skills and the list of
// recommended plugins; the skills setting stops the skills bundled in the program; and
// --ignore-user-config stops its config.toml, whose model, effort, approval policy and trust of the
// agent folder every launch passes itself. Only `codex exec` and `codex exec resume` accept that
// last option, so a headed start goes without it.
function codex(home, headed) {
  return {
    argv: ['-c', 'project_root_markers=[]', '-c', `projects={${JSON.stringify(home)}={trust_level="trusted"}}`,
      '--disable', 'memories', '--disable', 'plugins', '-c', 'skills.bundled.enabled=false',
      ...(headed ? [] : ['--ignore-user-config'])],
    env: {},
  };
}

// OpenCode has no argument for this and no native memory. Its first two switches also remove the
// agent's own files, so three more variables hand those back: the agent's `.opencode/` and
// `opencode.json` by path, and one object naming the agent's instruction files by absolute path (a
// relative `instructions` entry is not loaded under the first switch) and its skills folders. The
// third switch stops the instruction file of Claude Code's account folder.
function opencode(home) {
  const present = (...files) => files.filter((file) => fs.existsSync(file));
  const own = readJson(path.join(home, 'opencode.json'))?.instructions;
  const listed = (Array.isArray(own) ? own : []).filter((entry) => typeof entry === 'string')
    .map((entry) => (path.isAbsolute(entry) || LOCATED.test(entry) ? entry : path.join(home, entry)));
  const content = {
    instructions: [...new Set([...present(path.join(home, 'AGENTS.md')), ...listed])],
    skills: { paths: present(path.join(home, '.claude', 'skills'), path.join(home, '.agents', 'skills')) },
  };
  return {
    argv: [],
    env: {
      OPENCODE_DISABLE_PROJECT_CONFIG: '1',
      OPENCODE_DISABLE_EXTERNAL_SKILLS: '1',
      OPENCODE_DISABLE_CLAUDE_CODE: '1',
      OPENCODE_CONFIG_DIR: path.join(home, '.opencode'),
      OPENCODE_CONFIG: path.join(home, 'opencode.json'),
      OPENCODE_CONFIG_CONTENT: JSON.stringify(content),
    },
  };
}

const HARNESS = { claude, codex, opencode };

// What one start of `harness` is passed: `argv`, the arguments to add; `env`, the environment
// variables to set; `unset`, the variables to remove from the inherited environment before `env`
// is set. `agentHome` is the folder of the rbtv agent being started, or null for any other launch,
// which gets no argument and no variable. It is given by the caller that holds the agent, never
// read from the environment. `headed` says the start is the harness's interactive form.
function isolation(harness, agentHome, headed = false) {
  if (!agentHome) return { argv: [], env: {}, unset: UNSET };
  return { ...HARNESS[harness](path.resolve(agentHome), headed), unset: UNSET };
}

module.exports = { isolation };
