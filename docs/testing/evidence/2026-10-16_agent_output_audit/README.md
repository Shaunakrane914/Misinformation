# Four-agent output evidence — 2026-10-16

Read the [audit report](../../FOUR_AGENT_OUTPUT_AUDIT_2026-10-16.md) for methodology,
limitations and code owners. [Measurements](measurements.json) keep direct-API
and real browser observations separate, with exact request bodies, counts,
payload-capture hashes, source IDs/depths and console entries. No credentials
or full historical dossiers are included.

These are actual local Chromium screenshots, not generated mockups. `live-*`
captures used real buttons/local streaming/backend acquisition. `replay-*`
captures used exact saved fresh responses, without another provider acquisition.
They are dated local proof, not production acceptance. Images are unedited.

| Input | Agent | Live 390px | Live 1440px |
|---|---|---|---|
| TATAMOTORS.NS | Scout | [Mobile](live-01-scout-390-report.png) | [Desktop](live-01-scout-1440-report.png) |
| INFY.NS | Scout | [Mobile](live-02-scout-390-report.png) | [Desktop](live-02-scout-1440-report.png) |
| AAPL | Scout | [Mobile](live-03-scout-390-report.png) | [Desktop](live-03-scout-1440-report.png) |
| OpenAI | Trending | [Mobile](live-04-trending-390-report.png) | [Desktop](live-04-trending-1440-report.png) |
| NVIDIA | Trending | [Mobile](live-05-trending-390-report.png) | [Desktop](live-05-trending-1440-report.png) |
| electric vehicles | Trending | [Mobile](live-06-trending-390-report.png) | [Desktop](live-06-trending-1440-report.png) |
| Nike | BrandShield | [Mobile](live-07-brandshield-390-report.png) | [Desktop](live-07-brandshield-1440-report.png) |
| Apple | BrandShield | [Mobile](live-08-brandshield-390-report.png) | [Desktop](live-08-brandshield-1440-report.png) |
| Tata Motors | BrandShield | [Mobile](live-09-brandshield-390-report.png) | [Desktop](live-09-brandshield-1440-report.png) |
| Sam Altman | Personal Watch | [Mobile](live-10-personal_watch-390-report.png) | [Desktop](live-10-personal_watch-1440-report.png) |
| Tim Cook | Personal Watch | [Mobile](live-11-personal_watch-390-report.png) | [Initial desktop capture](live-11-personal_watch-1440-report.png) |
| Satya Nadella | Personal Watch | [Mobile](live-12-personal_watch-390-report.png) | [Desktop](live-12-personal_watch-1440-report.png) |

Additional controls:

- Pass A/Nike zero-source response hides the shared report:
  [390px full page](replay-07-brandshield-390-full.png),
  [1440px full page](replay-07-brandshield-1440-full.png). The empty banner
  remains, but two returned findings and query diagnostics are missing.
- Tim Cook's initial desktop capture has blank cards despite populated DOM.
  Exact-payload rechecks with natural paint/layout waits show content:
  [first desktop recheck](replay-tim-cook-stable-2-1440.png),
  [second desktop recheck](replay-tim-cook-stable-4-1440.png). No CSS/renderer
  replacement or provider request was used. The original alone does not prove
  a persistent UI defect.

Original temp tree: `aegis-twelve-live-264fa77672124089b572006bf1aceb37` in the
operating system's temporary directory. It holds `live.py`, `browser.py`,
`ui_live.py`, `analyze.py`, `stable_capture.py`, raw payloads/events, logs and
isolated databases/dossiers. These one-off runners are **temporary, not a
maintained repository test suite**; temp retention is not guaranteed. Durable
request bodies and metrics are in the JSON. Do not publish raw dossiers or
import source credentials into reports.
