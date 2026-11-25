# Tailscale exit node through NordVPN

Turn a Debian machine into a **Tailscale exit node whose internet traffic leaves through NordVPN**. Pick it as the exit node on any device on your tailnet, and that device appears on the internet with a NordVPN IP. It works at home or away.

It uses the official NordVPN Linux app (NordLynx), so switching country is one command, or one tap on the included web page.

The one non-obvious part is a **firewall clash**. NordVPN's app drops Tailscale's own connections to its relays and coordination server. This repo fixes that with a six-line nftables rule, without turning NordVPN's firewall off. See [docs/Firewall.md](docs/Firewall.md).

## Two ways to use it

| | What you get |
|---|---|
| **[standalone/](standalone/)** | Just the nftables fix: one `.nft` file and a systemd unit. For machines where you already run NordVPN and Tailscale |
| **The Ansible playbook** (this folder) | The whole setup on a Debian machine: Tailscale exit node, NordVPN app with token login and auto-connect, the firewall fix, UDP GRO tuning, and a country-switcher page on the tailnet |

Tested with Debian 13 (trixie), NordVPN 6.1.0 and Tailscale 1.104, on a KVM VM. It should work on any Debian machine you can SSH into with sudo: a cloud server, a Raspberry Pi or bare metal. It's offered as is, and NordVPN or Tailscale may change their internals.

## Quick start (playbook)

1. **Tailnet policy:** allow a tag (default `tag:nord-exit`) and auto-approve it as an exit node. See [docs/Architecture.md](docs/Architecture.md#tailnet-policy).
2. **Secrets:** a NordVPN access token and a Tailscale auth key, tagged and pre-approved:
   ```sh
   ansible-vault create group_vars/nord_exit/vault.yml   # format: group_vars/nord_exit/vault.yml.example
   ```
3. **Inventory:** `cp inventory.example.yml inventory.yml`, then set your machine's address and your LAN range.
4. **Run:**
   ```sh
   ansible-playbook site.yml --ask-vault-pass                          # safe to rerun
   ansible-playbook check.yml --ask-vault-pass                         # health check
   ansible-playbook check.yml --ask-vault-pass --tags all,exit-test    # also test the exit from this machine
   ```
5. **Use it:** choose the exit node on your devices. Switch country at `http://<hostname>:8080/`.

Without secrets in the vault, the run stops at each login and tells you how to finish it by hand.

`inventory.yml`, `group_vars/nord_exit/vault.yml` and `ansible.log` are gitignored, so your details stay out of your fork.

## Docs

[docs/index.md](docs/index.md): architecture, setup, NordVPN login, the firewall fix, the country switcher, performance tuning and troubleshooting.

**Don't make this the exit node of the router it sits behind.** That creates a routing loop. See [docs/Troubleshooting.md](docs/Troubleshooting.md).

## License

MIT
