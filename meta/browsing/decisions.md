# browsing decisions

Standing decisions about browsing. Each states the decision and its reason; the skill and the pages of `capabilities/` describe the resulting design.

## One skill for everything that needs a browser or a web page

Reading a page, previewing a link, driving a browser and researching with sources are method pages under the `browsing` skill, not skills of their own, and the component is in `meta`. Reason: owner decision, 2026-10-13; an agent chooses once, and the former `web` module made it choose a router skill and then a second skill.

## Reading a page starts without a browser

`capture-cli` is the route for a page's text, and a browser is used only for a page it reports as blocked for low content. Reason: owner decision, 2026-08-21; a browser costs more for the same text.

## agent-browser is the default browser program

`playwright cli` is used for replacing or blocking a response, recording video and Playwright files. Reason: measured on 2026-08-31 with agent-browser 0.33: its route command exited 0 without blocking, and its recording needs a separately installed `ffmpeg`.

## No server record and no copied program reference

The component ships no MCP server record and no reference pages for `agent-browser` or `playwright cli`; the method page names each program's own guide. Reason: owner decision, 2026-10-13; the chrome-devtools server route was never exercised, and copied pages fall behind the installed program.
