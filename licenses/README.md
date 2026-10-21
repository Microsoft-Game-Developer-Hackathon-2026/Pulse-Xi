# License-text inventory

These files preserve **existing declarations and third-party notices**. They do not choose a blanket PULSE XI application license.

- `GPL-3.0-or-later.txt`: official GNU GPL v3 text from https://www.gnu.org/licenses/gpl-3.0.txt; applicable script headers allow this version or later. Keep the authoring scripts/source and notices with covered distributions.
- `CC0-1.0.txt`: SPDX license-list-data text from https://raw.githubusercontent.com/spdx/license-list-data/main/text/CC0-1.0.txt, corresponding to the artwork's existing CC0 dedication. Rights-holder authority is still a human confirmation item.
- `react-three-fiber-9.4.0-MIT.txt`: missing published-package license supplied from its exact official source tag: https://raw.githubusercontent.com/pmndrs/react-three-fiber/v9.4.0/LICENSE.
- `gltf-validator-LICENSE.txt` and `gltf-validator-NOTICES.txt`: actual files from installed Khronos Validator 2.0.0-dev.3.10; development tool, not runtime.
- `frontend/public/assets/THIRD_PARTY_NOTICES.txt`: actual installed production dependency copyright/license texts, built and served with the web app. MIT, ISC and BSD-3-Clause texts and copyright holders are preserved. Regenerate/check with `python scripts/collect-runtime-notices.py [--check]` after `npm ci`.

The repository has no root application license. Satvik/repository rights holders must decide that scope, including unmarked helper code; this audit has not assigned one. See `docs/ASSET_SECURITY_RELEASE_REVIEW.md` for distribution boundaries, provenance limits and the outstanding human approval checklist.
