# Saha Dışı

Saha Dışı is a native iOS football commentary and fixture app backed by a continuously refreshed, verified public-source feed.

## Data principles

- Official fixture data is collected from TFF.
- Commentary shown in the live feed is restricted to attributable direct quotes or manually verified literal statements.
- Team crests and commentator portraits are only used when identity can be verified; ambiguous images fall back safely.
- The app supports team, commentator, team+commentator, and all-feed notification preferences.

## iOS

The Xcode project is under `ios/SahaDisi`.

## Live feed

GitHub Actions workflow `.github/workflows/collector.yml` refreshes `backend/feed.json` and validates feed integrity before publishing changes.

Collector v4 combines configured news pages, Google News RSS searches, and captioned videos from verified YouTube channels. Video quotes are accepted only when the video identifies exactly one tracked commentator and the transcript segment passes attribution and quality checks. `backend/collector_state.json` keeps collection incremental, while `backend/feed.json` remains the historical base so previously verified statements are not lost on the next run.
