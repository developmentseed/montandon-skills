# Deploying ask.montandondata.org

The Chainlit app runs as a systemd service on port 8300 (chosen to avoid clashing
with other services on the box), under a dedicated `askmonty` system user. Nginx
sits in front as a reverse proxy and terminates TLS via certbot.

## 1. Create the `askmonty` user

Runs the app as an unprivileged account instead of root or a personal login, so a
compromise of the app (or its dependencies) doesn't get any more access than the
app itself needs. `-r` makes it a system account (no password login, not listed in
login screens); `-m` still gives it a home directory, which it needs for uv's
cache and its own venv:

```bash
sudo useradd -r -m -d /home/askmonty -s /usr/sbin/nologin askmonty
```

## 2. Deploy the code as that user

```bash
sudo -u askmonty git clone https://github.com/developmentseed/montandon-skills.git /home/askmonty/montandon-skills
cd /home/askmonty/montandon-skills

# install uv for the askmonty user specifically (not system-wide) so the
# systemd unit below can reference a stable, predictable path to it
sudo -u askmonty curl -LsSf https://astral.sh/uv/install.sh | sudo -u askmonty sh

sudo -u askmonty /home/askmonty/.local/bin/uv sync

# .env holds MONTANDON_TOKEN (and any other secrets) — keep it readable only
# by askmonty
sudo -u askmonty sh -c 'echo "MONTANDON_TOKEN=<your-token>" > .env'
sudo chmod 600 /home/askmonty/montandon-skills/.env
```

If you're moving an existing checkout instead of cloning fresh, `chown -R
askmonty:askmonty /home/askmonty/montandon-skills` after copying it into place.

## 3. Install and start the systemd service

```bash
sudo cp deploy/montandon-chainlit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now montandon-chainlit
sudo systemctl status montandon-chainlit
```

It restarts automatically on crash (`Restart=on-failure`) and on server reboot
(`enable`). Logs: `sudo journalctl -u montandon-chainlit -f`.

To deploy a new version: `git pull` as `askmonty` in the repo dir, then `sudo
systemctl restart montandon-chainlit`.

## 4. Nginx + TLS

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ask.montandondata.org
sudo ln -s /etc/nginx/sites-available/ask.montandondata.org /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# point the DNS A/AAAA record for ask.montandondata.org at this server first,
# then issue the cert (certbot edits the nginx config in place to add the 443 block):
sudo certbot --nginx -d ask.montandondata.org
```
