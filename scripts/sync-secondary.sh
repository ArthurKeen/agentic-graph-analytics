#!/usr/bin/env bash
#
# Mirror main to the secondary repo (arango-solutions/agentic-graph-analytics)
# at project milestones.
#
# Deliberately manual: the secondary is a publication surface, not a continuous
# mirror, so it advances when you decide something is a milestone — not on
# every push to main.
#
# Usage:
#   scripts/sync-secondary.sh            # check, then push if fast-forward safe
#   scripts/sync-secondary.sh --dry-run  # report what would happen, push nothing
#
set -euo pipefail

PRIMARY="origin"
SECONDARY="arango-solutions"
BRANCH="main"
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

cd "$(git rev-parse --show-toplevel)"

if ! git remote get-url "$SECONDARY" >/dev/null 2>&1; then
  echo "error: no '$SECONDARY' remote. Add it with:" >&2
  echo "  git remote add $SECONDARY https://github.com/arango-solutions/agentic-graph-analytics.git" >&2
  exit 1
fi

echo "Fetching both remotes…"
git fetch --quiet "$PRIMARY" "$BRANCH"
git fetch --quiet "$SECONDARY" "$BRANCH" 2>/dev/null || true

PRIMARY_SHA="$(git rev-parse "$PRIMARY/$BRANCH")"
if git rev-parse --verify --quiet "$SECONDARY/$BRANCH" >/dev/null; then
  SECONDARY_SHA="$(git rev-parse "$SECONDARY/$BRANCH")"
else
  SECONDARY_SHA=""
fi

echo
printf '  %-16s %s\n' "$PRIMARY/$BRANCH" "$(git rev-parse --short "$PRIMARY_SHA")"
if [[ -n "$SECONDARY_SHA" ]]; then
  printf '  %-16s %s\n' "secondary $BRANCH" "$(git rev-parse --short "$SECONDARY_SHA")"
else
  printf '  %-16s %s\n' "secondary $BRANCH" "(absent)"
fi

if [[ "$PRIMARY_SHA" == "$SECONDARY_SHA" ]]; then
  echo
  echo "Already in sync — nothing to mirror."
  exit 0
fi

if [[ -n "$SECONDARY_SHA" ]]; then
  AHEAD="$(git rev-list --count "$SECONDARY_SHA..$PRIMARY_SHA")"
  BEHIND="$(git rev-list --count "$PRIMARY_SHA..$SECONDARY_SHA")"
  echo "  → $AHEAD commit(s) to mirror"

  # A non-zero BEHIND means the secondary holds commits that main does not.
  # Pushing would discard them, so stop and let a human decide.
  if [[ "$BEHIND" -ne 0 ]]; then
    echo
    echo "REFUSING TO PUSH: the secondary has $BEHIND commit(s) not in $PRIMARY/$BRANCH."
    echo "A push would discard them. Inspect first:"
    echo "  git log --oneline $PRIMARY/$BRANCH..$SECONDARY/$BRANCH"
    exit 1
  fi
  echo "  fast-forward safe: yes"
else
  echo "  → creating $BRANCH on the secondary"
fi

echo
git --no-pager log --oneline "${SECONDARY_SHA:+$SECONDARY_SHA..}$PRIMARY_SHA" | sed 's/^/    /'
echo

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "--dry-run: nothing pushed."
  exit 0
fi

# Push the primary's ref explicitly rather than the local branch, so a stale
# or dirty local checkout can never be what lands on the secondary.
git push "$SECONDARY" "$PRIMARY_SHA:refs/heads/$BRANCH"
echo
echo "Pushed $BRANCH -> $SECONDARY (${SECONDARY_SHA:+$(git rev-parse --short "$SECONDARY_SHA")..}$(git rev-parse --short "$PRIMARY_SHA"))"
