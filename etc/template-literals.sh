#!/bin/bash
set -eou pipefail

_err() {
    echo "$@" 1>&2
    exit 1
}

if (( $# == 0 )); then
    _err 'bash $0 file.js...'
fi

IFS= read -r -d '' _perl <<'EOF' || true
if (s{^(\s*(?:template:|SIREPO\.(?:appReportTypes|appPanelHeadingButtons|appFieldEditors|appDownloadLinks)\s*\+?=)\s*)\[\s*$}{$1`\n}) {
    $i = 1;
}
elsif (!$i) {
    # pass
}
elsif (s{^(\s*)\]\.join\(''\)}{$1`}) {
    $i = 0;
}
elsif (m{^\s*//.*}) {
    $_ = '';
}
elsif (s{^(\s*)'(.*)',\s*$}{$1$2\n}) {
    # pass
}
elsif (s{^(\s*)(\w+.*),\s*$}{$1\$\{$2\}\n}) {
    # pass
}
else {
    chomp;
    die($_);
}
EOF

for f in "$@"; do
    if ! perl -n - "$f" <<< "$_perl"; then
        _err "error file=$f"
    fi
done

for f in "$@"; do
    echo -n "$f: "
    perl -pi - "$f" <<<"$_perl"
    echo done
done
