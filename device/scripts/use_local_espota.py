Import("env")

from pathlib import Path


env.Replace(UPLOADER=str(Path(env.subst("$PROJECT_DIR")) / "scripts" / "espota.py"))
