<img width="2048" height="1597" alt="Dual 5 split browser view" src="https://github.com/user-attachments/assets/a2d0ef63-2179-4c06-90b6-490c9ea6e2e2" />

# Dual 5 — Unofficial Helium derivative

Dual 5 places two independent tab bars and browser panes in one window. Unlike a conventional Split View that places two tabs side by side, each side of Dual 5 manages multiple tabs independently.

The same layout can be created by positioning two separate windows, but Dual 5 integrates that workflow into one window. Dragging the divider resizes both panes together, so each window does not need to be positioned or resized separately.

## Download

[Download Dual-5-macOS-arm64.dmg](https://github.com/atemizu/Dual/releases/download/v5.0.0/Dual-5-macOS-arm64.dmg)

Open the DMG and copy Dual 5.app to Applications. This build is for Apple Silicon Macs. The distributed app is ad-hoc signed and is not signed or notarized with an Apple Developer ID.

## Project status

The former development name was Helium Dual. Some legacy names remain in storage paths and internal identifiers for compatibility. Dual 5 is an unofficial project and is not affiliated with imput LLC or the Helium project.

- Based on Helium 0.16.5.1 / Chromium 152.0.7977.82
- Target platform: macOS arm64 (Apple Silicon)
- Modified files: [MODIFICATIONS.md](MODIFICATIONS.md), [modifications.json](modifications.json)
- Build instructions: [BUILDING.md](BUILDING.md)
- Validation scope: [VALIDATION.md](VALIDATION.md)

## Source and license

The canonical change set is [helium-dual-window.patch](helium-dual-window.patch). The pinned upstream commit and hashes are recorded in [source-lock.json](source-lock.json).

The original code and modifications are released under the GNU General Public License version 3 (GPL-3.0-only). License text and third-party notices are included in [LICENSE](LICENSE), [licenses/](licenses/), and [NOTICE.md](NOTICE.md). The distributed app retains the upstream credits and license view at helium://credits/.

Dual 5 is an unofficial modified version of Helium. It is not affiliated with, sponsored by, or endorsed by imput LLC or the Helium project. The modifications are released under GPL-3.0-only.
