"""Operators: reload addon, refresh list, set all tags, open preferences."""

import sys

import bpy
from bpy.props import BoolProperty
from bpy.types import Operator

from .reload import reload_addon_modules, schedule_self_reload
from .scan import refresh_list
from .utils import ADDON_ID, get_prefs, tags_refresh


class ERL_OT_reload_addon(Operator):
    """Reloads the selected addon and its submodules"""

    bl_idname = "erl.reload_addon_operator"
    bl_label = "Reload Selected Addon"
    bl_options = {"REGISTER", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        if not hasattr(context.window_manager, "erl_reload_props"):
            return False
        props = context.window_manager.erl_reload_props
        return props.addon_index >= 0 and len(props.addon_items) > 0

    def execute(self, context):
        props = context.window_manager.erl_reload_props
        if props.addon_index < 0 or props.addon_index >= len(props.addon_items):
            self.report({"ERROR"}, "No addon selected to reload.")
            return {"CANCELLED"}

        addon_name = props.addon_items[props.addon_index].module_name

        # A disabled addon is not registered, so reloading it would import and
        # register it without Blender knowing it is enabled.
        if context.preferences.addons.get(addon_name) is None:
            self.report(
                {"ERROR"},
                f"Addon '{addon_name}' is not enabled. Enable it before reloading.",
            )
            return {"CANCELLED"}

        # Save selection to preferences
        prefs = get_prefs(context)
        if prefs:
            prefs.last_selected_addon = addon_name

        self.report({"INFO"}, f"Attempting to reload addon: '{addon_name}'...")

        # Reloading this extension itself must not happen inside this operator:
        # unregistering our own operator class while it is executing frees its
        # RNA type and crashes Blender (as does touching `self` or `props`
        # afterwards). Defer the whole sequence to a timer, once this operator
        # has returned.
        if addon_name == ADDON_ID or addon_name.startswith(ADDON_ID + "."):
            self.report(
                {"INFO"},
                f"Reloading '{addon_name}' once the operator finishes...",
            )
            schedule_self_reload(addon_name)
            return {"FINISHED"}

        if not reload_addon_modules(addon_name, self.report):
            return {"CANCELLED"}

        # Refresh UI
        refresh_list(context)

        # Force UI update redraws
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        return {"FINISHED"}


class ERL_OT_refresh_list(Operator):
    """Refresh the addon list"""

    bl_idname = "erl.refresh_list_operator"
    bl_label = "Refresh List"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        refresh_list(context, refresh_modules=True)
        return {"FINISHED"}


class ERL_OT_tags_set(Operator):
    """Set every tag filter checkbox to the same value."""

    bl_idname = "erl.tags_set"
    bl_label = "Set All Tags"
    bl_options = {"REGISTER", "INTERNAL"}

    value: BoolProperty(
        name="Value",
        description="Enable or disable all tags",
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        props = context.window_manager.erl_reload_props
        props.tag_items.clear()
        # "All" re-adds every tag checked (nothing excluded); "None" re-adds
        # them unchecked so the whole list is filtered out.
        tags_refresh(props, default_value=self.value)

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {"FINISHED"}


class ERL_OT_open_preferences(Operator):
    """Open the Add-on Preferences panel for the selected addon"""

    bl_idname = "erl.open_preferences"
    bl_label = "Open Preferences"
    bl_description = "Open the add-on preferences panel"
    bl_options = {"REGISTER", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        props = getattr(context.window_manager, "erl_reload_props", None)
        return props is not None and 0 <= props.addon_index < len(props.addon_items)

    def execute(self, context):
        props = context.window_manager.erl_reload_props
        item = props.addon_items[props.addon_index]

        # Blender's Add-ons search matches bl_info["name"] (which addon_utils
        # derives from the manifest for extensions), not the module name.
        search_name = item.display_name
        module = sys.modules.get(item.module_name)
        if module is not None:
            try:
                import addon_utils

                search_name = addon_utils.module_bl_info(module).get("name") or search_name
            except Exception:
                pass

        # Clear the built-in filters as Blender's add-on installer does, so the
        # search is guaranteed to reveal the target even if filters were set.
        context.preferences.active_section = "ADDONS"
        context.preferences.view.show_addons_enabled_only = False
        context.window_manager.addon_filter = "All"
        context.window_manager.addon_search = search_name

        try:
            bpy.ops.screen.userpref_show()
        except RuntimeError as exc:
            # No suitable window (e.g. background mode): filters are still set.
            self.report({"WARNING"}, f"Could not open Preferences: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}
