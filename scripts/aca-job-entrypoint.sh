#!/usr/bin/env sh
set -eu

job="${1:-${SPAUTOPOST_JOB:-dry-run}}"
if [ "$#" -gt 0 ]; then
  shift
fi

case "$job" in
  dry-run | validate | validate-config)
    exec spautopost "$@" --dry-run dry-run-job
    ;;
  collect | collect-advisories)
    exec spautopost "$@" collect-advisories
    ;;
  generate | generate-drafts)
    exec spautopost "$@" generate-drafts
    ;;
  publish-approved)
    exec spautopost "$@" publish-approved
    ;;
  *)
    echo "unknown SPAutoPost ACA job: $job" >&2
    exit 64
    ;;
esac
