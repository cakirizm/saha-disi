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

Collector v4 combines configured news pages, rotating news/social/agency discovery, YouTube transcript review candidates, and credential-gated X/Instagram API readers. A video title alone cannot verify a speaker, so new transcript candidates require review. `backend/collector_state.json` keeps collection incremental, while `backend/feed.json` remains the historical base. Transfer reports are not official confirmations. Commentary images use verified portraits, not article metadata.

See [source applications and setup](docs/KAYNAK_BASVURULARI.md) for provider links, required secrets, coverage limits and a ready-to-send agency application. Run `python -m unittest discover -s tests -v` for data regression checks.
