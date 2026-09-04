# Saha Dışı — iOS First

Native SwiftUI app. Minimum iOS 17. No third-party SDK/dependency.

## Open
Open `SahaDisi.xcodeproj` in Xcode, choose your Development Team and run on iPhone/Simulator.

Bundle id defaults to `com.sahadisi.app`; change it in Signing & Capabilities if needed.

## Data
The app always has `Resources/seed.json` as offline fallback.
To point it at a live feed, set the UserDefaults key `sahadisi.remoteFeedURL` to an HTTPS URL returning the same JSON schema. A future Settings screen can expose this; production should hard-code your owned endpoint/config.

Recommended free MVP path: GitHub Actions runs `backend/collector_v2.py` and `backend/build_feed.py`; publish `backend/feed.json` from a repository/Pages endpoint you control.
