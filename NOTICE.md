# Copyright, licenses and attribution

Copyright 2026 Helium Dual contributors — original contributions and modifications, GPL-3.0-only. Functional changes: 2026-09-08. Publication annotations and tooling: 2026-09-09.

This is an independent, unofficial derivative. It is not affiliated with imput LLC or the Helium project.

## Preserved upstream material

- Helium: GPL-3.0 for its original code and modifications; `licenses/Helium-GPL-3.0.txt`.
- Helium macOS: the pinned repository's original `LICENSE` and `LICENSE.ungoogled_chromium` are copied verbatim to `licenses/helium-macos-LICENSE.txt` and `licenses/helium-macos-LICENSE.ungoogled_chromium.txt`.
- ungoogled-chromium: original BSD 3-Clause notice in `licenses/ungoogled-chromium.txt`.
- Chromium: original notice in `licenses/Chromium-LICENSE.txt`; individual files and dependencies retain their own notices/licenses.

Upstream source and dependencies fetched during a build retain their copyright, license and credit files. This list identifies the material bundled here; it is not a replacement for all licenses in the full upstream source tree.

The original test-input archive contains unmodified Chromium inputs. Its per-file provenance and hashes are in `fixtures/original-test-inputs.manifest.json`; original in-file notices are preserved. The archive is build/test source input, not a compiled application.

Existing upstream copyright and license lines are not removed by the publication patch. GPL notices identify the independent modifications, without changing the license of unmodified imported portions. Four newly authored Helium Dual files previously had a generic BSD-style header; those local headers now identify GPL-3.0-only. That correction does not remove any imported upstream notice.

The covered modified work is conveyed under GPLv3 as a whole, subject to retained compatible third-party notices. No trademark license or endorsement is granted by these notices. Project identification artwork is separate from the program's code; see `assets/NOTICE.md`.

## Header convention

New local files use the copyright/GPL wording found in existing Helium patches, following the official CONTRIBUTING.md Code style guidance. The holder for independent modifications is Helium Dual contributors; this does not attribute them to the official Helium authors. Existing imported notices remain intact.
