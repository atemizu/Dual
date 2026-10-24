# Copyright, licenses and attribution

Copyright 2026 Helium Dual contributors (also written as "Dual contributors") — original contributions and modifications, GPL-3.0-only. Functional changes: 2026-09-08 to 2026-10-25 (Dual 6.4.0, based on Helium 0.20.1.1). Publication annotations and tooling: 2026-09-09, 2026-09-29, 2026-10-04, 2026-10-05, 2026-10-06, 2026-10-10 and 2026-10-25.

This is an independent, unofficial derivative. It is not affiliated with imput LLC or the Helium project.

## Preserved upstream material

- Helium: GPL-3.0 for its original code and modifications; `licenses/Helium-GPL-3.0.txt`.
- Helium macOS: the pinned repository's original `LICENSE` and `LICENSE.ungoogled_chromium` are copied verbatim to `licenses/helium-macos-LICENSE.txt` and `licenses/helium-macos-LICENSE.ungoogled_chromium.txt`.
- ungoogled-chromium: original BSD 3-Clause notice in `licenses/ungoogled-chromium.txt`.
- Chromium: original notice in `licenses/Chromium-LICENSE.txt`; individual files and dependencies retain their own notices/licenses.

Upstream source and dependencies fetched during a build retain their copyright, license and credit files. This list identifies the material bundled here; it is not a replacement for all licenses in the full upstream source tree.

Existing upstream copyright and license lines are not removed by the publication patch. GPL notices identify the independent modifications, without changing the license of unmodified imported portions. Four newly authored Helium Dual files previously had a generic BSD-style header; those local headers now identify GPL-3.0-only. Two more newly authored files (`helium_dual_state.h`, `helium_dual_state_smoke.cc`) named "The Helium Authors" as their copyright holder; from 6.3.0 they name the Dual contributors. These corrections do not remove any imported upstream notice.

## Branding

From 6.2.3, the app shows Dual's own name and logo. `dual_rebrand.py` replaces the browser's name in the interface text and copies the images in `branding/` (made from Dual's own icon by `branding/make_branding.py`) to the places where Helium's preparation puts Helium's logos. No Helium logo is used in the app. Text that refers to Helium itself (Helium's online services, its partner program, its authors) keeps Helium's name, and the About page states that Dual is an unofficial derivative of Helium.

The covered modified work is conveyed under GPLv3 as a whole, subject to retained compatible third-party notices. No trademark license or endorsement is granted by these notices. Project identification artwork is separate from the program's code; see `assets/NOTICE.md`.

## Bundled extensions

`extensions/report` (Dual Problem Report), `extensions/timelimit` (Dual Site Time Limit) and `extensions/translate` (Dual Page Translate) are original works of the Dual contributors, code and icons alike, released under GPL-3.0-only. Each is a separate program from the browser: Dual loads it from the app bundle as an ordinary extension. They contain no third-party code or artwork. The icons are pixel drawings by Dual's author (the translate icon is a provisional drawing by the Dual contributors); the drawings are in `extensions/art/` and `extensions/make_pixel_icons.py` turns them into the icon files.

## Translation program and model

`translate-host/` (the program `dual-translate-host`, which Dual Page Translate uses) is an original work of the Dual contributors, released under GPL-3.0-only. The built program links in third-party code under the MIT License, whose notices are shipped next to it in the app (`Contents/Resources/Dual Native Hosts/dual-translate-host-licenses/`) and kept in `translate-host/licenses/`:

- llama.cpp and ggml, release b11846 — Copyright (c) 2023-2026 The ggml authors, MIT License.
- JSON for Modern C++ (vendored in llama.cpp) — Copyright (c) 2013-2025 Niels Lohmann, MIT License.

The translation model, Gemma 4 E4B by Google DeepMind in the 4-bit GGUF version made by Unsloth (`unsloth/gemma-4-E4B-it-GGUF`), is not part of Dual or of this repository. The program downloads it from Hugging Face when the user asks, and the model is licensed under the Apache License 2.0 by its authors.

## Tools

The scripts in `tools/` and `packaging/` are original works of the Dual contributors, released under GPL-3.0-only.

## Header convention

New local files use the copyright/GPL wording found in existing Helium patches, following the official CONTRIBUTING.md Code style guidance. The holder for independent modifications is Helium Dual contributors; this does not attribute them to the official Helium authors. Existing imported notices remain intact.
