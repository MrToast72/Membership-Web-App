# Membership Verification Web Application

A web-based membership verification system that replaces desktop barcode scanner apps. Built with FastAPI, SQLite, and deployed via Docker/Traefik.

## Features

- **Membership Verification**: Scan barcodes via USB scanner (acts as keyboard HID)
- **Priority Matching**: Membership # → Email → Name (First Last / Last, First) → Partial match
- **Excel Import**: Import membership lists from .xlsx/.xlsm files (additive merge-based)
- **Audit Trail**: Hash-chained audit log for data integrity
- **Scan History**: All scans logged to SQLite + CSV export
- **Web Admin Panel**: Edit members, import Excel, view history
- **Security**: Formula injection protection, atomic writes, change detection locks

## Quick Start

### Local Development

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker Deployment (Portainer)

1. **Set up GitHub secrets** for Docker image build:
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_PASSWORD`: Your Docker Hub access token

2. **Push to main branch** - GitHub Actions will automatically build and push the image

3. **Deploy with Portainer**:
   ```bash
   # On your server
   curl -L https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
   chmod +x /usr/local/bin/docker-compose
   
   # Create .env file
   echo "DOCKER_USERNAME=your_username" > .env
   echo "MEMBER_BASIC_AUTH_USER=admin" >> .env
   echo "MEMBER_BASIC_AUTH_PASS=your_password" >> .env
   
   # Deploy
   docker-compose pull
   docker-compose up -d
   ```

## Excel Import Format

The system supports Excel files with columns:
- First Name, Last Name (auto-combined to Name)
- Email
- Membership Number
- Membership Type
- Includes Cart (Yes/No)
- Includes Range (Yes/No)
- Membership Amount Used

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SQLITE_DB_PATH` | Path to SQLite database | `data/membership.db` |
| `BACKUP_DIR` | Directory for database backups | `backups` |
| `MEMBER_BASIC_AUTH_USER` | Basic auth username (optional) | - |
| `MEMBER_BASIC_AUTH_PASS` | Basic auth password (optional) | - |

## Spec Compliance

- SQLite as single source of truth
- Atomic writes (temp file → commit → replace)
- Change detection safety locks
- Never overwrite valid DB data with blank Excel values
- Formula injection protection (`=`, `+`, `-`, `@` prefixed values)
- Hash-chained audit trail (SHA-256)
- Traefik integration with Cloudflare cert resolver

## Testing

```bash
pytest tests/ -v
```

## License

MIT
