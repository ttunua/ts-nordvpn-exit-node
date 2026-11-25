# Firewall: Nord vs Tailscale

If you don't use Ansible, the [`standalone/`](../standalone/) folder has just this fix: the nft file, the systemd unit and install steps.

## Symptom

As soon as `nordvpn connect` runs, Tailscale on the machine reports *"could not connect to the '<city>' relay server"*, and `sudo tailscale netcheck` shows `UDP: false` with no DERP latency. SSH over the LAN still works.

## Cause

NordVPN 6.x creates an nftables table `inet nordvpn` (`daemon/firewall/nft/nft.go`). Its **output** and **forward** chains have **policy drop**. They accept only:

- `lo`;
- packets or connections marked **0xe1f1**, Nord's own mark, which isn't configurable;
- the allowlisted subnets (your LAN and 100.64.0.0/10) and UDP port 41641;
- the `nordlynx` tunnel.

tailscaled marks its own sockets with fwmark **0x80000**, so its policy routing sends them out `eth0`, not through the tunnel. Nord's output chain doesn't recognise that mark and drops those packets: TCP 443 to the coordination server and DERP, and STUN on other ports. Only UDP 41641 gets through, thanks to the allowlist.

Exit-node traffic itself is fine: it's forwarded to `nordlynx`, which Nord accepts.

## Fix: our own nft table (role `nft_bypass`)

`/etc/nordvpn-tailscale-bypass.nft`:

```
table inet nordvpn_tailscale_bypass {
	chain output {
		type route hook output priority mangle - 10; policy accept;
		meta mark & 0x00ff0000 == 0x00080000 meta mark set 0x0000e1f1
	}
}
```

- It runs just before Nord's chain (priority mangle - 10) and swaps Tailscale's mark for Nord's bypass mark. Nord's rule `meta mark 0xe1f1 … accept` then lets the packet through, and sets the connection mark so replies get back in.
- The chain is `type route`, so the kernel looks up the route again after the mark changes. Nord's `ip rule` 32765 (`not fwmark 0xe1f1 lookup 205`) then sends it out the main table (`eth0`), as Tailscale intended.
- `nordvpn-tailscale-bypass.service` loads it. It's a oneshot ordered `Before=tailscaled.service nordvpnd.service`.

## Why not something else

| Option | Why not |
|---|---|
| Edit Nord's `inet nordvpn` table | Nord rebuilds it on every connect |
| An `accept` rule in your own table | In nftables a drop in any base chain is final. An accept elsewhere doesn't override it |
| `nordvpn set firewall disabled` | Works, but removes Nord's leak protection |
| Allowlist only (100.64.0.0/10, UDP 41641) | Needed, but doesn't cover TCP 443 to the DERP and control servers |
| Raw WireGuard instead of the app | Loses country switching. See [NordVPN login](NordVPN-Login.md) |

## Checking it

```sh
sudo nft list table inet nordvpn_tailscale_bypass
sudo tailscale netcheck | grep -E 'UDP|IPv4'   # UDP: true, IPv4 = your ISP address
sudo tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Health"))'   # []
```

Run `tailscale netcheck` **with sudo**. Without root it can't set the bypass mark, and always reports `UDP: false`.
