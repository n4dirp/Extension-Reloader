"""Sidebar panels: main reload panel, tag filter, addon details."""

import os

from bpy.types import Menu, Panel

from .operators import (
    ERL_OT_open_preferences,
    ERL_OT_refresh_list,
    ERL_OT_reload_addon,
    ERL_OT_tags_set,
)
from .utils import (
    _domain_from_url,
    _draw_link,
    _label_multiline,
    get_prefs,
    split_tags,
)


def _draw_details(layout, item):
    """Draw the details of the addon currently selected in the list.

    Every field uses the same right-aligned key / left-aligned value rows.
    """
    col = layout.column(align=True)

    split = col.split(factor=0.25)
    col_a = split.column()
    col_b = split.column()
    col_a.alignment = "RIGHT"
    col_b.alignment = "LEFT"

    col_a.label(text="Name")
    col_b.label(text=item.display_name)

    if item.tagline:
        col_a.label(text="Tagline")
        _label_multiline(col_b, text=item.tagline)

    if item.website:
        col_a.label(text="Website")
        _draw_link(col_b, item.website, _domain_from_url(item.website))

    if item.maintainer:
        col_a.label(text="Maintainer")
        col_b.label(text=item.maintainer)

    if item.version:
        col_a.label(text="Version")
        col_b.label(text=item.version)

    if item.tags:
        col_a.label(text="Tags")
        col_b.label(text=", ".join(split_tags(item.tags)))

    col_a.label(text="Module")
    col_b.label(text=item.module_name)

    if item.filepath:
        col_a.label(text="File")
        row = col_b.row()
        row.label(text=item.filepath)
        row.operator("wm.path_open", text="", icon="FILE_FOLDER", emboss=False).filepath = os.path.dirname(
            item.filepath
        )


class ERL_MT_list_options(Menu):
    """Options for the addon list, opened from the reload panel."""

    bl_label = "Addon List Options"
    bl_idname = "ERL_MT_list_options"

    def draw(self, context):
        layout = self.layout
        prefs = get_prefs(context)

        layout.operator(ERL_OT_refresh_list.bl_idname, text="Refresh List", icon="FILE_REFRESH")

        if prefs is not None:
            layout.separator()
            layout.prop(prefs, "show_addons_enabled_only", text="Enabled Only")

        layout.separator()
        layout.operator(
            ERL_OT_open_preferences.bl_idname,
            text="Addon Preferences",
            icon="PREFERENCES",
        )


class ERL_PT_reload_panel(Panel):
    """Panel in the 3D Viewport sidebar for reloading addons."""

    bl_label = "Extension Reloader"
    bl_idname = "ERL_PT_reload_addon_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Dev"

    def draw(self, context):
        layout = self.layout
        props = context.window_manager.erl_reload_props

        # Buttons
        if 0 <= props.addon_index < len(props.addon_items):
            reload_text = f'Reload "{props.addon_items[props.addon_index].display_name}"'
        else:
            reload_text = "Reload Addon"
        layout.operator(ERL_OT_reload_addon.bl_idname, text=reload_text, icon="FILE_REFRESH")

        # Draw the UIList
        row = layout.row()
        row.template_list(
            "ERL_UL_AddonList",
            "",
            props,
            "addon_items",
            props,
            "addon_index",
        )
        col = row.column()
        col.menu(ERL_MT_list_options.bl_idname, text="", icon="DOWNARROW_HLT")
        col.separator(factor=0.5)
        col.popover(panel="ERL_PT_tags_panel", text="", icon="TAG")


class ERL_PT_tags_panel(Panel):
    """Tag filter checkboxes, modeled on Blender's own add-on tag panel."""

    bl_label = "Show Tags"
    bl_idname = "ERL_PT_tags_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 14

    def draw(self, context):
        layout = self.layout
        props = context.window_manager.erl_reload_props

        row = layout.row()

        subrow = row.row()
        subrow.alignment = "RIGHT"
        subrow.label(text="Select:")

        row = subrow.row()
        row.operator(ERL_OT_tags_set.bl_idname, text="All").value = True
        row.operator(ERL_OT_tags_set.bl_idname, text="None").value = False

        layout.separator(type="LINE")

        # Derive tags read-only: refresh_list() keeps ``tag_items`` in sync.
        tags = sorted(
            {tag for item in props.addon_items for tag in split_tags(item.tags)},
            key=str.casefold,
        )
        tag_map = {item.name: item for item in props.tag_items}
        tags = [tag for tag in tags if tag in tag_map]
        if tags:
            # Two columns; the first column gets the extra row when odd.
            tags_len_half = (len(tags) + 1) // 2
            split = layout.split(factor=0.5)
            col = split.column()
            for i, tag in enumerate(tags):
                if i == tags_len_half:
                    col = split.column()
                col.prop(tag_map[tag], "show_tag", text=tag)
        else:
            col = layout.column()
            col.active = False
            col.label(text="No tags.")


class ERL_PT_addon_details_panel(Panel):
    """Subpanel showing the details of the addon selected in the list."""

    bl_label = "Addon Details"
    bl_idname = "ERL_PT_addon_details_panel"
    bl_parent_id = ERL_PT_reload_panel.bl_idname
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Dev"

    @classmethod
    def poll(cls, context):
        props = getattr(context.window_manager, "erl_reload_props", None)
        return props is not None and 0 <= props.addon_index < len(props.addon_items)

    def draw(self, context):
        props = context.window_manager.erl_reload_props
        _draw_details(self.layout, props.addon_items[props.addon_index])
