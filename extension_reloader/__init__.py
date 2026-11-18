"""Extension Reloader - reloads another addon (including submodules) without restarting Blender.

Submodules:
  utils       shared helpers (prefs access, tag utilities, draw helpers)
  scan        scanning installed addons and populating the UI list
  reload      unregister / reload / re-register of addon modules
  properties  RNA property groups and addon preferences
  ui_list     the addon list UIList with search & tag filtering
  operators   the erl.* operators
  panels      the sidebar panels
"""

import bpy

from .operators import (
    ERL_OT_open_preferences,
    ERL_OT_refresh_list,
    ERL_OT_reload_addon,
    ERL_OT_tags_set,
)
from .panels import (
    ERL_MT_list_options,
    ERL_PT_addon_details_panel,
    ERL_PT_reload_panel,
    ERL_PT_tags_panel,
)
from .properties import (
    ERL_AddonListItem,
    ERL_AddonPreferences,
    ERL_ReloadProperties,
    ERL_TagItem,
)
from .scan import (
    auto_refresh_list_on_load,
    refresh_list,
    select_addon_in_list,
)
from .ui_list import ERL_UL_AddonList

# The self-reload timer (reload.py) looks these up dynamically on the reloaded
# top-level module. Listing them in __all__ keeps them from being removed as
# "unused" and silently breaking the post-reload UI refresh.
__all__ = ("refresh_list", "select_addon_in_list")

classes = (
    ERL_AddonListItem,
    ERL_TagItem,
    ERL_ReloadProperties,
    ERL_AddonPreferences,
    ERL_UL_AddonList,
    ERL_OT_reload_addon,
    ERL_OT_refresh_list,
    ERL_OT_tags_set,
    ERL_OT_open_preferences,
    ERL_MT_list_options,
    ERL_PT_reload_panel,
    ERL_PT_tags_panel,
    ERL_PT_addon_details_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.erl_reload_props = bpy.props.PointerProperty(type=ERL_ReloadProperties)

    # Safely load the list *after* Blender sets up context.
    bpy.app.handlers.load_post.append(auto_refresh_list_on_load)


def unregister():
    if auto_refresh_list_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(auto_refresh_list_on_load)

    if hasattr(bpy.types.WindowManager, "erl_reload_props"):
        del bpy.types.WindowManager.erl_reload_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
