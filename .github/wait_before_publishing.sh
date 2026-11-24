#!/usr/bin/env bash
# Used by .github/workflows/publish.yml. Waits the given number of seconds, then says whether to publish:
# go=yes, or go=no as soon as main holds a newer upload, which publishes itself.
end=$((SECONDS + $1))
while true; do
  newest=$(git ls-remote origin refs/heads/main 2>/dev/null | cut -f1)
  if [ -n "$newest" ] && [ "$newest" != "$GITHUB_SHA" ]; then
    echo "A newer upload has replaced this one, so this one stops here."
    echo "go=no" >> "$GITHUB_OUTPUT"
    exit 0
  fi
  left=$((end - SECONDS))
  if [ "$left" -le 0 ]; then break; fi
  sleep $((left < 30 ? left : 30))
done
echo "go=yes" >> "$GITHUB_OUTPUT"
