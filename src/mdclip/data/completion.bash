# Bash completion for mdclip
# Install: mdclip completion bash --install
# Or: mdclip completion bash > ~/.local/share/bash-completion/completions/mdclip

_mdclip_completions() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Flags requiring argument
    case "$prev" in
        -o|--output)
            # Complete vault-relative directories, or absolute paths
            if [[ "$cur" == /* ]] || [[ "$cur" == ~* ]]; then
                # Absolute path - use normal directory completion
                COMPREPLY=($(compgen -d -- "$cur"))
            else
                # Vault-relative - complete from vault directory
                local vault=""
                if [[ -f ~/.mdclip.yml ]]; then
                    vault=$(grep -E '^vault:' ~/.mdclip.yml 2>/dev/null | sed 's/vault:\s*//' | tr -d "\"'")
                    vault="${vault/#\~/$HOME}"
                fi
                if [[ -n "$vault" && -d "$vault" ]]; then
                    local IFS=$'\n'
                    COMPREPLY=($(cd "$vault" && compgen -d -- "$cur" 2>/dev/null))
                else
                    COMPREPLY=($(compgen -d -- "$cur"))
                fi
            fi
            return 0
            ;;
        -t|--template)
            local templates=""
            if [[ -f ~/.mdclip.yml ]]; then
                templates=$(grep -E '^\s+-?\s*name:' ~/.mdclip.yml 2>/dev/null | sed 's/.*name:\s*//' | tr -d "\"'" | tr '\n' ' ')
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
        local opts="-o --output -t --template --tags --skip-existing -n --dry-run -y --yes --all-sections --no-format --no-open --rate-limit --vault --config --list-templates --verbose --version -h --help"
        COMPREPLY=($(compgen -W "$opts" -- "$cur"))
        return 0
    fi

    # File/URL completion for positional args
    COMPREPLY=($(compgen -f -- "$cur"))
}

complete -F _mdclip_completions mdclip
