# Repository workflow

- Implement the user's requested changes directly in this repository.
- Preserve unrelated user changes and never commit secrets, credentials, signing certificates, provisioning profiles, or local environment files.
- Run the most relevant available validation for each change before committing.
- After validation succeeds, commit all changes made for the request with a concise, descriptive commit message and push the commit to `origin/main` automatically.
- If validation fails, push is rejected, credentials are unavailable, or the requested change is unsafe, stop and clearly report the blocker instead of forcing the operation.
- Treat `codemagic.yaml` as the CI/CD source of truth for Codemagic builds. Keep its iOS signing and TestFlight publishing requirements intact unless the user explicitly requests a change.
