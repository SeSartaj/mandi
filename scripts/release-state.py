"""Persist image tags so plain docker compose commands reuse deployed releases."""

import os
import sys
from pathlib import Path

path, slot, release = sys.argv[1:]
if slot not in {"blue", "green"}:
    raise SystemExit("Invalid deployment slot.")
updates = {"RELEASE": release, slot.upper() + "_RELEASE": release}
source = Path(path)
lines = [
    line
    for line in source.read_text().splitlines()
    if line.partition("=")[0] not in updates
]
lines += [f"{key}={value}" for key, value in updates.items()]
target = source.with_name(source.name + ".next")
with target.open("w") as output:
    os.chmod(target, 0o600)
    output.write("\n".join(lines) + "\n")
target.replace(source)
