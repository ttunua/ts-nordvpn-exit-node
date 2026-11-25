# NordVPN login

Checked against NordVPN app 6.1.0 for Linux (source: [NordSecurity/nordvpn-linux](https://github.com/NordSecurity/nordvpn-linux)).

## Methods

| Method | How | Use for |
|---|---|---|
| **Access token** (what the playbook uses) | `nordvpn login --token <token>` | Unattended builds |
| Token at a prompt | `nordvpn login --token` with no argument: a masked prompt that needs a real terminal | By hand, so the token never appears in argv |
| Browser and callback | `nordvpn login` prints a link. Sign in, copy the final `nordvpn://…` link, then run `nordvpn login --callback "<link>"` | Fallback. Single-use, so by hand only |

## Tokens

- Make one at Nord Account → **NordVPN** → advanced settings → **Get access token**. Confirm with the code Nord sends by email, then **Generate new token**. It's shown only once. The same page has **Revoke**. ([Nord support](https://support.nordvpn.com/hc/en-us/articles/20286980309265))
- There are two types: **30-day** and **non-expiring**. A non-expiring token saves you from rebuilding the vault every month.
- The 6.x CLI takes the token only as an argument or from a TTY prompt. There's no stdin, file or env var option (`cli/terminal.go`). The playbook passes it as an argument with `no_log`, so it's briefly visible in `/proc/<pid>/cmdline`. That's fine on a single-user machine.
- In 6.1.0, plain `nordvpn logout` **keeps the token valid**. `nordvpn logout --revoke-token` revokes it. Older versions worked the other way round with `--persist-token`, but that flag doesn't exist in 6.1.0.
- The CLI help says token login doesn't support MFA. Making a token needs the email code.

## Sessions

- They're stored in `/var/lib/nordvpn/data/settings.dat`, encrypted with a key tied to the machine ID. They survive reboots and upgrades, but **can't be copied** to another machine. Each machine logs in itself.
- nordvpnd renews the session on its own. Not verified: what auto-connect does if the session expires. `check.yml` fails on "Nord is logged in" if you're logged out, so run it now and then.

## Alternatives considered (not used)

- **Plain WireGuard with Nord's API:** `curl -u token:<token> https://api.nordvpn.com/v1/users/services/credentials` gives a `nordlynx_private_key`, and servers come from `/v1/servers/recommendations`. It's undocumented, and you lose `nordvpn connect <country>`, which the [country switcher](Country-Switcher.md) needs.
- **`nordvpn set firewall disabled`:** this also solves the Tailscale clash, but removes Nord's leak protection. See [Firewall](Firewall.md) for the narrower fix used instead.
