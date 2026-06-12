# Holix Link

Lightweight client for [Holix](https://github.com/javded-itres/Holix) remote folder access behind NAT.

On the user's PC you install **only Holix Link** — no full Holix agent, gateway, or `~/.holix/profiles/`.

## Requirements

- Python 3.12+
- Outbound HTTPS (WSS) to your Holix gateway

## Install

```bash
pipx install Holix-Link
# or
curl -fsSL https://raw.githubusercontent.com/javded-itres/Holix-Link/main/scripts/install-link.sh | bash
```

Windows:

```powershell
.\scripts\install-link.ps1
```

## Quick start

1. On the server: `holix link create --profile support`
2. On the client:

```bash
holix-link pair LINK-XXXX-YYYY --folder ~/Projects/acme
holix-link install-service
holix-link status
```

## Data directory

| OS | Default path |
|----|--------------|
| Linux / macOS | `~/.holix-link/` |
| Windows | `%LOCALAPPDATA%\HolixLink\` |

Override with `HOLIX_LINK_HOME`.

## CLI

| Command | Description |
|---------|-------------|
| `holix-link wizard` | Interactive pairing + folder selection |
| `holix-link pair CODE --folder PATH` | Pair with a one-time code |
| `holix-link status` | Connection and folder status |
| `holix-link disconnect` | Revoke local credentials |
| `holix-link install-service` | User-level autostart (systemd / LaunchAgent / Task Scheduler) |

## Documentation

- **User guide (EN/RU):** [Holix LINK.md](https://github.com/javded-itres/Holix/blob/feature/remote-folder-agent/docs/en/LINK.md)
- **Design:** [REMOTE_FOLDER_AGENT.md](https://github.com/javded-itres/Holix/blob/feature/remote-folder-agent/docs/design/REMOTE_FOLDER_AGENT.md)
- **On docs site:** run `holix docs build` on the server, then open `/docs/link`

## License

MIT