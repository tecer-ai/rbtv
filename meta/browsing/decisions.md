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

## A link's title comes from capture-cli

`capture-cli --title-only` returns a link's title and description, and a result blocked for low content names the browser command in its `next` key. Reason: owner decision, 2026-10-13; a request that carries a URL reaches the tool through the tools rule without opening the skill (0 of 4 test runs opened it), so the cheap route and the next step are stated where the agent is.

## The report form is checked by a program

The research page ends with a run of `research-check`, and the agent corrects the report until it passes. Reason: owner decision, 2026-10-13: the form must hold every time, and one report in ten written from the page alone departed from it. The citation line therefore fixes the place of the link status, which the page had left open.
