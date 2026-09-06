# SetuCrest Analytics Event Verification

Last updated: 6 September 2026

## Property map

| Website | GA4 Measurement ID | Microsoft Clarity ID |
|---|---|---|
| https://setucrestglobal.com/ | `G-DXJY15K95Q` | `ye3it7o3s9` |
| https://school-supplies.setucrestglobal.com/ | `G-3E05BDB3VY` | `ye3j85ac3u` |
| https://trade-solutions.setucrestglobal.com/ | `G-NQDR6R521P` | `ye3jl4kydo` |

Never install another website's Measurement ID or Clarity ID on a property.

## Implemented GA4 events

| Event | Method parameter | Where |
|---|---|---|
| `generate_lead` | `whatsapp` | WhatsApp link clicks on all sites |
| `generate_lead` | `email` | Email link clicks on all sites |
| `generate_lead` | `phone` | Telephone link clicks on all sites |
| `select_content` | `business_division` | Parent links to Trade or School divisions |
| `select_content` | `service_page` | Trade service-page links |
| `select_content` | `category_page` | School category-page links |
| `file_download` | `brochure` | School brochure link |

Every tracked click also sends `link_url` and a shortened `link_text`.

## Browser verification

1. Open the website in Chrome Incognito with ad blockers disabled.
2. Open Developer Tools and select **Network**.
3. Filter for `google-analytics.com/g/collect`.
4. Click the interaction being tested.
5. Open the new collection request.
6. Confirm:
   - Status is `204`.
   - `tid` is the correct Measurement ID.
   - `en` is the expected event name.
   - Event parameters include the expected method.

Test one website/property at a time.

## GA4 Realtime and DebugView

1. Select the matching GA4 property.
2. Open **Reports → Realtime**.
3. Perform a test click and allow several minutes.
4. Inspect the event-name card for `generate_lead`, `select_content` or `file_download`.

For detailed testing, enable Analytics Debugger in a test browser or use Google Tag Assistant, then open **Admin → Data display → DebugView**. Do not leave a debug extension enabled during ordinary browsing.

## Marking key events

In GA4 Admin, open **Data display → Events** after events have first been received. Mark `generate_lead` as a key event. Treat `select_content` and ordinary brochure downloads as engagement indicators unless there is a specific reporting reason to count them as conversions.

## Known limitation: Zoho Forms

The School enquiry form is embedded from a Zoho domain. The parent page cannot reliably detect a successful cross-domain form submission. Configure confirmation tracking inside Zoho Forms, through a dedicated thank-you redirect on the School domain, or through Zoho's supported GA integration. Do not infer successful submissions merely from an iframe view or click.

## Clarity verification

In Developer Tools Network, confirm both the project tag and a Clarity collection request. The collection host can vary. Use an **All** request filter and search for `clarity`. Recordings and heatmaps can take time to process after the first valid session.

## New-site replication

For every new SetuCrest subdomain:

1. Create separate GA4 and Clarity projects.
2. Record the IDs in the master playbook before installation.
3. Install IDs on every indexable HTML page and the 404 page.
4. Add click tracking using the same event names and method convention.
5. Verify Network requests, Realtime and DebugView before marking analytics complete.
