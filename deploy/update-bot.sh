#!/usr/bin/env bash
# Fetches the latest tag, checks it out, and restarts the bot's systemd service.
# Falls back to pulling the main branch if no tags are found.
set -euo pipefail

REPO_DIR="/root/target-assistant-bot" # Ensure this path is correct on your server
SERVICE_NAME="targetbot.service"
LOG_PREFIX="[update-bot]"

cd "$REPO_DIR" || { echo "$LOG_PREFIX Failed to cd into $REPO_DIR" >&2; exit 1; }

echo "$LOG_PREFIX Fetching latest tags from origin..."
if ! git fetch --tags origin; then
    echo "$LOG_PREFIX git fetch --tags origin failed" >&2
    exit 1
fi

# Get the latest tag. If no tags, this will be empty.
LATEST_TAG=$(git describe --tags $(git rev-list --tags --max-count=1) 2>/dev/null || true)

if [ -z "$LATEST_TAG" ]; then
    echo "$LOG_PREFIX No tags found. Falling back to the main branch."
    # Fallback to main if no tags exist (e.g., initial setup)
    # Ensure we are on main and it's up to date
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        echo "$LOG_PREFIX Not on main branch. Checking out main..."
        if ! git checkout main; then
            echo "$LOG_PREFIX git checkout main failed" >&2
            exit 1
        fi
    fi
    echo "$LOG_PREFIX Pulling latest changes from origin/main..."
    if ! git pull origin main --ff-only; then
        echo "$LOG_PREFIX git pull origin main failed" >&2
        exit 1
    fi
    echo "$LOG_PREFIX Updated to the latest version of the main branch. Restarting service $SERVICE_NAME..."
elif git describe --exact-match --tags HEAD 2>/dev/null | grep -q "$LATEST_TAG"; then
    echo "$LOG_PREFIX Already on the latest tag: $LATEST_TAG. No update needed."
    # Optional: restart service even if on latest tag, if configuration might have changed
    # echo "$LOG_PREFIX Restarting service $SERVICE_NAME anyway..."
    # sudo systemctl restart "$SERVICE_NAME"
    # echo "$LOG_PREFIX Service $SERVICE_NAME restarted."
    exit 0 # Exit successfully, no actual update performed but we are on the latest tag
else
    echo "$LOG_PREFIX Latest tag found: $LATEST_TAG. Checking out..."
    if ! git checkout "$LATEST_TAG"; then
        echo "$LOG_PREFIX git checkout to tag $LATEST_TAG failed" >&2
        exit 1
    fi
    echo "$LOG_PREFIX Repository updated to tag $LATEST_TAG. Restarting service $SERVICE_NAME..."
fi

if sudo systemctl restart "$SERVICE_NAME"; then
    echo "$LOG_PREFIX Service $SERVICE_NAME restarted successfully."
else
    echo "$LOG_PREFIX Failed to restart service $SERVICE_NAME." >&2
    exit 1
fi 