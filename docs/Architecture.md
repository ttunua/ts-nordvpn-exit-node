# Architecture

```
 your device ──(WireGuard, Tailscale)──▶ exit node ──(NordLynx tunnel)──▶ Nord server ──▶ internet
  exit node = <ts_hostname>               tailscale0 → forward → nordlynx
```

## Traffic paths on the exit node

| Traffic | Route | Why |
|---|---|---|
| Exit-node traffic forwarded from `tailscale0` | `ip rule` 32765 → Nord's table 205 → `nordlynx` | Nord's default route. Tailscale masquerades it (mark 0x40000) |
| tailscaled's own traffic (control, DERP, STUN, WireGuard on UDP 41641) | fwmark 0x80000 → `ip rule` 5210 → main table → `eth0` → your normal connection | Tailscale's bypass mark. Nord's firewall drops it without [the fix](Firewall.md) |
| LAN (`lan_cidr`, for example 192.168.1.0/24) and tailnet (100.64.0.0/10) | main table | Nord allowlist plus Nord's own `ip rule` entries |
| The machine's own traffic (apt, curl) | table 205 → `nordlynx` | Nord |

So your device's traffic goes through Nord. Tailscale's own connections (to the coordination server, the relays, and direct peer connections) use your normal connection. That keeps direct connections on your LAN fast.

**IPv6:** Nord turns IPv6 off on the machine, so nothing leaves over IPv6. Exit-node clients fall back to IPv4.

**DNS:** the playbook runs `tailscale up --accept-dns=false` on the exit node, so it doesn't fight Nord over DNS. On the clients, DNS follows your tailnet's DNS settings. If your tailnet uses a global DNS resolver such as NextDNS or another DNS-over-HTTPS service, lookups may still leave from the client's own network, not through Nord. Your ISP then sees only encrypted DoH, but the resolver sees your real IP. Changing that is a tailnet-wide DNS setting.

## Tailnet policy

Add the tag, let it advertise an exit node without manual approval, and give it no grants of its own. Example (HuJSON):

```jsonc
{
  "tagOwners": {
    "tag:nord-exit": ["autogroup:admin"],
  },

  "autoApprovers": {
    "exitNode": ["tag:nord-exit"],
  },

  "grants": [
    // Your existing grants. Members reach the exit node through a grant such as:
    // {"src": ["autogroup:member"], "dst": ["*"], "ip": ["*"]},
    // Don't add any grant with "tag:nord-exit" as its src.
  ],

  "tests": [
    {
      "src":  "tag:nord-exit",
      "deny": ["tag:server:22"],
    },
  ],
}
```

- No grant has `tag:nord-exit` as its source, so the exit node **can't start** connections to your other devices.
- The `tests` entry makes the policy check fail if a later change lets it SSH to another tag. Replace `tag:server` with a tag you use.
- Members can use it as an exit node through a grant that lets them reach the internet via exit nodes (for example `autogroup:member → *`).

## Don't use it as the exit node of the router it sits behind

A router can only use an exit node that doesn't reach the internet through that same router. Your exit node reaches the internet through your router. If you set that router's exit node to it, you get a loop: the exit node's own Nord tunnel is sent back into Tailscale, to the exit node itself. Nord can't reach its server, and the whole network loses internet.

Use the exit node per device, or from a router at another location. For a whole network on Nord, use your router's own VPN client. See [Troubleshooting](Troubleshooting.md).

## Roles

| Role | Does |
|---|---|
| `base` | apt full-upgrade, curl, gnupg, nftables; qemu-guest-agent if `install_guest_agent` is true |
| `tuning` | UDP GRO forwarding on `lan_iface` at boot. See [Performance](Performance.md) |
| `nft_bypass` | `/etc/nordvpn-tailscale-bypass.nft` and `nordvpn-tailscale-bypass.service`. See [Firewall](Firewall.md) |
| `tailscale` | apt repo, forwarding sysctl, `tailscale up --authkey` with `--advertise-exit-node --advertise-tags=<ts_tag> --accept-dns=false` |
| `nordvpn` | apt repo (the same as Nord's install.sh), allowlist, kill switch off, token login, auto-connect, connect |
| `switcher_page` | `/opt/nordvpn-page/nordvpn_page.py` and `nordvpn-page.service`. See [Country switcher](Country-Switcher.md) |
