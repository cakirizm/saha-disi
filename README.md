# Saha Dışı

Saha Dışı is an iOS-first Turkish football commentary intelligence app.

## What is inside

- Native SwiftUI iOS app
- Real structured football commentary seed data
- Commentator, player, team and match views
- Prediction/result tracking
- Collector pipeline and source registry
- Auto-refresh feed architecture
- GitHub Actions collector workflow
- Web preview and design/audit docs

## Project structure

- `ios/SahaDisi/` — native iOS app
- `backend/` — collector/feed tooling and data
- `collector/` — collector prototype
- `data/` — seed data
- `docs/` — audits, roadmap and design references
- `.github/workflows/collector.yml` — scheduled collector workflow

## iOS

Open `ios/SahaDisi/SahaDisi.xcodeproj` in Xcode, select your Development Team, then run on an iOS 17+ simulator/device.

Default bundle identifier: `com.sahadisi.app`.

## Data refresh

The app supports remote `feed.json` refresh with local fallback/cache. Configure the production feed URL using `SahaDisiFeedURL` in the iOS app `Info.plist`.

## Status

V6 iOS-first audited prototype. The next production step is to connect the collector output to a stable HTTPS feed endpoint and continue expanding verified commentator sources.
