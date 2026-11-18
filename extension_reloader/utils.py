"""Shared helpers: preferences access, tag utilities, and small draw helpers."""

# Robust way to resolve Addon ID for preferences in Blender 4.2+ Extensions
ADDON_ID = __package__ if __package__ else __name__


def get_prefs(context):
    """Safely get addon preferences."""
    if context is None:
        return None
    addon_prefs = context.preferences.addons.get(ADDON_ID)
    return addon_prefs.preferences if addon_prefs else None


def split_tags(tags):
    """Split the internal tag storage string into a list of tags."""
    return [tag for tag in tags.split("\n") if tag] if tags else []


def tags_refresh(props, default_value=True):
    """Sync ``props.tag_items`` with the tags present in the addon list.

    New tags are added with ``show_tag`` set to ``default_value`` and tags no
    longer present are removed. Returns the sorted list of tag names.
    Modeled on ``tags_refresh`` from Blender's own extension UI.
    """
    tags_next = set()
    for item in props.addon_items:
        tags_next.update(split_tags(item.tags))

    tags_curr = {item.name for item in props.tag_items}
    tags_to_add = tags_next - tags_curr
    tags_to_remove = tags_curr - tags_next

    if tags_to_remove:
        # Remove last indices first.
        for index in reversed([i for i, item in enumerate(props.tag_items) if item.name in tags_to_remove]):
            props.tag_items.remove(index)

    for tag in tags_to_add:
        item = props.tag_items.add()
        item.name = tag
        item.show_tag = default_value

    return sorted(tags_next, key=str.casefold)


def tags_excluded(item_tags, exclude_tags):
    """Return True if an item is hidden by the tag filter.

    An item is hidden when it has no tags at all or when all of its tags are
    excluded. Only meaningful when ``exclude_tags`` is non-empty.
    Modeled on ``tags_exclude_match`` from Blender's own extension UI.
    """
    if not item_tags:
        return True
    for tag in item_tags:
        if tag not in exclude_tags:
            return False
    return True


def _label_multiline(layout, **kwargs):
    """Draw wrapped text; ``label_multiline`` only exists in Blender 5.3+."""
    if hasattr(layout, "label_multiline"):
        layout.label_multiline(**kwargs)
    else:
        layout.label(**kwargs)


def _domain_from_url(url):
    from urllib.parse import urlparse

    return urlparse(url).netloc or url


def _draw_link(layout, url, text):
    """Draw a clickable URL; ``UILayout.link`` only exists in Blender 5.3+."""
    if hasattr(layout, "link"):
        layout.link(url=url, text=text)
    else:
        layout.operator("wm.url_open", text=text, icon="URL", emboss=False).url = url
