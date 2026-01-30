# Bash completion for mdclip
# Install: mdclip completion bash --install
# Or: mdclip completion bash > ~/.local/share/bash-completion/completions/mdclip

_mdclip_completions() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Handle 'completion' subcommand
    if [[ "${COMP_WORDS[1]}" == "completion" ]]; then
        case "$COMP_CWORD" in
            1)
                COMPREPLY=($(compgen -W "completion" -- "$cur"))
                ;;
            2)
                COMPREPLY=($(compgen -W "bash" -- "$cur"))
                ;;
            *)
                COMPREPLY=($(compgen -W "--install --path" -- "$cur"))
                ;;
        esac
        return 0
    fi

    # Flags requiring argument
    case "$prev" in
        -o|--output)
            compopt -o filenames -o nospace
            mapfile -t COMPREPLY < <(compgen -d -- "$cur")
            return 0
            ;;
        -t|--template)
            local templates=""
            if [[ -f ~/.mdclip.yml ]]; then
                # YAML format: "  - name: value" or "    name: value"
                templates=$(awk -F': ' '/^[[:space:]]+-?[[:space:]]*name:/ {gsub(/["\047]/, "", $2); print $2}' ~/.mdclip.yml 2>/dev/null | tr '\n' ' ')
            fi
            COMPREPLY=($(compgen -W "$templates" -- "$cur"))
            return 0
            ;;
        --vault|--config)
            COMPREPLY=($(compgen -f -- "$cur"))
            return 0
            ;;
        --rate-limit|--tags)
            return 0
            ;;
    esac

    # Flag completion
    if [[ "$cur" == -* ]]; then
        local opts="-o --output -t --template --tags --force -n --dry-run -y --yes --all-sections --no-format --no-open --rate-limit --cookies --vault --config --list-templates --verbose --version -h --help"
        COMPREPLY=($(compgen -W "$opts" -- "$cur"))
        return 0
    fi

    # Positional args: file completion, plus 'completion' subcommand if it matches
    if [[ "$COMP_CWORD" -eq 1 ]] && [[ "completion" == "$cur"* ]]; then
        COMPREPLY=("completion")
        return 0
    fi

    # Default: file completion for URLs, bookmarks, etc.
    compopt -o default
    COMPREPLY=()
}

complete -F _mdclip_completions mdclip
