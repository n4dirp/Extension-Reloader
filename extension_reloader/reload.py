"""Unregistering, reloading and re-registering addon modules."""

import importlib
import sys
import traceback
from types import ModuleType

import bpy


def _reload_order(addon_name, modules):
    """Order modules so that dependencies are reloaded before their importers.

    ``importlib.reload`` reuses a module's dictionary, but a submodule that did
    ``from .helpers import helper`` keeps the *old* function object if
    ``helpers`` is reloaded afterwards. Detect those references from each
    module's globals (direct module objects and ``__module__`` on functions and
    classes), then topologically sort the submodules. The addon root goes last
    so its ``from .x import y`` statements bind to the freshly reloaded objects.
    """
    names = {name for name, _ in modules}
    module_map = dict(modules)
    root = addon_name if addon_name in module_map else None

    deps = {name: set() for name in names}
    for name, module in modules:
        if name == root:
            continue
        for value in list(vars(module).values()):
            if isinstance(value, ModuleType):
                dependency = value.__name__
            else:
                dependency = getattr(value, "__module__", None)
            if dependency in names and dependency not in (name, root):
                deps[name].add(dependency)

    remaining = names - ({root} if root else set())
    ordered = []
    while remaining:
        ready = sorted(name for name in remaining if deps[name].issubset(ordered))
        if not ready:
            # Circular imports: break the cycle deterministically.
            ready = [sorted(remaining, key=lambda name: (-name.count("."), name))[0]]
        ordered.extend(ready)
        remaining.difference_update(ready)

    if root is not None:
        ordered.append(root)

    return [(name, module_map[name]) for name in ordered]


def reload_addon_modules(addon_name, report=None, _importlib=importlib, _sys=sys, _traceback=traceback):
    """Unregister, reload (dependencies first), and re-register an addon.

    Must NOT be called from an operator that belongs to ``addon_name``:
    unregistering the running operator's class frees its RNA type while the
    operator is still on the stack, which crashes Blender. Self reloads go
    through :func:`schedule_self_reload` instead.
    """

    def _report(level, message):
        if report is not None:
            try:
                report({level}, message)
                return
            except Exception:
                pass
        print(f"[Extension Reloader] {message}")

    addon_module = _sys.modules.get(addon_name)
    if addon_module is None:
        _report(
            "WARNING",
            f"Module '{addon_name}' not found in sys.modules. Skipping unregister.",
        )
    else:
        unregister_func = getattr(addon_module, "unregister", None)
        if unregister_func is not None:
            try:
                _report("INFO", f"Calling unregister() for '{addon_name}'...")
                unregister_func()
            except Exception as e:
                _report("WARNING", f"Error during unregister: {e}")

    modules_to_reload = _reload_order(
        addon_name,
        [
            (module_name, module_obj)
            for module_name, module_obj in list(_sys.modules.items())
            if module_name == addon_name or module_name.startswith(addon_name + ".")
        ],
    )

    _report("INFO", f"Found {len(modules_to_reload)} module(s) to reload.")

    for module_name, module_obj in modules_to_reload:
        try:
            _importlib.reload(module_obj)
        except Exception as e:
            _report("WARNING", f"Error reloading submodule '{module_name}': {e}")

    reloaded_module = _sys.modules.get(addon_name) or _importlib.import_module(addon_name)
    register_func = getattr(reloaded_module, "register", None)
    if register_func is None:
        _report("ERROR", f"Reloaded addon '{addon_name}' has no register() function.")
        return False

    try:
        register_func()
    except Exception as e:
        _traceback.print_exc()
        _report("ERROR", f"Failed to re-register addon '{addon_name}': {e}")
        return False

    _report("INFO", f"Addon '{addon_name}' reloaded and re-registered successfully.")
    return True


def schedule_self_reload(addon_name):
    """Reload this addon once the calling operator has fully returned.

    ``addon_name`` is captured in a closure on purpose: reloading the module
    replaces its globals, so a module-level variable would already be reset by
    the time the timer callback runs.
    """

    def _run(addon_name=addon_name, _sys=sys, _traceback=traceback):
        try:
            reload_addon_modules(addon_name)
        except Exception:
            _traceback.print_exc()
        finally:
            context = bpy.context
            window_manager = getattr(context, "window_manager", None)
            if window_manager is not None:
                reloaded_module = _sys.modules.get(addon_name)
                refresh_func = getattr(reloaded_module, "refresh_list", None)
                if refresh_func is not None:
                    try:
                        refresh_func(context)
                        select_func = getattr(reloaded_module, "select_addon_in_list", None)
                        if select_func is not None:
                            select_func(context, addon_name)
                    except Exception:
                        _traceback.print_exc()

                for window in window_manager.windows:
                    for area in window.screen.areas:
                        area.tag_redraw()
        return None  # One-shot timer.

    bpy.app.timers.register(_run, first_interval=0.0)
