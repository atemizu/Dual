![Dragging the divider resizes both panes; each side keeps its own tabs](assets/dual-demo.gif)

# Dual — Unofficial Helium derivative

Dual places two independent tab bars and browser panes in one window. Unlike a conventional Split View that places two tabs side by side, each side of Dual manages multiple tabs independently.

The same layout can be created by positioning two separate windows, but Dual integrates that workflow into one window. Dragging the divider resizes both panes together, so each window does not need to be positioned or resized separately.

## Download

[Download Dual-6.2.4-macOS-arm64.dmg](https://github.com/atemizu/Dual/releases/download/v6.2.4/Dual-6.2.4-macOS-arm64.dmg)

Open the DMG and copy Dual 6.2.4.app to Applications. This build is for Apple Silicon Macs. The distributed app is ad-hoc signed and is not signed or notarized with an Apple Developer ID.

### If macOS won't open the app

Because the app is not notarized, macOS blocks it the first time ("cannot be opened", "Apple could not verify…", or "is damaged").

1. Try to open Dual 6.2.4 once, then close the warning.
2. Open **System Settings → Privacy & Security**, scroll down, and click **Open Anyway** next to the message about Dual 6.2.4. Confirm with your password.

If the app is reported as damaged, or Open Anyway does not appear, remove the download quarantine flag in Terminal:

```sh
xattr -dr com.apple.quarantine "/Applications/Dual 6.2.4.app"
```

Dual 6.2.4 uses the same bundle identifier as Dual 5 and earlier Dual 6 releases, so an existing profile carries over. Quit the older Dual before opening Dual 6.2.4.

## What's new in 6.2.4

- Zen mode: the right side now appears the same way as the tab bar on the left — a rounded panel that slides in from the window edge, with a "New tab" row. A hidden left or right browser floats in the same way.
- After the left browser is closed, moving the pointer to the left edge shows the panel for opening it again. It used to appear behind the remaining browser.
- When the window buttons (close, minimize, full screen) move to the other browser, that browser's toolbar makes room for them before it is resized.
- The left tab bar's hide button (×) appears as soon as both browsers are open.
- Lighter while the pointer moves over a page: the cursor is no longer re-registered on every mouse move (about two thirds less browser CPU time in our measurement on macOS 27).
- Dual no longer sends crash reports. The crash reporting setting is fixed to Disabled, and the app has no upload address for them.

Earlier changes (6.2.3): resize the window from any side; in Zen mode the outer strip stays hidden until the pointer reaches that edge and the window buttons fade with the toolbar; the right hide button sits at the right end of its tab bar; drag the outer strip to move the window; the app shows Dual's own name and logo.

Earlier changes (6.2.2): based on Helium 0.17.2.2 / Chromium 153 with Helium's release configuration, smoother divider dragging, no separate title bar, rounded corners, optional Zen mode, and a fix for panes staying dimmed after adding an extension.

Details: [MODIFICATIONS.md](MODIFICATIONS.md).

## Project status

The former development name was Helium Dual. Some legacy names remain in storage paths and internal identifiers (such as `helium://` pages) for compatibility. Inside the app, Dual uses its own name and logo; text about Helium's online services and the credits keep Helium's name. Dual is an unofficial project and is not affiliated with imput LLC or the Helium project.

- Based on Helium 0.17.2.2 / Chromium 153.0.8010.52
- Target platform: macOS arm64 (Apple Silicon)
- Modified files: [MODIFICATIONS.md](MODIFICATIONS.md), [modifications.json](modifications.json)
- Build instructions: [BUILDING.md](BUILDING.md)
- Validation scope: [VALIDATION.md](VALIDATION.md)

## Helium services

Like Helium, Dual can use Helium's online services (for example, for extension downloads) when you enable them. Helium's privacy policy states that it does not apply to third-party or unofficial builds, so it does not cover Dual.

Dual does not send crash reports. Helium's crash reporting service is for Helium's own builds, and Dual's own changes can be the cause of a crash, so from 6.2.4 the crash reporting setting is fixed to Disabled and the app contains no upload address for crash reports. (Dual 6.2.3 and earlier asked after a crash by default and sent a report to Helium's service if you agreed, or automatically if you chose that; please set crash reporting to Disabled there.)

## Source and license

The canonical change set is [helium-dual-window.patch](helium-dual-window.patch), made against Helium 0.17.2.2 after Helium's own source preparation, followed by [dual_rebrand.py](dual_rebrand.py), which puts Dual's name and the logos in [branding/](branding/) in place of Helium's. The pinned upstream commits and hashes are recorded in [source-lock.json](source-lock.json).

The original code and modifications are released under the GNU General Public License version 3 (GPL-3.0-only). License text and third-party notices are included in [LICENSE](LICENSE), [licenses/](licenses/), and [NOTICE.md](NOTICE.md). The distributed app retains the upstream credits and license view at helium://credits/.

Dual is an unofficial modified version of Helium. It is not affiliated with, sponsored by, or endorsed by imput LLC or the Helium project. The modifications are released under GPL-3.0-only.
