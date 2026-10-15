"""Compile the selected document with the production compiler and runtime."""
import os
from pathlib import Path
import subprocess

Import("env")

project = Path(env.subst("$PROJECT_DIR"))
root = project.parents[1]
document = Path(os.environ.get("ESPHTML_TEST_UI", "examples/counter/ui.html"))
if not document.is_absolute():
    document = root / document
document = document.resolve()
generated = project / "generated"
subprocess.run([
    env.subst("$PYTHONEXE"), "-m", "esp_html_ui", "compile", str(document),
    "--output", str(generated), "--name", "counter", "--width", "320", "--height", "170",
], check=True)
config = root / "examples/counter/config"
lvgl = Path(env.subst("$PROJECT_LIBDEPS_DIR")) / env.subst("$PIOENV") / "lvgl"
env.Append(CPPPATH=[str(root / "runtime"), str(generated), str(config), str(lvgl)])
env.Append(CCFLAGS=["-include", str(config / "tft_setup.h")])
env.BuildSources("$BUILD_DIR/esphtml-runtime", str(root / "runtime"))
env.BuildSources("$BUILD_DIR/generated-ui", str(generated))
