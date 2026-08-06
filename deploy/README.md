# Deploying ask.montandondata.org

The Chainlit app runs standalone (`uv run --env-file .env chainlit run app.py`,
listening on `127.0.0.1:8000` by default). Nginx sits in front as a reverse proxy
and terminates TLS via certbot.

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
uv run --env-file .env chainlit run app.py
```
