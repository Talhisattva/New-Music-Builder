#!/usr/bin/env bash
# Guided source launcher for New Music Builder on macOS and Linux.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VENV_DIR="$ROOT/.venv"
REQUIREMENTS="$ROOT/requirements.txt"
MAIN_PY="$ROOT/main.py"
PREFERRED_MAJOR=3
PREFERRED_MINOR=12
MIN_MAJOR=3
MIN_MINOR=12

print_intro() {
  cat <<EOF
New Music Builder source launcher

This will:
  - check this repo
  - find a usable Python
  - create or fix .venv if needed
  - offer installs before changing anything
EOF
}

print_usage() {
  cat <<EOF
Usage: ./run_from_source.sh
EOF
}

if [[ "$#" -gt 0 ]]; then
  print_usage >&2
  exit 2
fi

validate_project_identity() {
  local failed=0
  local required_paths=(
    "$MAIN_PY"
    "$REQUIREMENTS"
    "$ROOT/README.md"
    "$ROOT/src/new_music_builder/__init__.py"
    "$ROOT/src/new_music_builder/app/application.py"
    "$ROOT/src/new_music_builder/platform/paths.py"
    "$ROOT/assets"
  )
  local path

  for path in "${required_paths[@]}"; do
    if [[ ! -e "$path" ]]; then
      echo "Missing: ${path#"$ROOT/"}" >&2
      failed=1
    fi
  done

  if [[ -f "$MAIN_PY" ]] &&
     ! grep -Fq "from new_music_builder.app.application import run" "$MAIN_PY"; then
    echo "main.py does not look like the expected launcher." >&2
    failed=1
  fi

  if [[ -f "$ROOT/src/new_music_builder/__init__.py" ]] &&
     ! grep -Fq '"""New Music Builder package."""' "$ROOT/src/new_music_builder/__init__.py"; then
    echo "Package identity check failed." >&2
    failed=1
  fi

  if [[ -f "$REQUIREMENTS" ]]; then
    for package in customtkinter miniaudio tkinterdnd2; do
      if ! grep -Eq "^${package}([<>=!~].*)?$" "$REQUIREMENTS"; then
        echo "requirements.txt is missing: $package" >&2
        failed=1
      fi
    done
  fi

  if [[ "$failed" -ne 0 ]]; then
    echo >&2
    echo "This does not look like a complete New Music Builder checkout." >&2
    echo "Nothing was installed or removed." >&2
    exit 1
  fi
}

ask_yes_no() {
  local prompt="$1"
  local reply
  while true; do
    read -r -p "$prompt [y/n]: " reply
    case "$reply" in
      y|Y|yes|YES) return 0 ;;
      n|N|no|NO) return 1 ;;
      *) echo "Please answer y or n." ;;
    esac
  done
}

quit_declined() {
  echo "Okay, leaving things alone."
  exit 0
}

safe_remove_project_venv() {
  local root_resolved venv_resolved expected

  if [[ -z "${ROOT:-}" || -z "${VENV_DIR:-}" ]]; then
    echo "Refusing to delete: internal paths are empty." >&2
    exit 1
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    return 0
  fi

  if [[ "$(basename "$VENV_DIR")" != ".venv" ]]; then
    echo "Refusing to delete: expected .venv, got $VENV_DIR" >&2
    exit 1
  fi

  root_resolved="$(cd "$ROOT" && pwd -P)"
  venv_resolved="$(cd "$VENV_DIR" && pwd -P)"
  expected="${root_resolved}/.venv"

  if [[ "$venv_resolved" != "$expected" ]]; then
    echo "Refusing to delete: path is not this repo's .venv." >&2
    echo "  got:      $venv_resolved" >&2
    echo "  expected: $expected" >&2
    exit 1
  fi

  if [[ ! -f "$venv_resolved/pyvenv.cfg" ]]; then
    echo "Refusing to delete: $venv_resolved does not look like a Python venv." >&2
    echo "Remove it manually if you really want to replace it." >&2
    exit 1
  fi

  echo "Removing .venv"
  rm -rf -- "$venv_resolved"
}

python_matches_preferred() {
  local py="$1"
  "$py" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (${PREFERRED_MAJOR}, ${PREFERRED_MINOR}) else 1)" 2>/dev/null
}

python_meets_minimum() {
  local py="$1"
  "$py" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (${MIN_MAJOR}, ${MIN_MINOR}) else 1)" 2>/dev/null
}

has_tkinter() {
  local py="$1"
  "$py" -c "import tkinter" 2>/dev/null
}

candidate_pythons() {
  local names=("python3.12" "python3.13" "python3.14" "python3")
  local name resolved
  local seen=""

  emit_unique() {
    local path="$1"
    [[ -z "$path" || ! -x "$path" ]] && return 0
    case " $seen " in
      *" $path "*) return 0 ;;
    esac
    seen+=" $path"
    echo "$path"
  }

  for name in "${names[@]}"; do
    if command -v "$name" >/dev/null 2>&1; then
      resolved="$(command -v "$name")"
      case "$resolved" in
        "$VENV_DIR"/*) ;;
        *) emit_unique "$resolved" ;;
      esac
    fi
  done
}

find_usable_python() {
  local py
  while IFS= read -r py; do
    [[ -z "$py" ]] && continue
    if ! python_meets_minimum "$py"; then
      continue
    fi
    if ! has_tkinter "$py"; then
      continue
    fi
    echo "$py"
    return 0
  done < <(candidate_pythons)
  return 1
}

find_python_without_tk() {
  local py
  while IFS= read -r py; do
    [[ -z "$py" ]] && continue
    if python_meets_minimum "$py" && ! has_tkinter "$py"; then
      echo "$py"
      return 0
    fi
  done < <(candidate_pythons)
  return 1
}

venv_python() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    echo "$VENV_DIR/bin/python"
    return 0
  fi
  return 1
}

venv_is_usable() {
  local py
  py="$(venv_python)" || return 1
  python_meets_minimum "$py" || return 1
  has_tkinter "$py" || return 1
  return 0
}

missing_python_packages() {
  local py="$1"
  "$py" - <<'PY'
import importlib.util
import sys

needed = [
    ("customtkinter", "customtkinter"),
    ("PIL", "Pillow"),
    ("miniaudio", "miniaudio"),
    ("soundfile", "soundfile"),
    ("numpy", "numpy"),
    ("tkinterdnd2", "tkinterdnd2"),
]

missing = [label for mod, label in needed if importlib.util.find_spec(mod) is None]
if missing:
    print("\n".join(missing))
    sys.exit(1)
sys.exit(0)
PY
}

install_preferred_python() {
  local system_name
  system_name="$(uname -s)"

  if [[ "$system_name" == "Darwin" ]]; then
    if ! command -v brew >/dev/null 2>&1; then
      echo "Homebrew was not found." >&2
      echo "Install it, then run:" >&2
      echo "  brew install python@3.12 python-tk@3.12" >&2
      exit 1
    fi

    echo "Installing Python 3.12 side-by-side with Homebrew..."
    HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_UPGRADE=1 brew install \
      python@3.12 \
      python-tk@3.12
    return 0
  fi

  if command -v apt-get >/dev/null 2>&1; then
    echo "Installing Python 3.12 with apt..."
    sudo apt-get update
    sudo apt-get install -y \
      python3.12 \
      python3.12-venv \
      python3.12-tk
    return 0
  fi

  if command -v dnf >/dev/null 2>&1; then
    echo "Installing Python 3.12 with dnf..."
    sudo dnf install -y python3.12 python3-tkinter
    return 0
  fi

  echo "No supported package manager was found." >&2
  echo "Please install Python 3.12 with tkinter, then run this again." >&2
  exit 1
}

print_manual_python_help() {
  local system_name
  system_name="$(uname -s)"
  echo "A usable Python was not found." >&2
  if [[ "$system_name" == "Darwin" ]]; then
    echo "Install Python 3.12 with tkinter, then run this again:" >&2
    echo "  brew install python@3.12 python-tk@3.12" >&2
    return 0
  fi

  if command -v apt-get >/dev/null 2>&1; then
    echo "Install Python 3.12 with tkinter, then run this again:" >&2
    echo "  sudo apt-get update" >&2
    echo "  sudo apt-get install -y python3.12 python3.12-venv python3.12-tk" >&2
    return 0
  fi

  if command -v dnf >/dev/null 2>&1; then
    echo "Install Python 3.12 with tkinter, then run this again:" >&2
    echo "  sudo dnf install -y python3.12 python3-tkinter" >&2
    return 0
  fi

  echo "Install Python 3.12 with tkinter for your distro, then run this again." >&2
}

ensure_base_python() {
  local base_py tkless_py
  if base_py="$(find_usable_python)"; then
    if python_matches_preferred "$base_py"; then
      echo "Using Python: $("$base_py" --version 2>&1)" >&2
    else
      echo "Using newer installed Python: $("$base_py" --version 2>&1)" >&2
    fi
    printf '%s\n' "$base_py"
    return 0
  fi

  if tkless_py="$(find_python_without_tk)"; then
    echo "Found Python, but it is missing tkinter: $("$tkless_py" --version 2>&1)" >&2
  fi

  echo
  echo "Python 3.12 is preferred for this project." >&2
  echo "I can try to install it side-by-side without changing your default python3." >&2
  echo

  if ! ask_yes_no "Install Python 3.12 now?"; then
    print_manual_python_help
    quit_declined
  fi

  install_preferred_python

  if ! base_py="$(find_usable_python)"; then
    echo "Python install finished, but no usable interpreter was found." >&2
    print_manual_python_help
    exit 1
  fi

  echo "Using Python: $("$base_py" --version 2>&1)" >&2
  printf '%s\n' "$base_py"
}

ensure_venv() {
  local base_py="$1"
  local existing_py existing_ver

  if venv_is_usable; then
    echo ".venv is ready."
    return 0
  fi

  echo
  if [[ -d "$VENV_DIR" ]]; then
    if existing_py="$(venv_python)"; then
      existing_ver="$("$existing_py" --version 2>&1 || true)"
      echo ".venv needs to be recreated."
      echo "Found: $existing_ver"
    else
      echo ".venv exists but is broken."
    fi
  else
    echo ".venv is missing."
  fi
  echo "It will use: $base_py"
  echo

  if ! ask_yes_no "Create or recreate .venv now?"; then
    quit_declined
  fi

  if [[ -d "$VENV_DIR" ]]; then
    safe_remove_project_venv
  fi

  echo "Creating .venv..."
  "$base_py" -m venv "$VENV_DIR"
}

ensure_python_packages() {
  local py missing
  py="$(venv_python)"

  if missing="$(missing_python_packages "$py")"; then
    echo "Python packages look good."
    return 0
  fi

  echo
  echo "Missing packages in .venv:"
  while IFS= read -r package; do
    [[ -n "$package" ]] && echo "  - $package"
  done <<< "$missing"
  echo

  if ! ask_yes_no "Install the missing packages into .venv now?"; then
    quit_declined
  fi

  echo "Installing Python packages..."
  "$py" -m pip install -U pip
  "$py" -m pip install -r "$REQUIREMENTS"

  if ! missing_python_packages "$py" >/dev/null; then
    echo "Some Python packages are still missing after install." >&2
    missing_python_packages "$py" >&2 || true
    exit 1
  fi
}

run_app() {
  local py
  py="$(venv_python)"
  echo
  echo "Starting New Music Builder..."
  exec "$py" "$MAIN_PY"
}

print_intro
echo
validate_project_identity
BASE_PY="$(ensure_base_python)"
ensure_venv "$BASE_PY"
ensure_python_packages
echo
echo "Everything looks ready."
run_app
