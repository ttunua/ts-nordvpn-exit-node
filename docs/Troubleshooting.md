# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| After `nordvpn connect`, Tailscale says it can't reach a relay; `netcheck` shows `UDP: false` | Nord's nft output chain (policy drop) blocks tailscaled's 0x80000-marked traffic to the control and DERP servers | The `nordvpn_tailscale_bypass` remark rule. See [Firewall](Firewall.md) |
| `tailscale netcheck` says `UDP: false` although Tailscale works | Without root it can't set the bypass mark | Run `sudo tailscale netcheck` |
| A device on the exit node has no internet, but the exit node does | Forwarded traffic dropped. Check `nordvpn status`, then `sudo nft list ruleset` (Nord's forward chain should accept `oifname nordlynx`) | `nordvpn connect`. If still broken, check `ip rule` for table 205 |
| `nordvpn set technology nordlynx` → "Command 'technology' doesn't exist" | Removed in 6.x. NordLynx is the default | Nothing to do. The playbook checks for `Protocol: NordLynx` |
| `nordvpn set autoconnect on` → "You're not logged in" | Needs a login first | Log in, then set it. The playbook does it in that order |
| `sysctl: command not found` as a normal user | It's in `/usr/sbin`, which isn't on the user's PATH | Use `/usr/sbin/sysctl`, or sudo |
| First `nordvpn` command on a fresh install: "Permission denied … usermod -aG nordvpn", although `id` shows the user in the group | The SSH session was opened before the user joined `nordvpn`. A running session never picks up new groups | The playbook reconnects (`meta: reset_connection`) right after adding the group. By hand: log out and back in |
| `nordvpn logout --persist-token` → "flag provided but not defined" | Not in 6.1.0. Plain `logout` already keeps the token; `--revoke-token` revokes it | Use plain `nordvpn logout` |
| A client (seen on iOS) has the exit node selected but no internet, though `tailscale ping` works. The exit node shows almost no traffic from it | The client's tunnel went stale after it changed network | Turn Tailscale off and on in the client, then pick the exit node again |
| The whole network loses internet (the exit node too) when your router uses this exit node | **Routing loop.** The exit node reaches the internet through that router, so its own Nord tunnel is sent back into Tailscale to itself | Turn the router's exit node off. Use the exit node per device, or from a router at another location. For a whole network on Nord, use your router's own VPN client. See [Architecture](Architecture.md) |
| After the exit node reboots, clients reach it slowly or only via DERP for a few minutes; the LAN address works | Clients take a few minutes to set up a direct path again. The exit node itself is healthy within seconds | Wait, or use the LAN address. Rerun the playbook if it timed out |
| Page loads on one device but not on a phone | No request reached the page. Usually Tailscale is off on the phone, or Safari searched for the short name | See [Country switcher](Country-Switcher.md): full URL with `http://` |
| Speed test via speed.cloudflare.com returns 0 or 403 | `__down` refuses more than 25 MB per request | Use `bytes=25000000`. See [Performance](Performance.md) |
| `check.yml` fails on "Nord is logged in" | The Nord session expired, or someone ran `nordvpn logout` | Rerun `site.yml` to log in with the vault token. If the token was revoked, make a new one and `ansible-vault edit` the vault |
| Exit IP lookup names a hosting company, not NordVPN | Nord rents servers from hosting providers | Normal. Check `nordvpn status` |
| tailscaled logs `TPM: error opening /dev/tpmrm0` | The machine has no (virtual) TPM | Harmless |
