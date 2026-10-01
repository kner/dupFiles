#!/usr/bin/env bash
# Lokale Installation ohne sudo; bestehende Suchindizes bleiben erhalten.
set -euo pipefail

usage() {
    cat <<'HELP'
Aufruf: ./install.sh [--prefix VERZEICHNIS]

Standard: ~/.local
Programm und Suchindex: PREFIX/share/dupFiles/
Programmaufruf:         PREFIX/bin/dupFiles

Erneuter Aufruf aktualisiert das Programm und erhält den Suchindex.
HELP
}

prefix="${HOME:?HOME ist nicht gesetzt}/.local"
while (($#)); do
    case "$1" in
        --prefix)
            if (($# < 2)) || [[ -z "$2" ]]; then
                echo 'Fehler: --prefix benötigt ein Verzeichnis.' >&2
                exit 2
            fi
            prefix="$2"
            shift 2
            ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

command -v python3 >/dev/null || { echo 'Fehler: Python 3 fehlt.' >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || {
    echo 'Fehler: Python 3.9 oder neuer wird benötigt.' >&2
    exit 1
}
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
[[ -f "$source_dir/dupFiles" ]] || { echo 'Fehler: dupFiles fehlt neben install.sh.' >&2; exit 1; }
prefix="$(realpath -m -- "$prefix")"
install_dir="$prefix/share/dupFiles"
bin_dir="$prefix/bin"
launcher="$bin_dir/dupFiles"
target="$install_dir/dupFiles"

# Einen fremden Programmaufruf nicht überschreiben.
if [[ -e "$launcher" || -L "$launcher" ]]; then
    if [[ ! -L "$launcher" ]] || [[ "$(readlink -- "$launcher")" != "$target" ]]; then
        echo "Fehler: $launcher existiert bereits und gehört nicht zu dieser Installation." >&2
        exit 1
    fi
fi
mkdir -p -- "$install_dir" "$bin_dir"
temporary="$(mktemp "$install_dir/.dupFiles-install.XXXXXX")"
trap 'rm -f -- "$temporary"' EXIT
install -m 755 -- "$source_dir/dupFiles" "$temporary"
mv -fT -- "$temporary" "$target"
if [[ ! -L "$launcher" ]]; then
    ln -s -- "$target" "$launcher"
fi
printf 'Installiert: %s\nAufruf:      %s\nSuchindex:   %s/dupFiles.index.json\n' "$target" "$launcher" "$install_dir"
case ":$PATH:" in
    *":$bin_dir:"*) echo 'dupFiles ist über PATH erreichbar.' ;;
    *)
        echo 'Für den Aufruf als dupFiles diese Zeile in der Shell ausführen und bei Bedarf in ~/.bashrc ergänzen:'
        printf 'export PATH=%q:"$PATH"\n' "$bin_dir"
        ;;
esac
