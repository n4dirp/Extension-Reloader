"""Scanning installed addons and populating the UI list."""

import os
import sys
import traceback

import bpy
from bpy.app.handlers import persistent

from .utils import get_prefs, tags_refresh

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Blender 4.2+ ships Python 3.11
    tomllib = None


def _manifest_data(module):
    """Return the parsed blender_manifest.toml of an addon module, if any."""
    filepath = getattr(module, "__file__", None)
    if not filepath or tomllib is None:
        return {}

    manifest_path = os.path.join(os.path.dirname(filepath), "blender_manifest.toml")
    try:
        with open(manifest_path, "rb") as manifest_file:
            return tomllib.load(manifest_file)
    except (OSError, ValueError):
        return {}


def _addon_details(module, info):
    """Return (tags, version, website, maintainer, filepath, tagline) for an addon module.

    Manifest values win over ``bl_info``; ``bl_info`` itself uses "author"
    where the manifest uses "maintainer".
    """
    manifest = _manifest_data(module)

    tags = []
    raw_tags = manifest.get("tags")
    if isinstance(raw_tags, list):
        tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    if not tags:
        category = info.get("category") if info else ""
        if category:
            tags = [str(category)]

    version = manifest.get("version")
    if isinstance(version, str) and version.strip():
        version = version.strip()
    else:
        version = info.get("version") if info else None
        if isinstance(version, (tuple, list)) and version:
            version = ".".join(str(part) for part in version)
        elif isinstance(version, str):
            version = version.strip()
        else:
            version = ""

    website = manifest.get("website") or (info.get("website") if info else "")
    maintainer = manifest.get("maintainer") or (info.get("author") if info else "")
    tagline = manifest.get("tagline") or (info.get("tagline") if info else "")

    filepath = getattr(module, "__file__", None)

    return (
        tags,
        version,
        str(website or "").strip(),
        str(maintainer or "").strip(),
        filepath or "",
        str(tagline or "").strip(),
    )


def _scan_addons(context, refresh_modules=False):
    """Map module name -> dict of addon information used by the list and details."""
    entries = {}

    try:
        import addon_utils

        modules = list(addon_utils.modules(refresh=refresh_modules))
    except Exception:
        traceback.print_exc()
        modules = []

    for module in modules:
        info = getattr(module, "bl_info", None) or {}
        module_name = module.__name__
        tags, version, website, maintainer, filepath, tagline = _addon_details(module, info)
        entries[module_name] = {
            "display_name": info.get("name") or module_name,
            "category": info.get("category", ""),
            "tags": tags,
            "version": version,
            "website": website,
            "maintainer": maintainer,
            "filepath": filepath,
            "tagline": tagline,
            "enabled": context.preferences.addons.get(module_name) is not None,
        }

    # Keep enabled addons the scan could not read (e.g. broken bl_info).
    for module_name in context.preferences.addons.keys():
        if module_name in entries:
            continue
        addon_prefs = context.preferences.addons.get(module_name)
        info = getattr(addon_prefs, "bl_info", None) or {}
        module = sys.modules.get(module_name)
        tags, version, website, maintainer, filepath, tagline = _addon_details(module, info)
        entries[module_name] = {
            "display_name": info.get("name") or module_name.split(".")[-1],
            "category": info.get("category", ""),
            "tags": tags,
            "version": version,
            "website": website,
            "maintainer": maintainer,
            "filepath": filepath,
            "tagline": tagline,
            "enabled": True,
        }

    return entries


def refresh_list(context, refresh_modules=False):
    """Populate the UIList with installed addons, honoring the list filters."""
    if not hasattr(context, "window_manager") or not hasattr(context.window_manager, "erl_reload_props"):
        return

    props = context.window_manager.erl_reload_props
    prefs = get_prefs(context)

    selected_name = None
    if 0 <= props.addon_index < len(props.addon_items):
        selected_name = props.addon_items[props.addon_index].module_name

    show_enabled_only = prefs.show_addons_enabled_only if prefs else True

    addon_data_list = []

    for module_name, entry in _scan_addons(context, refresh_modules).items():
        if show_enabled_only and not entry["enabled"]:
            continue
        addon_data_list.append((module_name, entry))

    # Sort alphabetically by display name instead of module name.
    addon_data_list.sort(key=lambda data: (data[1]["display_name"].casefold(), data[0].casefold()))

    props.addon_items.clear()
    for module_name, entry in addon_data_list:
        item = props.addon_items.add()
        item.module_name = module_name
        item.display_name = entry["display_name"]
        item.category = entry["category"]
        item.tags = "\n".join(entry["tags"])
        item.version = entry["version"]
        item.website = entry["website"]
        item.maintainer = entry["maintainer"]
        item.filepath = entry["filepath"]
        item.tagline = entry["tagline"]
        item.enabled = entry["enabled"]

    # Keep the current selection (or the last reloaded addon) if still listed.
    restore_name = selected_name or (prefs.last_selected_addon if prefs else "")
    props.addon_index = -1
    if restore_name:
        for index, item in enumerate(props.addon_items):
            if item.module_name == restore_name:
                props.addon_index = index
                break

    # Sync the tag checkboxes here rather than in a panel's draw(): modifying
    # RNA from draw() is unsupported and can trigger redraw loops.
    tags_refresh(props)


def _on_filter_prefs_update(self, context):
    """Rebuild the list when the enabled-only preference changes."""
    window_manager = getattr(context, "window_manager", None)
    if window_manager is None or not hasattr(window_manager, "erl_reload_props"):
        return

    refresh_list(context)

    for window in window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


@persistent
def auto_refresh_list_on_load(dummy):
    """Application handler to populate the list safely after Blender initializes."""
    refresh_list(bpy.context)


def _initial_refresh_timer():
    """Populate the list once ``register()`` has returned.

    ``addon_utils.enable()`` runs ``register()`` with a restricted
    ``bpy.context``, so defer the first scan until the event loop restores the
    real context. Returning ``None`` makes this a one-shot timer.
    """
    context = bpy.context
    refresh_list(context)

    window_manager = getattr(context, "window_manager", None)
    if window_manager is not None:
        for window in window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

    return None


def schedule_initial_refresh():
    """Queue the first list population right after the add-on is enabled."""
    bpy.app.timers.register(_initial_refresh_timer, first_interval=0.0)


def cancel_initial_refresh():
    """Cancel a queued initial refresh when the add-on is disabled/reloaded."""
    try:
        bpy.app.timers.unregister(_initial_refresh_timer)
    except ValueError:
        # Already fired, or never scheduled.
        pass


def select_addon_in_list(context, addon_name):
    """Select ``addon_name`` in the sidebar list, if it is present."""
    window_manager = getattr(context, "window_manager", None)
    if window_manager is None or not hasattr(window_manager, "erl_reload_props"):
        return

    props = window_manager.erl_reload_props
    for index, item in enumerate(props.addon_items):
        if item.module_name == addon_name:
            props.addon_index = index
            break
