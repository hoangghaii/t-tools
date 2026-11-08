# Optional Claude statusline

Merge `.agentkit/templates/claude-statusline.json.example` into project `.claude/settings.json` only when a statusline is desired. The installer copies the script into `.agentkit/templates/statusline/`; the example launcher locates that project root from nested working directories.

The Node implementation preserves directory/Git/model and optional usage display from the original kit. It uses only Node built-ins by default. Set `AGENTKIT_CCUSAGE=1` in the host environment only to use an already installed `ccusage` executable for extra session/cost metrics. It never invokes a package installer or fetches a tool automatically, and subprocess lookups have bounded timeouts.

Statusline configuration remains optional; installing core does not replace an existing statusline. The legacy source `.claude/statusline.js` is a thin launcher of this canonical script.
