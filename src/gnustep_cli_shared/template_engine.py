from __future__ import annotations

from pathlib import Path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _managed_gnumakefile_flags() -> str:
    return (
        "CC := clang\n"
        "OBJC := clang\n"
        "ADDITIONAL_OBJCFLAGS += -I$(GNUSTEP_PREFIX)/include -I$(GNUSTEP_PREFIX)/System/Sysroot/usr/include/GNUstep -I$(GNUSTEP_PREFIX)/System/Sysroot/usr/include\n"
        "ADDITIONAL_CPPFLAGS += -I$(GNUSTEP_PREFIX)/include -I$(GNUSTEP_PREFIX)/System/Sysroot/usr/include/GNUstep -I$(GNUSTEP_PREFIX)/System/Sysroot/usr/include\n"
        "ADDITIONAL_LDFLAGS += -L$(GNUSTEP_MAKEFILES)/../../../lib -L$(GNUSTEP_MAKEFILES)/../../../lib64\n\n"
    )


def available_templates() -> list[str]:
    return ["gui-app", "cli-tool", "library"]


def _canonical_template(template: str) -> str:
    if template == "cli":
        return "cli-tool"
    return template


def create_template(template: str, destination: str | Path, name: str) -> dict[str, object]:
    template = _canonical_template(template)
    dest = Path(destination).resolve()
    if dest.exists() and any(dest.iterdir()):
        return {
            "schema_version": 1,
            "command": "new",
            "ok": False,
            "status": "error",
            "summary": "Destination directory is not empty.",
            "template": template,
            "destination": str(dest),
            "created_files": [],
        }

    created_files: list[str] = []
    if template == "cli-tool":
        _write(
            dest / "GNUmakefile",
            (
                "include $(GNUSTEP_MAKEFILES)/common.make\n\n"
                f"TOOL_NAME = {name}\n"
                f"{name}_OBJC_FILES = main.m\n\n"
                f"{_managed_gnumakefile_flags()}"
                "include $(GNUSTEP_MAKEFILES)/tool.make\n"
            ),
        )
        _write(
            dest / "main.m",
            '#import <Foundation/Foundation.h>\n\nint main(void)\n{\n  printf("Hello from CLI tool\\n");\n  return 0;\n}\n',
        )
        _write(
            dest / "package.json",
            (
                '{\n'
                '  "schema_version": 1,\n'
                f'  "id": "org.example.{name.lower()}",\n'
                f'  "name": "{name}",\n'
                '  "kind": "cli-tool"\n'
                '}\n'
            ),
        )
        created_files = ["GNUmakefile", "main.m", "package.json"]
    elif template == "gui-app":
        _write(
            dest / "GNUmakefile",
            (
                "include $(GNUSTEP_MAKEFILES)/common.make\n\n"
                f"APP_NAME = {name}\n"
                f"{name}_OBJC_FILES = main.m AppController.m\n"
                f"{name}_RESOURCE_FILES = Resources/Info-gnustep.plist\n\n"
                f"{_managed_gnumakefile_flags()}"
                "include $(GNUSTEP_MAKEFILES)/application.make\n"
            ),
        )
        _write(
            dest / "main.m",
            '#import <AppKit/AppKit.h>\n\nint main(int argc, char **argv)\n{\n  return NSApplicationMain(argc, (const char **)argv);\n}\n',
        )
        _write(
            dest / "AppController.m",
            '#import <AppKit/AppKit.h>\n\n@interface AppController : NSObject\n@end\n\n@implementation AppController\n@end\n',
        )
        _write(dest / "Resources" / "Info-gnustep.plist", "{\n}\n")
        _write(
            dest / "package.json",
            (
                '{\n'
                '  "schema_version": 1,\n'
                f'  "id": "org.example.{name.lower()}",\n'
                f'  "name": "{name}",\n'
                '  "kind": "gui-app"\n'
                '}\n'
            ),
        )
        created_files = ["GNUmakefile", "main.m", "AppController.m", "Resources/Info-gnustep.plist", "package.json"]
    elif template == "library":
        _write(
            dest / "GNUmakefile",
            (
                "include $(GNUSTEP_MAKEFILES)/common.make\n\n"
                f"LIBRARY_NAME = {name}\n"
                f"{name}_OBJC_FILES = {name}.m\n"
                f"{name}_HEADER_FILES = {name}.h\n\n"
                f"{_managed_gnumakefile_flags()}"
                "include $(GNUSTEP_MAKEFILES)/library.make\n"
            ),
        )
        _write(dest / f"{name}.h", f"#import <Foundation/Foundation.h>\n\n@interface {name} : NSObject\n@end\n")
        _write(dest / f"{name}.m", f'#import "{name}.h"\n\n@implementation {name}\n@end\n')
        _write(
            dest / "package.json",
            (
                '{\n'
                '  "schema_version": 1,\n'
                f'  "id": "org.example.{name.lower()}",\n'
                f'  "name": "{name}",\n'
                '  "kind": "library"\n'
                '}\n'
            ),
        )
        created_files = ["GNUmakefile", f"{name}.h", f"{name}.m", "package.json"]
    else:
        return {
            "schema_version": 1,
            "command": "new",
            "ok": False,
            "status": "error",
            "summary": f"Unknown template: {template}",
            "template": template,
            "destination": str(dest),
            "created_files": [],
        }

    return {
        "schema_version": 1,
        "command": "new",
        "ok": True,
        "status": "ok",
        "summary": "Project template created.",
        "template": template,
        "destination": str(dest),
        "name": name,
        "created_files": created_files,
    }
