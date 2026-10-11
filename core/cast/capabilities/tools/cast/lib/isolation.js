'use strict';

// What a harness is passed so that an rbtv agent receives only what its own folder holds: nothing
// from a parent folder, and no native memory. Home-level configuration stays loaded. This file is
// the one place that knows each harness's switches, walks the agent folder's ancestors and reads
// the agent's and the ancestors' files: cast's launch, `cast resume` and Ignite's turn call it.
// Every form of a harness (headless, interactive, resume) accepts every value below.
// Measured on Claude Code 2.1.296, Codex 0.162.0 and OpenCode 1.17.18 (Linux, headless).

const fs = require('fs');
const os = require('os');
const path = require('path');

// Every environment variable an isolated launch sets, on any harness. A launch removes them from
// the environment it inherited, so a launch made by an agent never keeps that agent's values.
const UNSET = [
  'OPENCODE_DISABLE_PROJECT_CONFIG', 'OPENCODE_DISABLE_EXTERNAL_SKILLS',
  'OPENCODE_CONFIG_DIR', 'OPENCODE_CONFIG', 'OPENCODE_CONFIG_CONTENT',
];

// The instruction files Claude Code loads from a folder above the working folder: those at the
// folder's root, and those in its `.claude/`. In the user's home folder the second list is the
// home-level configuration, which stays loaded.
const CLAUDE_ROOT_FILES = ['CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md'];
const CLAUDE_FOLDER_FILES = ['.claude/CLAUDE.md', '.claude/AGENTS.md', '.claude/rules/**'];

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

// A JSON file's value, or null when the file is missing or cannot be parsed: a folder is not
// required to hold one, and a broken one in a parent folder must not stop the agent's launch.
function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^﻿/, '')); } catch { return null; }
}

// The names of the MCP servers a folder's `.mcp.json` defines.
function serverNames(folder) {
  const servers = readJson(path.join(folder, '.mcp.json'))?.mcpServers;
  return servers && typeof servers === 'object' ? Object.keys(servers) : [];
}

// Claude Code takes one settings object. The empty `.git` folder in the agent folder stops the
// parent skills, commands, sub-agents and settings; this stops what it leaves: the parents'
// instruction files and rules, listed by path because every pattern not built from the ancestors
// also removed the agent's own files, and the parents' MCP servers, turned off by name because
// --strict-mcp-config also removes the home-level servers. Memory is turned off by the setting,
// not by the environment variable, so nothing reaches a launch the agent makes.
function claude(home) {
  const userHome = path.resolve(os.homedir());
  const excludes = [];
  const servers = new Set();
  for (const dir of ancestors(home)) {
    const files = dir === userHome ? CLAUDE_ROOT_FILES : [...CLAUDE_ROOT_FILES, ...CLAUDE_FOLDER_FILES];
    excludes.push(...files.map((file) => path.join(dir, file)));
    for (const name of serverNames(dir)) servers.add(name);
  }
  for (const name of serverNames(home)) servers.delete(name);
  const settings = { claudeMdExcludes: excludes, disabledMcpjsonServers: [...servers].sort(), autoMemoryEnabled: false };
  return { argv: ['--settings', JSON.stringify(settings)], env: {} };
}

// Codex looks for a project root above the working folder and loads every `.codex/` on the way:
// with no root marker it stops at the working folder. The agent folder is then trusted by its own
// entry, without which its `.codex/` and, under an untrusted parent, its AGENTS.md are not loaded.
// Not passed: --disable plugins, which also removes the home-level marketplaces.
function codex(home) {
  return {
    argv: ['-c', 'project_root_markers=[]', '-c', `projects={${JSON.stringify(home)}={trust_level="trusted"}}`,
      '--disable', 'memories'],
    env: {},
  };
}

// OpenCode has no argument for this and no native memory. Its two switches also remove the agent's
// own files and the home-level skills and instructions, so three more variables hand those back:
// the agent's `.opencode/` and `opencode.json` by path, and one object naming the agent's
// instruction files by absolute path (a relative `instructions` entry is not loaded under the
// first switch) and the skills folders.
function opencode(home) {
  const userHome = os.homedir();
  const configHome = process.env.XDG_CONFIG_HOME || path.join(userHome, '.config');
  const present = (...files) => files.filter((file) => fs.existsSync(file));
  const own = readJson(path.join(home, 'opencode.json'))?.instructions;
  const listed = (Array.isArray(own) ? own : []).filter((entry) => typeof entry === 'string')
    .map((entry) => (path.isAbsolute(entry) || LOCATED.test(entry) ? entry : path.join(home, entry)));
  const content = {
    instructions: [...new Set([
      ...present(path.join(home, 'AGENTS.md')), ...listed, ...present(path.join(configHome, 'opencode', 'AGENTS.md')),
    ])],
    skills: {
      paths: present(path.join(home, '.claude', 'skills'), path.join(home, '.agents', 'skills'),
        path.join(userHome, '.claude', 'skills'), path.join(userHome, '.agents', 'skills')),
    },
  };
  return {
    argv: [],
    env: {
      OPENCODE_DISABLE_PROJECT_CONFIG: '1',
      OPENCODE_DISABLE_EXTERNAL_SKILLS: '1',
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
// read from the working folder or from the environment.
function isolation(harness, agentHome) {
  if (!agentHome) return { argv: [], env: {}, unset: UNSET };
  return { ...HARNESS[harness](path.resolve(agentHome)), unset: UNSET };
}

module.exports = { isolation };
