#!/usr/bin/env bash

# https://stackoverflow.com/a/28776166/5781491
(return 0 2>/dev/null) && { >&2 echo "setup.sh should be executed, not sourced" ; return 1 ; }

# https://stackoverflow.com/a/3355423/5781491
cd -- "$(dirname "$0")"
test -f .kattis-util-root || { >&2 echo "couldn't find .kattis-util-root file" ; exit 1 ; }

test -d ./.venv || python -m venv ./.venv || { >&2 echo "couldn't find or create venv" ; exit 1 ; }
./.venv/bin/python -m pip install --upgrade --requirement ./requirements.txt || { >&2 echo "couldn't install pip requirements" ; exit 1 ; }

git submodule update --init --recursive || { >&2 echo "couldn't update submodules" ; exit 1 ; }
