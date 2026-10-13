# Previewing a link

The result: the title and description of one URL, without reading or saving the page. Input: the URL.

Run the steps in order and stop at the first that returns a title.

1. Ask `defuddle` for one property at a time: `defuddle parse <url> -p title`, then `defuddle parse <url> -p description`. It starts no browser and writes no file.
2. For a URL of a platform that publishes oEmbed, fetch the endpoint with your harness's page-fetch tool, or with `curl -s`. Each returns JSON holding the title.

   | Platform | Endpoint |
   |---|---|
   | X (Twitter) | `https://publish.twitter.com/oembed?url=<url>` |
   | YouTube | `https://www.youtube.com/oembed?url=<url>&format=json` |
   | Any other | `https://noembed.com/embed?url=<url>` |

3. Fetch the URL with your harness's page-fetch tool and ask for exactly this: "Extract only the page title and meta description from the HTML head. Return title and description, nothing else." A fetch without that limit reads the whole page. When the harness has no page-fetch tool, skip this step.
4. Report the domain and what the earlier steps returned, and ask the user for the title and description.

When the task needs the page's text, stop and follow [Reading a page](reading-a-page.md); do not extend these steps to get the body.
