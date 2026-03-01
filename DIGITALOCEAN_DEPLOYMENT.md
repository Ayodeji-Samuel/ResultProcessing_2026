# DigitalOcean Deployment Notes

## 1) Environment variables (required)
Set these on your server/app platform:

- `FLASK_CONFIG=production`
- `SECRET_KEY=<long-random-value>`
- `DATABASE_URL=<digitalocean-postgresql-url>`

`DATABASE_URL` should use `postgresql://...` format.

## 2) Install dependencies

```bash
pip install -r requirements.txt
```

## 3) Initialize database schema

```bash
python run.py
```

The app creates tables automatically on startup if they do not exist.

## 4) Create first admin account securely

```bash
# Optional extra protection
export ADMIN_BOOTSTRAP_TOKEN=<one-time-token>

# Create admin with generated temporary password
python create_admin.py create \
  --username admin@yourdomain.edu \
  --full-name "System Administrator" \
  --generate-password \
  --bootstrap-token <one-time-token>
```

If you do not set `ADMIN_BOOTSTRAP_TOKEN`, omit `--bootstrap-token`.

## 5) Clean demo/test data before production upload

```bash
python clean_test_data.py --dry-run
python clean_test_data.py --execute --delete-non-admin-users --clean-uploads
```

## 6) Important production behavior

- No default HoD/admin account is auto-created.
- Production startup fails if `SECRET_KEY` or `DATABASE_URL` is missing.
- Keep `.env` out of version control (already covered by `.gitignore`).
