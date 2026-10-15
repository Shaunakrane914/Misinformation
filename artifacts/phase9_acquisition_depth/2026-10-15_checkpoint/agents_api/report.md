# Four-agent API investigation audit

Commit: abe547f1e17aab5b54e90ff55e2d4783afa95283; dirty source: True.
Observed at: 2026-10-15T14:43:10.445302+00:00. Overall research gate: **PARTIAL**.

API execution, returned records and research correctness are assessed separately.
Independent precision, recall, entailment and LLM-injection success require separate adjudication.

| Agent | Execution | Returned records | URL-bearing records | Coverage | Correctness |
|---|---|---:|---:|---|---|
| brandshield | PASS | 4 | 4 | REQUIRES_ADJUDICATION | NOT_VERIFIED |
| trending | PASS | 0 | 0 | NO_RETURNED_EVIDENCE | NOT_VERIFIED |
| scout | PASS | 0 | 0 | NO_RETURNED_EVIDENCE | NOT_VERIFIED |
| personal_watch | PASS | 1 | 1 | REQUIRES_ADJUDICATION | NOT_VERIFIED |

## brandshield

Exact request: {"brand_name": "Apple", "query": "Apple impersonation phishing brand threats"}

- Returned record: Apple
  URL: https://www.apple.com/
  Depth: PRIMARY_DOCUMENT; publication: 
  Retained passage: Apple Apple Apple Store Mac iPad iPhone Watch Vision AirPods Home Entertainment Accessories Support 0 + Apple HomeView Designed for life at home. Available starting 11.13 Learn more Pre-order iPhone 18 Pro Pro further. Learn more Buy iPhone Duo Hello, hello. Pre-order starting 5:00 a.m. PT on 10.16 Available starting 10.23 Learn more View pricing Apple TV 4K Stunning picture. Stunningly simple. Available starting 11.13 Learn more Pre-order HomePod mini 2 Sound in living color. Available starting 10.30 Learn more Pre-order Apple Home Collection Created for a better smart home experience. Coming later Learn more Shop Apple Watch Series 12 The most accurate heart rate sensing in a wearable. 1 L
- Returned record: OfficialAppleSupport
  URL: https://support.apple.com/
  Depth: PRIMARY_DOCUMENT; publication: 
  Retained passage: Official Apple Support Apple Store Mac iPad iPhone Watch Vision AirPods Home Entertainment Accessories Support 0 + Apple Support Need help? Start here. iPhone Mac iPad Watch Vision AirPods Reset Apple Account password Change a subscription Billing and payments Search for More Topics Search Support To reveal list of choices, type. Search Support Clear Search Handled with AppleCare Every AppleCare plan provides one-stop service for your Apple products, with quick and easy repairs for accidents like drops and spills. You’re also covered if your iPhone, iPad, or Apple Watch is lost or stolen. Learn more Apple Repair and Service We can help you find an Apple-certified repair, performed by trusted
- Returned record: Apple(India)
  URL: https://www.apple.com/in/
  Depth: PRIMARY_DOCUMENT; publication: 
  Retained passage: Apple (India) Apple Apple Store Mac iPad iPhone Watch AirPods Home Entertainment Accessories Support 0 + Get up to 12 months of No Cost EMI plus up to ₹15000 instant cashback on selected products with eligible cards. ‡ Shop Apple HomeView Designed for life at home. Available from 13 November Learn more Pre-order Welcome Joy. Celebrate the season with our festive offers. Shop iPhone 18 Pro Pro further. Learn more Buy Apple TV 4K Stunning picture. Stunningly simple. Available from 13 November Learn more Pre-order HomePod mini 2 Sound in living colour. Available from 30 October Learn more Pre-order iPhone Duo Hello, hello. Pre-order starting at 5:30 PM IST on 16 October Available from 23 Octobe
- Returned record: Profile: Apple (@Apple)
  URL: https://x.com/Apple
  Depth: PARTIAL_CONTENT; publication: Tue Sep 27 05:02:03 +0000 2011
  Retained passage: ### Profile: Apple (@Apple)  http://Apple.com

## trending

Exact request: {"asset_name": "Apple", "query": "Apple recent technology announcements"}

No evidence records returned. Evidence coverage is insufficient for an independently verified conclusion.

## scout

Exact request: {"ticker": "AAPL", "query": "Apple quarterly financial disclosures"}

No evidence records returned. Evidence coverage is insufficient for an independently verified conclusion.

## personal_watch

Exact request: {"name": "Tim Cook", "query": "Tim Cook recent public statements"}

- Returned record: Profile: Tim Cook (@tim_cook)
  URL: https://x.com/tim_cook
  Depth: UNREPORTED; publication: Wed Jul 31 22:41:25 +0000 2013
  Retained passage: ### Profile: Tim Cook (@tim_cook)  Apple Executive Chairman

Complete sanitized API payloads are in summary.json. Claim-to-passage adjudication is required before a research PASS can be assigned.
