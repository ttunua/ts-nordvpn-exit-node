# NordVPN + Tailscale on Linux: fix for Tailscale losing its relays

When the NordVPN Linux app (6.x) connects on a machine that also runs Tailscale, especially a Tailscale **exit node**, Tailscale loses its connection to its relay (DERP) and coordination servers. This repo is a six-line nftables rule that fixes it **without** turning off NordVPN's firewall.

Tested with NordVPN 6.1.0 (NordLynx), Tailscale 1.104 and Debian 13 (nftables). Offered as is: Nord or Tailscale may change their internals.

## Symptoms

Right after `nordvpn connect`:
- `tailscale status` shows a health warning like *"Tailscale could not connect to the '<city>' relay server"*.
- `sudo tailscale netcheck` shows `UDP: false` and no DERP latencies.
- Peers may still connect directly over UDP 41641 (if you allowlisted it), but anything that needs a relay or the control plane fails.

## Cause

The NordVPN app creates an nftables table `inet nordvpn`. Its `output` chain has **policy drop** and only accepts:
- loopback,
- packets or connections marked **`0xe1f1`** (Nord's own mark, not configurable),
- allowlisted subnets and ports,
- traffic on the `nordlynx` tunnel.

See `daemon/firewall/nft/nft.go` in [NordSecurity/nordvpn-linux](https://github.com/NordSecurity/nordvpn-linux).

tailscaled marks its own sockets with fwmark **`0x80000`**, and its policy routing (`ip rule` 5210: `fwmark 0x80000/0xff0000 lookup main`) sends them out your normal interface rather than the tunnel. Nord's chain doesn't recognise that mark, so it drops tailscaled's TCP 443 to the coordination and DERP servers, and its STUN probes.

## Fix

Add your own table whose `output` chain runs just **before** Nord's and swaps Tailscale's mark for Nord's:

```
meta mark & 0x00ff0000 == 0x00080000 meta mark set 0x0000e1f1
```

- Nord's rule `meta mark 0xe1f1 … accept` then accepts the packet, and sets the connection mark so replies get back in.
- The chain is `type route`, so the kernel looks up the route again after the mark changes. Nord's `ip rule` (`not fwmark 0xe1f1 lookup <nord table>`) then sends it out the main table, which is where Tailscale wanted it.
- Exit-node traffic forwarded from `tailscale0` is unmarked, so it still goes through `nordlynx`.

Why not the alternatives:

| Option | Problem |
|---|---|
| Edit Nord's `inet nordvpn` table | Nord rebuilds it on every connect |
| An `accept` rule in another table | In nftables a drop in any base chain is final; an accept elsewhere doesn't override it |
| `nordvpn set firewall disabled` | Works, but removes Nord's leak protection |
| Allowlist only (`100.64.0.0/10`, UDP 41641) | Needed, but doesn't cover TCP 443 to the DERP and control servers |

## Install

As root, on the machine running both:

```sh
apt-get install -y nftables     # for the nft command; Debian/Ubuntu
install -m 644 nordvpn-tailscale-bypass.nft /etc/nordvpn-tailscale-bypass.nft
install -m 644 nordvpn-tailscale-bypass.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now nordvpn-tailscale-bypass.service
```

The unit runs before `tailscaled` and `nordvpnd` at boot. Re-applying is safe: the file deletes and recreates its own table.

Recommended Nord settings next to it (replace the LAN range with yours):

```sh
nordvpn allowlist add subnet 192.168.1.0/24      # your LAN, so you keep SSH
nordvpn allowlist add subnet 100.64.0.0/10       # the tailnet
nordvpn allowlist add port 41641 protocol UDP    # Tailscale direct connections
nordvpn set killswitch off                       # or the LAN/tailnet get cut when Nord drops
```

For an exit node, also turn on forwarding (`net.ipv4.ip_forward=1`, `net.ipv6.conf.all.forwarding=1`) and run `tailscale up --advertise-exit-node`. Using `--accept-dns=false` on the exit node avoids a DNS tug-of-war with Nord.

## Check

```sh
sudo nft list table inet nordvpn_tailscale_bypass
sudo tailscale netcheck | grep -E 'UDP|IPv4'      # UDP: true, IPv4 = your ISP address
tailscale status                                  # no relay health warning
```

Run `tailscale netcheck` **with sudo**. Without root it can't set the bypass mark, and it always reports `UDP: false` on a Nord-protected machine.

## Uninstall

```sh
systemctl disable --now nordvpn-tailscale-bypass.service
rm /etc/systemd/system/nordvpn-tailscale-bypass.service /etc/nordvpn-tailscale-bypass.nft
systemctl daemon-reload
```

## Gotchas found along the way

| Symptom | Cause | Fix |
|---|---|---|
| Whole network loses internet when its router uses this exit node | Routing loop: the exit node reaches the internet through that same router, so its own Nord tunnel is sent back to itself | Use the exit node per device, or from routers elsewhere. For a whole network, use the router's own VPN client |
| `nordvpn set technology nordlynx` → "Command 'technology' doesn't exist" | Removed in 6.x, where NordLynx is the default | Nothing to do |
| First `nordvpn` command after adding a user to group `nordvpn` → "Permission denied … usermod -aG nordvpn" | The login session predates the group change | Log out and back in (in Ansible: `meta: reset_connection`) |
| `nordvpn logout --persist-token` → "flag provided but not defined" | Not in 6.1.0. Plain `logout` keeps the token; `--revoke-token` revokes it | Use plain `nordvpn logout` |
| An exit-node client (seen on iOS) has no internet, though `tailscale ping` works | Its tunnel went stale after a network change | Turn Tailscale off and on in the client |

## License

MIT
