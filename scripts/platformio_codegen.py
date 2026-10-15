"""Run the installed compiler using the same Python as PlatformIO/SCons."""
from pathlib import Path
import subprocess

Import("env")

project = Path(env.subst("$PROJECT_DIR"))
repository = project.parents[1]
name = env.GetProjectOption("custom_ui_name", "counter")
width = env.GetProjectOption("custom_ui_width", "320")
height = env.GetProjectOption("custom_ui_height", "170")
# Keep environments and UI names separate so changing a target cannot reuse stale C++.
generated = project / "generated" / env.subst("$PIOENV") / name
subprocess.run([
    env.subst("$PYTHONEXE"), "-m", "esp_html_ui", "compile", str(project / "ui.html"),
    "--output", str(generated), "--name", name, "--width", width, "--height", height,
], check=True)
# BuildSources clones this environment before PlatformIO adds library includes.
lvgl = Path(env.subst("$PROJECT_LIBDEPS_DIR")) / env.subst("$PIOENV") / "lvgl"
env.Append(CPPPATH=[str(repository / "runtime"), str(generated), str(project / "config"), str(lvgl)])
env.BuildSources("$BUILD_DIR/esphtml-runtime", str(repository / "runtime"))
env.BuildSources("$BUILD_DIR/generated-ui", str(generated))
