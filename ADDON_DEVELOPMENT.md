# Home Assistant app repository

This repository now contains a locally buildable Home Assistant app in
`octopus_intelligence/` and the repository descriptor at `repository.yaml`.

The app's Docker build context must be self-contained, so release packaging copies
the Python project into `octopus_intelligence/app/`. Run
`scripts/sync_addon_source.sh` after changing the Python package and before making
an app release.

For public distribution, publish this directory as a GitHub repository and add its
URL under **Settings → Apps → App store → Repositories**. The current package is
locally built by Supervisor. A later release can add a GitHub Actions multi-arch
image workflow and an `image` entry in `config.yaml`.

No software licence has been selected yet. Choose one before public release.

