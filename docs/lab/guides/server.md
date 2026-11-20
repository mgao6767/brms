# Running the app on a server

`brms-web` is a small web server. On your own computer it listens only on `127.0.0.1`. To share it
with colleagues or students, run it on a server.

## Start it

```bash
pip install "brms[web]"
brms-web --host 0.0.0.0 --port 8765 --data-dir /srv/brms --workers 4 --no-browser
```

| Option | Meaning |
|---|---|
| `--host 0.0.0.0` | listen on every network interface (default `127.0.0.1`, this computer only) |
| `--port` | the port (default 8765) |
| `--data-dir` | where banks and runs are stored (default `$BRMS_WEB_HOME` or `~/.brms-web`) |
| `--workers` | how many runs execute at once; each takes one CPU core and a few hundred MB of memory |
| `--no-browser` | do not try to open a browser |

Each run executes in its own process. A crashed run (for example, out of memory) is reported as
failed and the server carries on. Runs that were in progress when the server stopped are marked
failed when it restarts.

## Keep it running

With systemd, `/etc/systemd/system/brms-web.service`:

```ini
[Unit]
Description=BRMS Stress Lab
After=network.target

[Service]
User=brms
ExecStart=/opt/brms/venv/bin/brms-web --host 127.0.0.1 --port 8765 --data-dir /srv/brms --workers 4 --no-browser
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Protect it

!!! warning
    The app has no user accounts or rate limits. Anyone who can reach it can build banks, start runs
    and delete them. Put it behind a reverse proxy that requires a login before you expose it.

For example with nginx, basic authentication and TLS, forwarding to the app on `127.0.0.1:8765`:

```nginx
server {
    listen 443 ssl;
    server_name lab.example.org;
    # ssl_certificate ... ; ssl_certificate_key ... ;
    location / {
        auth_basic "BRMS Stress Lab";
        auth_basic_user_file /etc/nginx/brms.htpasswd;
        proxy_pass http://127.0.0.1:8765;
        proxy_read_timeout 120s;
    }
}
```

## Data

Each bank and run is a folder under `--data-dir` (`banks/<id>/`, `runs/<id>/`). Back it up as you
would any folder; delete a folder to remove an item. The demo banks come from the installed
package and are not copied.

The JSON API behind the app is documented at `/docs` on the running server.
