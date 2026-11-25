# Performance

Expect a fraction of your line speed through the exit node. The limit is the exit node's CPU, not the network.

## Why it's CPU-bound

- **Every packet is encrypted twice.** tailscaled decrypts it from your device (userspace wireguard-go), then the kernel's WireGuard (NordLynx) encrypts it again for Nord. Replies go through both in reverse.
- **One core** means tailscaled, the kernel's WireGuard and the packet forwarding all share it.
- **No AVX2 in a VM guest.** Many hypervisors hide AVX2 from the guest by default, so WireGuard's ChaCha20 crypto can't take the fast path.
- **One NIC queue and no UDP GRO forwarding.** All packets come in on one queue, and the kernel handles forwarded UDP packets one at a time instead of in batches.

## What helps

If the exit node is a VM, set these in your hypervisor. The playbook doesn't create or change VMs.

| Setting | Why |
|---|---|
| CPU type `host` (or CPU passthrough) | The guest sees AVX2, so WireGuard's crypto is faster |
| 2 vCPUs | tailscaled and the kernel's WireGuard can run at the same time |
| virtio NIC with multiqueue = number of vCPUs | Incoming packets are spread over the cores |
| UDP GRO forwarding | The kernel batches forwarded UDP packets |

CPU type and queue changes usually need a full stop and start of the VM, not just a reboot.

The `tuning` role does UDP GRO forwarding for you. It installs ethtool and a oneshot unit that runs this at boot, on `lan_iface`:

```sh
/usr/sbin/ethtool -K eth0 rx-udp-gro-forwarding on rx-gro-list off
```

This is Tailscale's advice for Linux exit nodes and subnet routers. See [Performance best practices](https://tailscale.com/kb/1320/performance-best-practices). It needs Tailscale 1.54 or newer and Linux 6.2 or newer. Debian 13 has both.

## What didn't help

| Idea | Why not |
|---|---|
| A 3rd vCPU (with 3 NIC queues) | No measurable gain over 2, within run-to-run noise |
| More memory | 1 GB is plenty. Packets aren't waiting on memory |
| Faster disk | Forwarding doesn't touch the disk |

## Measured example

On a 4-core i5-6500T Proxmox host, with a line of about 230–280 Mbit/s:

| Exit node VM | Speed |
|---|---|
| 1 vCPU, default CPU type | ≈ 97–111 Mbit/s |
| 2 vCPUs, host CPU type, multiqueue, GRO on | ≈ 160–175 Mbit/s |
| 3 vCPUs | no better than 2 |

## How to measure

From a client. This downloads 25 MB from Cloudflare 5 times and prints the speed of each run:

```sh
TS=/Applications/Tailscale.app/Contents/MacOS/Tailscale   # or just: tailscale
$TS set --exit-node=<ts_hostname>
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w '%{speed_download}\n' 'https://speed.cloudflare.com/__down?bytes=25000000' \
    | awk '{printf "%.0f Mbit/s\n", $1*8/1000000}'
done
$TS set --exit-node=
```

- Cloudflare's `__down` endpoint refuses more than 25 MB per request (403), so keep `bytes=25000000`.
- For your line speed, run the loop without the first `set` line. Take the median of the 5 runs.
- Compare on the same Nord server. "Fastest" can pick a far server on its own. Pin it first, for example `nordvpn connect nz102`.
