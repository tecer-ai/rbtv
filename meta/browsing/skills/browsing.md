---
name: browsing
description: "CONTAINS: the choice among researching a subject with scored and cited sources, reading and saving a web page, previewing a link and driving a real browser, with the program for each PURPOSE: a research report whose every claim carries its source, or a page read, saved, operated, captured as an image or measured, by the cheapest route that works ALWAYS LOAD WHEN: the task needs information from the web or a browser, in any words (\"research X\", \"do a web research\", \"look this up\", \"find sources\", \"how big is the market\", \"compare the prices\", \"read this page\", \"save this article\", \"what is this link\", \"take a screenshot\", \"open the site\", \"log in and click\", \"check my app in the browser\", \"why is this page slow\"): open it as the first step, before the first web search, page fetch or browser command DO NOT LOAD WHEN: the question is about files or code in the workspace (the coordinate skill's investigate method), or the task produces a design, document or deck (the office skill); this skill is not needed for those"
---

# Browsing

This skill covers work that needs a page from the web or a real browser: research with sources, reading and saving a page, previewing a link, and operating, capturing or measuring a page, including an app you are building.

Use the first row of the table that returns what the task needs. The rows after the first run from the cheapest route to the most expensive: a link's title costs less than its text, and a page read without a browser costs less than the same page opened in one.

Three limits hold on every row:

- Your harness's web search tool finds pages. A page's text, saved copy or image comes from the rows below. Where the harness has a page-fetch tool, it is enough for a look at a static public page you will not save or cite.
- A file a command writes (a saved page, a screenshot, a trace) goes where the task says. When the task names no place, write it in your scratch folder and report the path.
- Do not report that the web or a browser is unavailable before running the program the page names and reading its error.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN | DO NOT LOAD WHEN |
|---|---|---|---|---|
| [Researching with sources](../capabilities/methods/researching-with-sources.md) | The research procedure, from the first search to the report: the score every source gets, the count of sources a claim needs, and the report file with its fixed parts | Answer a question from several web sources so that a reader can check every claim | the task asks to research, compare, size a market, find sources or back an answer with sources; read it before the first search | one known page answers the task |
| [Previewing a link](../capabilities/methods/previewing-a-link.md) | Four steps that return a URL's title and description without reading the page | Say what a link is | the task needs only what a URL is | the task needs the page's text |
| [Reading a page](../capabilities/methods/reading-a-page.md) | The `capture-cli` invocations, what each result means and when to name an extractor | Get a page's or PDF's text, saved to a file, and know whether it was the article | the task needs the text of a known URL or of a local HTML or PDF file, or the page saved | the page must be clicked, logged into or measured |
| [Driving a browser](../capabilities/methods/driving-a-browser.md) | The choice between `agent-browser` and `playwright cli` for each job, the order of an interaction, the review of an app being built, and the action for each start-up error | Operate a page, capture it as an image, measure it, or check an app in a real browser | the task needs a click, a form, a login, a screenshot, a network or performance measurement, or a look at an app being built; or Reading a page returned `low_content_density` | the page's text is all the task needs and Reading a page has not been tried |
