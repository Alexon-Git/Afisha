# Deployment guide — Afisha

This document explains how to deploy the Afisha project to a Linux server and how CI/CD (GitHub Actions) in this repository will deploy the app.

Server paths (assumed):
- Frontend: `/var/www/alexon/Afisha/frontend/`
- Backend: `/var/www/alexon/Afisha/backend/`

Required server preparation
1. Create a user (e.g. `alexon`) and ensure it has sudo privileges for service control and Docker.
2. Install Docker and Docker Compose v2 (or ensure `docker compose` command exists).
3. Install Nginx and enable the site config (copy `deploy/nginx/afisha.conf` to `/etc/nginx/sites-available/afisha.conf` and symlink to `sites-enabled`).
4. Create directories and set ownership:

```bash
sudo mkdir -p /var/www/alexon/Afisha/frontend
sudo mkdir -p /var/www/alexon/Afisha/backend
sudo chown -R alexon:alexon /var/www/alexon
```

5. (Optional) Set up SSL (Certbot) for the domain.

GitHub Actions secrets required
- `HOST` — server hostname or IP
- `USERNAME` — SSH username (e.g. alexon)
- `PASSWORD` — password for the SSH user (used by sshpass). NOTE: SSH key is recommended instead of a password.
- `PAT` — (optional) GitHub PAT if additional API access needed; not required for these workflows

How CI/CD works (current workflows)
- `deploy-frontend.yml` — builds the frontend (`npm run build`) and rsyncs `frontend/build/` to `/var/www/alexon/Afisha/frontend/` on the server, then reloads nginx.
- `deploy-backend.yml` — rsyncs `backend/` to the server (excluding `data/`) and restarts backend via `docker compose up -d --build`.

Notes and security recommendations
- Using `PASSWORD` and `sshpass` is less secure. Prefer adding an SSH private key to GitHub Secrets (`SSH_PRIVATE_KEY`) and updating workflows to use it.
- Secrets must be stored in the repository's Settings → Secrets & variables → Actions.
- Configure firewall to only allow necessary ports (80/443 for nginx, not exposing backend port publicly).

Systemd/service
- We provide `deploy/systemd/afisha-backend.service` as an example if you want systemd to manage the backend docker-compose lifecycle.

Troubleshooting
- If files are not synced, verify rsync and SSH access manually using the same HOST/USERNAME/PASSWORD.
- Check nginx logs `/var/log/nginx/afisha-error.log` and `/var/log/nginx/afisha-access.log`.
