# Saha Dışı V1 — iOS First

Saha Dışı is a football-commentary data product. The repository now contains:

- `ios/SahaDisi/` — native SwiftUI iPhone app, iOS 17+, no third-party SDKs.
- `backend/collector_v2.py` — public-page discovery + conservative rule-based candidate extraction.
- `backend/build_feed.py` — candidate dedupe / confidence gate / feed builder.
- `backend/sources.json` — source registry.
- `.github/workflows/collector.yml` — optional six-hourly free-ish GitHub Actions collector for a repo you control.
- `data/seed.json` — curated starter feed with real source URLs plus example match records.
- legacy web prototype remains in root for reference only.

## iOS first run
Open `ios/SahaDisi/SahaDisi.xcodeproj` in Xcode. Select your Apple Development Team. Build.

## Local backend test
```bash
python backend/collector_v2.py --limit 5
python backend/build_feed.py
python backend/server.py
```
Then `backend/feed.json` is available at `http://127.0.0.1:8787/feed.json` for local inspection. iOS production should use HTTPS.

## Important source rule
Saha Dışı stores structured summaries and source links, not full copied articles/videos. Source-specific terms and robots rules still need to be respected before enabling automated collection for a production domain.

## Benchmark Week 1 — 28–31 Aug 2026
The supplied nine Süper Lig results are loaded as Week 3. Verified public-source statements are linked by `match_id`. Measurable predictions carry `prediction_outcome` (`correct` / `wrong`). Initial verified benchmark includes Ahmet Çakar's four pre-match picks plus post-match records for Nihat Kahveci, Ali Ece, Serdar Ali Çelikler, Mustafa Çulcu and Ahmet Çakar. Missing records are intentionally left missing rather than fabricated.

## V3 automatic refresh (27-person pool)
- `backend/commentators.json`: the 27-person production pool.
- `backend/collector_v3.py`: direct editorial hubs + public Google News RSS discovery; no X dependency and no paid API key.
- `.github/workflows/collector.yml`: refreshes every 2 hours and commits changed feed/health data.
- `backend/collector_health.json`: source-by-source collection health and candidate counts.
- iOS `FeedService`: remote-first, ETag/cache-aware behavior with last-good cache and bundled fallback.
- Before TestFlight, set `productionFeedURL` in `FeedService.swift` to the HTTPS URL serving `backend/feed.json` (or configure the existing override). Without a real hosted URL, no iPhone app can receive server-side changes after release.
- Auto-publish remains conservative. Lower-confidence RSS-discovered items go to review; direct/high-trust sources can pass the >=95 gate.

## V5 iOS audit update
See `docs/AUDIT_V5.md`. Production feed URL is now configured through the `SahaDisiFeedURL` key in `Info.plist`; no Swift source change is required when the HTTPS feed endpoint is deployed.
