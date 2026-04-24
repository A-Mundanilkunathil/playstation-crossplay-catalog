# PSCrossplay — native iOS app

SwiftUI app that reads the same `games.json` catalog the website does, shown as five grid-of-cards sections (PS+ Extra PS4↔PS5 / PS5↔PC / Triple + All-games PS5↔PC / Triple). Tapping a card opens a Google Images search for "{title} gameplay". Pull-to-refresh re-fetches the published JSON; a "Rebuild now" toolbar action triggers the GitHub Actions workflow and polls until it finishes.

## Prerequisites

1. **Xcode** (full install, not just Command Line Tools) — free from the Mac App Store. ~15 GB download.
2. After Xcode installs, point the toolchain at it:
   ```sh
   sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
   ```
3. **Free Apple ID** — sign into Xcode via Xcode → Settings → Accounts → "+".

## Build

The `.xcodeproj` is generated from `project.yml` via [xcodegen](https://github.com/yonaskolb/XcodeGen). If you edit `project.yml` or add/remove Swift files, regenerate:

```sh
cd ios
xcodegen
```

Then open:

```sh
open PSCrossplay.xcodeproj
```

In Xcode:

1. Select the **PSCrossplay** target → **Signing & Capabilities**
2. Team: your personal Apple ID team
3. Bundle identifier: keep `com.pscrossplay.app` (or change to anything unique)
4. Scheme: **PSCrossplay** → build & run (⌘R)

First run defaults to the **iPhone 15 Simulator** — the app appears with the bundled `seed-games.json` data (currently ~248 games), then background-fetches the live JSON from GitHub Pages.

## Sideload to your iPhone

1. Plug your iPhone into the Mac via USB.
2. In Xcode's device picker, pick your iPhone instead of the simulator.
3. Build & run. First install prompts you on the iPhone:
   - **Settings → General → VPN & Device Management → Developer App** → tap your Apple ID → **Trust**.
4. Free-tier certs **expire every 7 days**. Just plug your phone back in and Xcode → Run once a week to refresh. (Paid Apple Developer Program at $99/yr extends this to a year and unlocks TestFlight.)

## Refresh behavior

- **Pull down on the catalog** → re-downloads `games.json` from GitHub Pages. Fast (<1 s).
- **Toolbar ⟳ menu → "Rebuild now (~2 min)"** → triggers a fresh GitHub Actions run, polls until completed, then re-downloads. Requires a GitHub PAT saved in **Settings**:
  - Go to https://github.com/settings/tokens → *Fine-grained tokens* → *Generate new*
  - Repository access: only this repo
  - Permissions: **Actions: Read and write**
  - Copy the `github_pat_...` token, open the app's **Settings** (gear icon), paste in, tap *Save*. Stored in iOS Keychain, device-only.

## Files

```
ios/
├── project.yml                     # xcodegen spec
├── README.md
└── PSCrossplay/
    ├── PSCrossplayApp.swift        # @main
    ├── Models/Game.swift           # Codable
    ├── Services/
    │   ├── GameStore.swift         # fetch + disk cache
    │   ├── WorkflowDispatcher.swift# GitHub Actions dispatch + poll
    │   └── KeychainPAT.swift
    ├── Views/
    │   ├── RootView.swift
    │   ├── CatalogView.swift
    │   ├── SectionView.swift
    │   ├── GameCard.swift
    │   ├── FilterBar.swift
    │   └── SettingsView.swift
    └── Resources/seed-games.json   # frozen snapshot for first-launch
```

The generated `PSCrossplay.xcodeproj/` is **committed to the repo** — opening the project after `git clone` works without re-running `xcodegen`.
