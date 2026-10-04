# Building an MCP server record

An [MCP server](../glossary/mcp-server.md) record tells rbtv how a harness reaches one MCP server.

## Purpose

It gives the agent the server's actions on every harness that supports MCP servers, from one record. Without it, each harness's settings are edited by hand and drift apart. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- The description alone tells a reviewer what the server lets the agent do ([Progressive disclosure](../principles/progressive-disclosure.md)).
- It names either an address or a command, never both.
- No secret is written in it: each variable the server needs names the environment variable that holds it.
- No other component already registers the same server ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Write the address of a remote server, or the command and arguments that start a local one. List each variable the server reads with the name of the environment variable that holds its value.
