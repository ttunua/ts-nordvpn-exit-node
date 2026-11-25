# Setup

You run the playbook from your own computer (the control machine). It configures an existing Debian machine over SSH. That can be a VM, a cloud server, a Raspberry Pi or bare metal. Debian 13 (trixie) is tested.

## Prerequisites

- **Ansible** on the control machine (for example `brew install ansible` or `pipx install ansible`).
- **A Debian machine** you can reach by SSH as `nord_user` (default `debian`), with passwordless sudo.
- **A NordVPN subscription.**
- **A Tailscale account**, with admin rights to edit the tailnet policy and make auth keys.

## 1. Tailnet policy

Add `tag:nord-exit` (or your `ts_tag`) and its exit-node auto-approval to your tailnet policy. See the snippet in [Architecture](Architecture.md#tailnet-policy).

## 2. Make the secrets

- **Nord token:** Nord Account → **NordVPN** → advanced settings → **Get access token**. Pick non-expiring or 30-day. See [NordVPN login](NordVPN-Login.md).
- **Tailscale auth key:** admin console → Settings → Keys → **Generate auth key**. Make it **tagged** with your `ts_tag` and **pre-approved**. The key is used only when the machine joins the tailnet. A one-off key is spent by that join. A reusable key works for rebuilds until it expires (90 days at most).

## 3. The vault

```sh
cp group_vars/nord_exit/vault.yml.example group_vars/nord_exit/vault.yml
ansible-vault encrypt group_vars/nord_exit/vault.yml
ansible-vault edit group_vars/nord_exit/vault.yml
```

It holds two values:

```yaml
vault_nordvpn_token: "…"
vault_tailscale_authkey: "tskey-auth-…"
```

`vault.yml` is gitignored. Keep the vault password somewhere safe, such as a password manager.

## 4. The inventory

```sh
cp inventory.example.yml inventory.yml
```

Set the host's address and any variables you want to change. `inventory.yml` is gitignored. The main variables (defaults in `group_vars/all.yml`):

| Variable | Default | What |
|---|---|---|
| `nord_user` | `debian` | Login user that runs the `nordvpn` CLI |
| `ts_tag` | `tag:nord-exit` | Tag the exit node advertises |
| `ts_hostname` | the inventory hostname | Tailscale hostname |
| `debian_release` | `trixie` | Debian release for the apt repos |
| `lan_cidr` | e.g. `192.168.1.0/24` | Your LAN, allowlisted in Nord so you keep SSH |
| `tailnet_cidr` | `100.64.0.0/10` | The tailnet, allowlisted in Nord |
| `lan_iface` | `eth0` | Interface for UDP GRO forwarding |
| `page_port` | `8080` | Port of the country switcher page |
| `install_guest_agent` | `false` | Install qemu-guest-agent (for VMs) |
| `ts_cli` | `/Applications/Tailscale.app/Contents/MacOS/Tailscale` | Tailscale CLI on the control machine, for the exit test |

## 5. Run

```sh
ansible-playbook site.yml --ask-vault-pass --check --diff   # dry run
ansible-playbook site.yml --ask-vault-pass                  # apply
ansible-playbook check.yml --ask-vault-pass                 # health check
ansible-playbook check.yml --ask-vault-pass --tags all,exit-test
```

The exit test runs on the control machine. It records your public IP first, switches your exit node to the new one, and checks that your public IP through it is different. It uses `ts_cli` for that.

## Rerunning

`site.yml` is idempotent. Rerun it after an upgrade or to fix drift. It changes only what differs.

## Without secrets

If a vault value is missing, the run stops at that step and tells you what to do:

- **Tailscale:** it prints a login link. Open it, approve the device, then rerun.
- **Nord:** log in on the machine with the browser method, then rerun:
  ```sh
  nordvpn login                                  # prints a link; sign in in your browser
  nordvpn login --callback "<nordvpn://… link>"  # the final link from the browser
  ```

## Teardown (test machine)

```sh
nordvpn logout          # keeps the token valid; add --revoke-token to revoke it
sudo tailscale logout
```

`--persist-token` doesn't exist in 6.1.0. Then remove the device in the Tailscale admin console if it's still listed.
