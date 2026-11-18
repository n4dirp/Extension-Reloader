"""RNA property groups and addon preferences."""

from bpy.props import (
    BoolProperty,
    CollectionProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import AddonPreferences, PropertyGroup

from .scan import _on_filter_prefs_update
from .utils import ADDON_ID


class ERL_AddonListItem(PropertyGroup):
    """An item in the addon list."""

    module_name: StringProperty()
    display_name: StringProperty()
    category: StringProperty()
    # Newline separated; tags may contain spaces (e.g. "3D View").
    tags: StringProperty()
    version: StringProperty()
    website: StringProperty()
    maintainer: StringProperty()
    filepath: StringProperty()
    tagline: StringProperty()
    enabled: BoolProperty(default=True)


class ERL_TagItem(PropertyGroup):
    """A tag checkbox in the tag filter (mirrors Blender's extension UI)."""

    name: StringProperty()
    show_tag: BoolProperty(default=True)


class ERL_ReloadProperties(PropertyGroup):
    """Properties for the Extension Reloader utility."""

    addon_items: CollectionProperty(type=ERL_AddonListItem)
    addon_index: IntProperty(default=-1)
    tag_items: CollectionProperty(type=ERL_TagItem)


class ERL_AddonPreferences(AddonPreferences):
    """Preferences for the Extension Reloader utility."""

    bl_idname = ADDON_ID

    last_selected_addon: StringProperty(
        name="Last Selected Addon",
        description="Remembers the last addon selected for reload across sessions",
        default="",
    )

    show_addons_enabled_only: BoolProperty(
        name="Enabled Addons Only",
        description="Only list addons that are currently enabled",
        default=True,
        update=_on_filter_prefs_update,
    )
