"""UIList for the addon list, with search and tag filtering."""

from typing import cast

import bpy
from bpy.types import UIList

from .utils import get_prefs, split_tags, tags_excluded


class ERL_UL_AddonList(UIList):
    """UIList for displaying available addons."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        name_row = row.row(align=True)

        # Only show enabled state when disabled addons are listed as well.
        prefs = get_prefs(context)
        if prefs is not None and not prefs.show_addons_enabled_only:
            name_row.label(
                text="",
                icon="CHECKBOX_HLT" if item.enabled else "CHECKBOX_DEHLT",
            )

        # Using a plugin icon to make the list slightly prettier
        name_row.label(text=item.display_name, icon="PLUGIN")

        version_row = row.row(align=True)
        version_row.active = False
        # Version is right-aligned so the digits line up down the column.
        version_row.alignment = "RIGHT"
        version_row.label(text=item.version)

    def filter_items(self, context, data, propname):
        """Make the list search match display, module name, category & tags.

        The default UIList filter matches the item's ``name`` property, which
        ``ERL_AddonListItem`` does not have, so searching used to hide every
        entry instead of filtering. Tag filtering is applied on top of the
        text search.
        """
        items = getattr(data, propname)
        match = [True] * len(items)

        if self.filter_name:
            filter_by_name = bpy.types.UI_UL_list.filter_items_by_name
            text_flags = [0] * len(items)
            for attr in ("display_name", "module_name", "category", "tags"):
                # The bpy stubs type the return as None; at runtime it is list[int].
                text_flags = cast(
                    "list[int]",
                    filter_by_name(
                        self.filter_name,
                        self.bitflag_filter_item,
                        items,
                        attr,
                        flags=text_flags,
                    ),
                )
            match = [bool(bitflag) for bitflag in text_flags]

        # Unchecked tags form an exclusion set, same model as Blender's own
        # add-on tag filter: an item is hidden when all of its tags are
        # excluded (or it has no tags at all).
        exclude_tags = {item.name for item in data.tag_items if not item.show_tag}
        if exclude_tags:
            match = [
                matched and not tags_excluded(split_tags(item.tags), exclude_tags)
                for matched, item in zip(match, items)
            ]

        if self.filter_name or exclude_tags:
            if self.use_filter_invert:
                match = [not matched for matched in match]
            flags = [self.bitflag_filter_item if matched else 0 for matched in match]
        else:
            flags = [self.bitflag_filter_item] * len(items)

        # The built-in alphabetical sort also relies on the missing ``name``
        # property, so handle it here. Only visible items may be reordered:
        # indices must stay within the filtered item count.
        new_order = []
        if self.use_filter_sort_alpha:
            visible = [index for index, bitflag in enumerate(flags) if bitflag & self.bitflag_filter_item]
            new_order = list(range(len(items)))
            for new_index, index in enumerate(sorted(visible, key=lambda i: items[i].display_name.casefold())):
                new_order[index] = new_index

        return flags, new_order
