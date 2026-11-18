# Extension Reloader

A Blender extension for addon development that reloads other addons (including their submodules) without restarting Blender, speeding up the edit-test cycle while you work on an addon.

## Features

- Lists all installed addons and extensions in the sidebar, with search and tag filtering
- Reloads an addon's full module tree in dependency order (submodules first, addon root last)
- Per-addon details: version, maintainer, category, website, and file path
- Options to show only enabled addons and to set tags for all addons at once

## Usage

1. Open the 3D Viewport sidebar (`N` key) in the **Dev** tab.
2. In the **Extension Reloader** panel, find the addon you want to reload.
3. Select it and click **Reload Selected Addon**.

## Requirements

- Blender 4.2+

## License

GPL-3.0-or-later (see `LICENSE`)
