# Country switcher

Open **`http://<ts_hostname>:8080/`** on any device that's on your tailnet. With the MagicDNS full name: `http://<ts_hostname>.<your-tailnet>.ts.net:8080/`. The port is `page_port`.

It shows `nordvpn status`, with buttons for **Fastest**, a list of countries, and **Disconnect**. A switch takes about a second. Anyone using the exit node at that moment loses their connection for about a second.

## How it's built

- `/opt/nordvpn-page/nordvpn_page.py`: standard-library Python (`http.server`). It reads `PORT` from its environment. It binds **only** to the machine's Tailscale IPv4 (`tailscale ip -4`), so it's not reachable from the LAN.
- It accepts only the countries in its built-in list, plus `fastest` and `disconnect`. Anything else gets **403**.
- It refuses POSTs whose `Origin` doesn't match `Host`, so a website you visit can't switch your VPN.
- `nordvpn-page.service` runs as `nord_user` (group `nordvpn`), with `Restart=always`, so it waits for Tailscale to get its IP at boot.
- After a reboot, Nord auto-connects to the **fastest** server, whatever country you picked before.

## Change the country list

Edit `COUNTRIES` in `roles/switcher_page/files/nordvpn_page.py` and rerun the playbook. Names must match `nordvpn countries`, for example `New_Zealand` or `United_States`.

## iPhone and iPad

- Type the URL with `http://` in full. Safari can treat a bare short name as a search.
- The Tailscale app must be **Connected**. For the short name, "Use Tailscale DNS" must be on. Otherwise use the full MagicDNS name or the node's 100.x.y.z address.
- **Shortcut:** add **Get Contents of URL** with URL `http://<ts_hostname>:8080/`, method **POST**, request body **Form**, and a field `c` = `Japan` (or `fastest`, `disconnect`). Shortcuts sends no Origin header, so the page accepts it.
