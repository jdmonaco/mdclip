#!/usr/bin/env bash

# Ensure homebrew gather-cli is on PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Set the name of your browser
BROWSER="Microsoft Edge"

# Set your Obsidian vault name
VAULT_NAME="Forge"

# Detect frontmost browser and get URL
get_browser_url() {
    case "$BROWSER" in
        "Google Chrome")
            osascript -e 'tell application "Google Chrome" to get URL of active tab of front window'
            ;;
        "Google Chrome Canary")
            osascript -e 'tell application "Google Chrome Canary" to get URL of active tab of front window'
            ;;
        "Chromium")
            osascript -e 'tell application "Chromium" to get URL of active tab of front window'
            ;;
        "Brave Browser")
            osascript -e 'tell application "Brave Browser" to get URL of active tab of front window'
            ;;
        "Microsoft Edge")
            osascript -e 'tell application "Microsoft Edge" to get URL of active tab of front window'
            ;;
        "Arc")
            osascript -e 'tell application "Arc" to get URL of active tab of front window'
            ;;
        "Safari")
            osascript -e 'tell application "Safari" to get URL of front document'
            ;;
        "Firefox")
            # Firefox doesn't support AppleScript well, need alternative
            echo ""
            ;;
        *)
            echo ""
            ;;
    esac
}

URL=$(get_browser_url 2>/dev/null)

if [ -z "$URL" ]; then
    osascript -e 'display notification "No supported browser focused or could not get URL" with title "mdclip"'
    exit 1
fi

# Optional: skip non-http URLs (like chrome://, about:, etc.)
if [[ ! "$URL" =~ ^https?:// ]]; then
    osascript -e "display notification \"Skipping non-web URL: $URL\" with title \"mdclip\""
    exit 0
fi

OUTPUT=$($HOME/.local/bin/mdclip "$URL" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    # Extract relative path from "Saved: path/to/file.md"
    RELATIVE_PATH=$(echo "$OUTPUT" | grep -oE 'Saved: .+\.md$' | sed 's/Saved: //')
    
    if [ -n "$RELATIVE_PATH" ]; then
        # URL-encode the path (preserve slashes)
        ENCODED_PATH=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$RELATIVE_PATH''', safe='/'))")
        
        # Open in Obsidian
        open "obsidian://open?vault=$VAULT_NAME&file=$ENCODED_PATH"
        
        # Extract just filename for notification
        FILENAME=$(basename "$RELATIVE_PATH")
        osascript -e "display notification \"$FILENAME\" with title \"mdclip ✓\""
    else
        osascript -e "display notification \"Clipped (path not found)\" with title \"mdclip ✓\""
    fi
else
    osascript -e "display notification \"$OUTPUT\" with title \"mdclip ✗\""
fi
