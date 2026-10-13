# Previewing a link

The result: the title and description of one URL, without reading or saving the page. Input: the URL.

1. Run `capture-cli --url <url> --title-only`. It fetches the page once, writes nothing, and prints JSON whose `title` and `description` are what the page declares. `state` is `titled` and the exit status 0 when a title was found.
2. When the result is `blocked` and the URL belongs to a platform that publishes oEmbed, fetch the endpoint with `curl -s`. Each returns JSON holding the title.

   | Platform | Endpoint |
   |---|---|
   | X (Twitter) | `https://publish.twitter.com/oembed?url=<url>` |
   | YouTube | `https://www.youtube.com/oembed?url=<url>&format=json` |
   | Any other | `https://noembed.com/embed?url=<url>` |

3. When neither returns a title, report the domain and the `failure_reason`, and ask the user what the link is.

When the task needs the page's text, stop and follow [Reading a page](reading-a-page.md); do not extend these steps to get the body.
