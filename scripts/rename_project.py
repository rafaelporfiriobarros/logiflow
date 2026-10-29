from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

REPLACEMENTS = (
    ("LogiFlow AI", "LogiFlow"),
    ("logiflow_ai", "logiflow"),
    ("logiflow-ai", "logiflow"),
)

TEXT_EXTENSIONS = {
    ".py", ".toml", ".md", ".yml", ".yaml",
    ".json", ".ini", ".sql", ".txt", ".example",
    ".ps1", ".sh", ".html",
}

SKIP_FILES = {
    "uv.lock",
    "compose.override.yaml",
}

tracked = subprocess.check_output(
    ["git", "ls-files", "-z"],
    cwd=ROOT,
).decode("utf-8").split("\0")

changed = []

for relative in tracked:
    if not relative:
        continue

    path = ROOT / relative

    if not path.is_file():
        continue

    if path.name in SKIP_FILES:
        continue

    if path.suffix.lower() not in TEXT_EXTENSIONS:
        continue

    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeError:
        continue

    updated = original

    for old, new in REPLACEMENTS:
        updated = updated.replace(old, new)

    if updated != original:
        path.write_text(updated, encoding="utf-8")
        changed.append(relative)

source = ROOT / "src" / "logiflow_ai"
target = ROOT / "src" / "logiflow"

if source.exists():
    if target.exists():
        raise RuntimeError(
            "A pasta src/logiflow já existe. "
            "Verifique antes de continuar."
        )

    source.rename(target)
    print("Renomeado: src/logiflow_ai -> src/logiflow")

print(f"Arquivos de texto atualizados: {len(changed)}")

for relative in changed:
    print(f"  {relative}")