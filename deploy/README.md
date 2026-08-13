# Deploying ask.montandondata.org

The Chainlit app runs standalone on port 8300 (chosen to avoid clashing with other
services on the box). Nginx sits in front as a reverse proxy and terminates TLS
via certbot.

## One-time server setup

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ask.montandondata.org
sudo ln -s /etc/nginx/sites-available/ask.montandondata.org /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# point the DNS A/AAAA record for ask.montandondata.org at this server first,
# then issue the cert (certbot edits the nginx config in place to add the 443 block):
sudo certbot --nginx -d ask.montandondata.org
```

## Running the app

Process management isn't included here — run it however you're already running it
(tmux, nohup, etc.):

```bash
uv run --env-file .env chainlit run app.py --port 8300
```
