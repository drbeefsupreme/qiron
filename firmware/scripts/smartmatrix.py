from pathlib import Path
import subprocess

Import("env")

library = Path(env.subst("$PROJECT_LIBDEPS_DIR/$PIOENV")) / "SmartMatrix"
patch = Path(env.subst("$PROJECT_DIR")) / "scripts" / "long-text.patch"
applied = subprocess.run(["git", "apply", "--reverse", "--check", patch], cwd=library, capture_output=True)
if applied.returncode:
    subprocess.run(["git", "apply", patch], cwd=library, check=True)
