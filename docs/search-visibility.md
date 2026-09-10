# Search visibility maintenance

This repository serves an existing GitHub Pages site. Keep the established
business positioning, domain, contact details, enquiry flow and analytics.
Do not add product prices or unsupported delivery promises.

## Publishing content

1. Edit the relevant existing page. Preserve the canonical URL unless the page
   is intentionally being moved. Use a different page only for a distinct need.
2. Add a normal descriptive link from a relevant existing page. Keep useful
   buying guidance visible in HTML, including information beside downloads.
3. Update visible article dates and Article.dateModified only when the article
   changes meaningfully. Keep the original datePublished.
4. Before committing, run `python3 scripts/seo.py sitemap`. This refreshes dates
   for meaningful changes in the working tree compared with HEAD and preserves
   dates for unchanged pages. Run it before the content commit, not after it.
5. Run `python3 scripts/seo.py check`, then commit the content and sitemap together.
6. Check GitHub Actions: `pages build and deployment` and `Search discovery`.

`Search discovery` validates metadata and sitemap on pushes and pull requests.
For a main-branch push, notification waits for the matching successful Pages
build, then compares the commit with the last successful IndexNow notification.
Changes across failed or skipped notifications are retained. The first run uses
the pre-update commit in indexnow.json as its baseline. It verifies the public
key and live page content before notifying IndexNow.
Layout-only HTML changes and CSS/JavaScript-only changes are not submitted.
Sitemap freshness still depends on step 4: this workflow does not write commits
or change the existing GitHub Pages deployment configuration.

Each hostname has its own public verification file and `indexnow.json` key.
This key is website-verification material, not a private account credential.
No new account secret is required. The built-in GitHub token is used with
read-only permissions solely to check deployment and notification workflow runs.

If notification fails, inspect its log and rerun that failed Search discovery
workflow after resolving the problem. Do not rerun unchanged submissions daily.
An HTTP 200/202 confirms receipt, not crawling, indexing or rankings.
IndexNow serves participating engines such as Bing; it is not a Google submission.

For a local offline preview of the changed URL selection, after committing:
`python3 scripts/seo.py indexnow --base <previous-commit-sha> --dry-run`

## Google Search Console checks

Use the verified Domain property for setucrestglobal.com or the matching
URL-prefix property for this hostname. Existing sitemap submissions need not be
repeated every day; confirm that the sitemap is read successfully.

For a small number of important new or substantially improved pages, use URL
Inspection > Test live URL > Request indexing when appropriate. Repeat requests
do not accelerate crawling. Google decides whether and when to index a page.

Review these statuses individually:

| Status | Interpretation and next check |
| --- | --- |
| Discovered, currently not indexed | Known URL, not yet crawled. Inspect access, links and crawl information. |
| Crawled, currently not indexed | Fetched but not indexed. Review usefulness, overlap and canonical selection; this status alone does not establish poor quality. |
| Duplicate / alternate | Compare the declared and Google-selected canonicals. An intended alternate may need no change. |
| Indexed with impressions but few clicks | Review the actual queries, titles and relevance before changing the page. |

Track the URL, inspection date, last crawl, Google-selected canonical, indexing
reason, impressions, clicks and relevant queries. Use equal reporting periods;
record enquiries separately from traffic. Search Console reports require account
access and cannot be created or verified by editing this repository.

## Evidence and distribution

The site includes practical checklists and explicitly labelled planning examples.
No stock image or invented result should be presented as proof of a real order
or a founder's visit. To add first-hand material, retain the date, location,
product details, image ownership/permission and what was actually observed.
For completed supply examples, verify the requirement, agreed specifications,
actual outcome and permission to identify the client. Keep private documents
and personal contacts out of the public repository.

Link a useful guide when sharing with a relevant supplier, logistics partner or
business community that permits resource sharing. Give context for the resource;
do not publish duplicate promotional posts or buy bulk links. This change does
not send outreach messages or claim any acquired backlinks.

## Sources

- [Google: sitemaps and accurate lastmod](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google: requesting a recrawl](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl)
- [Google: page indexing report](https://support.google.com/webmasters/answer/7440203)
- [IndexNow protocol](https://www.indexnow.org/documentation)
- [GitHub: workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
