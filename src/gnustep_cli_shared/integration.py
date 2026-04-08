from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_desktop_entry(
    *,
    app_id: str,
    display_name: str,
    exec_path: str,
    icon_name: str,
    categories: list[str],
) -> str:
    categories_field = ";".join(categories) + ";"
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={display_name}\n"
        f"Exec={exec_path}\n"
        f"Icon={icon_name}\n"
        f"Categories={categories_field}\n"
        "Terminal=false\n"
        f"X-GNUstep-Package={app_id}\n"
    )


def generate_windows_shortcut_metadata(
    *,
    app_id: str,
    display_name: str,
    executable: str,
    icon_path: str,
    start_menu_group: str = "GNUstep",
) -> dict[str, Any]:
    return {
        "app_id": app_id,
        "display_name": display_name,
        "executable": executable,
        "icon_path": icon_path,
        "start_menu_group": start_menu_group,
        "shortcut_name": f"{display_name}.lnk",
    }


def validate_gui_integration(
    *,
    package_id: str,
    display_name: str | None,
    icon_path: str | None,
    launcher_enabled: bool | None,
    categories: list[str] | None,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not display_name:
        errors.append({"code": "missing_display_name", "message": "GUI package is missing display name metadata."})
    if not icon_path:
        errors.append({"code": "missing_icon", "message": "GUI package is missing icon metadata."})
    if launcher_enabled is not True:
        errors.append({"code": "missing_launcher", "message": "GUI package must enable launcher generation."})
    if not categories:
        errors.append({"code": "missing_categories", "message": "GUI package is missing desktop categories."})
    return {
        "schema_version": 1,
        "package_id": package_id,
        "ok": len(errors) == 0,
        "errors": errors,
    }

