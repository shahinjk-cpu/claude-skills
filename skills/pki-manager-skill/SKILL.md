---
name: pki-cli
description: Manage X.509 certificates and SSH certificates via the PKI Manager CLI (`pki`). Use this skill for creating CAs, issuing, renewing, revoking and downloading certificates (PEM, DER, PKCS#12, JKS, private keys), managing CRLs, audit logs, compliance reports and the SSH CA. Triggered by mentions of PKI CLI, `pki` commands, certificate management or CA operations.
---

# PKI Manager CLI

## Overview

`pki` is the command-line client of the PKI Manager REST API. It is one static binary
(version 1.0.0 and later are written in Rust). Use it for all operations.

## Install

Check first: `pki --version`. If `pki` is not on the `PATH`, install a release binary from
<https://github.com/oriolrius/pki-manager-cli/releases>.

```bash
# Linux or macOS: download the archive for this machine and install the binary
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)        T=x86_64-unknown-linux-musl ;;
  Linux-i?86)          T=i686-unknown-linux-musl ;;
  Linux-aarch64)       T=aarch64-unknown-linux-musl ;;
  Linux-armv7l)        T=armv7-unknown-linux-musleabihf ;;
  Darwin-arm64)        T=aarch64-apple-darwin ;;
  *) echo "no release binary for $(uname -sm)"; exit 1 ;;
esac
V=$(curl -fsSL https://api.github.com/repos/oriolrius/pki-manager-cli/releases/latest | jq -r .tag_name)
curl -fsSLO "https://github.com/oriolrius/pki-manager-cli/releases/download/$V/pki-cli-${V#v}-$T.tar.gz"
tar -xzf "pki-cli-${V#v}-$T.tar.gz"
install -m 755 "pki-cli-${V#v}-$T/pki" ~/.local/bin/pki   # or sudo install ... /usr/local/bin/
```

Other ways:

- Debian/Ubuntu: `sudo apt install ./pki-cli_<version>_<arch>.deb` (`amd64`, `i386`, `arm64`, `armhf`).
- Fedora/RHEL: `sudo rpm -i pki-cli-<version>-1.<arch>.rpm` (`x86_64`, `i686`, `aarch64`, `armv7hl`).
- Windows x86-64: download `pki.exe` from the release (1.0.1 and later) and put it on the `PATH`,
  or unzip `pki-cli-<version>-x86_64-pc-windows-msvc.zip`.
  PowerShell: `Invoke-WebRequest https://github.com/oriolrius/pki-manager-cli/releases/latest/download/pki.exe -OutFile pki.exe`.
- From source (Rust 1.88+): `cargo install --locked --git https://github.com/oriolrius/pki-manager-cli`.
- The last Python version (0.5.0) runs with
  `uvx --from "git+https://github.com/oriolrius/pki-manager-cli.git@v0.5.0" pki`.
  Use it only when no release binary is available. Do not use `uvx` without `@v0.5.0`:
  the default branch is Rust and `uvx` cannot build it.

## Configuration

Settings come from (first value wins): CLI option, environment variable, `./.env`,
`~/.config/pki-cli/.env`.

```bash
mkdir -p ~/.config/pki-cli
cat > ~/.config/pki-cli/.env << 'EOF'
PKI_API_URL=https://your-pki-server.example.com/api/v1
PKI_OIDC_URL=https://your-iam-server.example.com/realms/realm/protocol/openid-connect/token
PKI_CLIENT_ID=your-client-id
PKI_CLIENT_SECRET=your-client-secret
EOF
chmod 600 ~/.config/pki-cli/.env
```

- `PKI_API_URL` is mandatory and must end with `/api/v1`. With only `/api`, every call
  fails with `Not Found: Route GET:/api/...`.
- Authentication, one of three modes:
  1. OIDC client credentials: `PKI_OIDC_URL`, `PKI_CLIENT_ID` and `PKI_CLIENT_SECRET`, all three.
  2. A bearer token: `PKI_TOKEN` (or `--token`).
  3. None: only for a server with OIDC disabled.
- Other variables: `PKI_CA_BUNDLE` (PEM file to trust a server with a private CA),
  `PKI_RATE_LIMIT_RETRIES` (retry on HTTP 429), `PKI_TOKEN_CACHE_FILE`, `NO_COLOR`.
- The root options go **before** the command:
  `pki --api-url https://pki.example.com/api/v1 --token "$T" ca list`.

```bash
pki config   # show the settings (secrets are masked)
pki login    # get a token and cache it
pki logout   # clear the cached token
pki health   # check the API
```

## Certificate Authorities

```bash
pki ca list
pki ca list --status active -q "Root" -o json
pki ca get <CA_ID>

# Create a root CA (defaults: --org YMBIHQ, --country ES, RSA-4096, 20 years)
pki ca create --cn "My Root CA" --org "My Organization" --country ES
pki ca create --cn "My CA" --org "Org" --country ES --algorithm RSA-2048 --validity-years 10

pki ca certs <CA_ID>                                  # certificates of this CA
pki ca revoke <CA_ID> --reason cessationOfOperation   # asks for confirmation; -f skips it
pki ca delete <CA_ID> -f                              # --destroy-key also deletes the KMS key

# CA certificate files
pki ca pem <CA_ID> -o ca.pem                          # public URL, no authentication
pki ca download <CA_ID> -f der -o ca.der
pki ca download <CA_ID> -f p12-truststore -o truststore.p12   # password defaults to changeit
pki ca download <CA_ID> -f jks-keystore -p secret -o ca.jks   # keystores need -p
```

A CA keystore (`p12-keystore`, `jks-keystore`) has the CA private key. The server refuses it
(`CA_KEY_EXPORT_DISABLED`) unless it runs with `ALLOW_CA_KEY_EXPORT=true`.

- CA key algorithms: `RSA-2048`, `RSA-4096` only.
- CA validity: `--validity-years` (1-30).

## Certificates

```bash
pki cert list
pki cert list --ca <CA_ID> --status active --type server -o json
pki cert get <CERT_ID>

# Issue (defaults: --type server, RSA-2048, 365 days; the CN is added to the DNS SANs)
pki cert issue --ca <CA_ID> --cn "myserver.example.com" --type server \
    --dns "www.example.com" --dns "api.example.com" --ip "192.168.1.100" \
    --validity 365 --algorithm ECDSA-P256
pki cert issue --ca <CA_ID> --cn "client.example.com" --type client
pki cert issue --ca <CA_ID> --cn "node.example.com" --type dual        # server + client
pki cert issue --ca <CA_ID> --cn "user@example.com" --type email \
    --email "user@example.com" --no-cn-san

# Renew (new key pair by default)
pki cert renew <CERT_ID> --validity 90
pki cert renew <CERT_ID> --same-key --revoke-original
pki cert renew <CERT_ID> --dns new.example.com        # SAN or subject changes

pki cert revoke <CERT_ID> --reason keyCompromise -f --generate-crl
pki cert delete <CERT_ID> -f
```

- Delete works only for a revoked certificate, or one expired for more than 90 days.
- Before PKI Manager 3.19.1 the server cannot delete the original of a renewed certificate
  (`FOREIGN KEY constraint failed`); 3.19.1 deletes it and keeps the renewal.

- Types: `server`, `client`, `dual`, `email`, `code_signing`.
- Key algorithms: `RSA-2048`, `RSA-4096`, `ECDSA-P256`, `ECDSA-P384`.
- Validity: `--validity` in days (1-825).
- A server certificate needs a CN with two or more labels (`web.internal`, not `web`).

### Download

```bash
pki cert download <CERT_ID>                              # PEM certificate, server file name
pki cert download <CERT_ID> -o cert.pem
pki cert download <CERT_ID> -f chain-pem -o fullchain.pem # certificate + issuing CA (server 3.19.1+)
pki cert download <CERT_ID> -f key-pem -o key.pem        # private key (PKCS#8 PEM)
pki cert download <CERT_ID> -f pkcs12 -p secret -o cert.p12
pki cert download <CERT_ID> -f jks -p changeit -o keystore.jks
```

Formats: `pem`, `der`, `chain-pem`, `full-pem`, `full-der`, `csr-pem`, `key-pem`, `key-der`,
`pkcs8-pem`, `pkcs8-der`, `pkcs8-encrypted`, `p12`/`pfx` (alias `pkcs12`), `jks-keystore`
(alias `jks`), `jks-truststore`. `p12`, `pfx`, `jks-*` and `pkcs8-encrypted` need `-p`.
`--encrypt-key` encrypts an exported key with `-p`; `--no-chain` removes the chain from a bundle.

- `chain-pem`: certificate + issuing CA. `full-pem`: certificate + **private key** + issuing CA.
  Never use `full-pem` as a certificate file that others can read.
- On a PKI Manager 3.19.0 server, `chain-pem` has only the certificate and `full-pem` has no CA:
  append the CA yourself (`pki ca pem <CA_ID>`).

## CRLs

```bash
pki crl list <CA_ID>
pki crl generate <CA_ID> --next-update-days 7
pki crl download <CA_ID> --output-file ca.crl         # PEM; -f der for binary
```

## Dashboard, search, audit, reports

```bash
pki stats
pki expiring --limit 10          # 1-20
pki search "example.com"
pki domain list -q example.com
pki audit list --operation ca.create --status failure --limit 20
pki report generate --type certificate_inventory --output-file inventory.csv
```

Report types: `certificate_inventory`, `revocation`, `ca_operations` (CSV only).

## SSH certificates

`pki ssh` drives the SSH CA: `ca`, `host`, `user`, `identity`, `principal`, `token`, `block`,
`cert`, `bulk`, `zone`, plus the public files (`trusted-user-ca-keys`, `host-ca-keys`,
`cert-authority`, `krl`). Run `pki ssh <group> --help` for the options.

```bash
pki ssh ca create --type user --label "User CA"
pki ssh host register --fqdn host1.example.com -k @/etc/ssh/ssh_host_ecdsa_key.pub -a 10.0.0.5
pki ssh host issue --host-id <HOST_ID>
pki ssh host cert <HOST_ID> > ssh_host_ecdsa_key-cert.pub
pki ssh identity create -s alice --email alice@example.com
pki ssh principal create -n deploy
pki ssh principal grant --identity-id <IDENTITY_ID> --principal-id <PRINCIPAL_ID>
pki ssh user issue --identity-id <IDENTITY_ID> -k @~/.ssh/id_ed25519.pub -p deploy \
    -e permit-pty --ttl 3600 -o json | jq -r .certificate > ~/.ssh/id_ed25519-cert.pub
pki ssh trusted-user-ca-keys > /etc/ssh/trusted_user_ca_keys
```

- A host key must be ECDSA P-256 (it also encrypts the host KRL).
- `-k @file` reads the key from a file.

`pki external` calls the machine API with an integration token (`--token`, not the
management token): `health`, `ca-bundle`, `sign`, `revoke`, `certificate-status`, `ssh`, `ra`.

## Output

Most read commands take `-o table` (default) or `-o json`. JSON is the server response,
unchanged. Status lines (✓, ✗) go to stderr, so stdout stays clean for `jq`.

```bash
CA_ID=$(pki ca list -o json | jq -r '.items[0].id')
pki cert list -o json | jq '.items[] | {id, subjectDn, status, notAfter}'
pki expiring -o json | jq -r '.[].id'
```

JSON shapes: `ca list` and `cert list` give `{items, pagination}`; `expiring` gives an array
of `{id, cn, type, san, notAfter, daysRemaining}`; `search` gives `{query, results, totalCount}`;
`ca create` and `cert issue` give an object with `id`.

## Examples

### Create a CA and issue a certificate

```bash
CA_ID=$(pki ca create --cn "Internal CA" --org "MyOrg" --country ES -o json | jq -r '.id')
pki cert issue --ca "$CA_ID" --cn "web.internal" --type server \
    --dns "www.internal" --dns "api.internal"
```

### Renew expiring certificates

```bash
for id in $(pki expiring --limit 20 -o json | jq -r '.[].id'); do
    pki cert renew "$id"
done
```

### Files for Nginx

```bash
pki cert download <CERT_ID> -f chain-pem -o /etc/nginx/ssl/mysite.crt  # cert + CA (3.19.1+)
pki cert download <CERT_ID> -f key-pem  -o /etc/nginx/ssl/mysite.key
```

### Keystore for a Java application

```bash
pki cert download <CERT_ID> -f jks -p changeit -o /opt/app/keystore.jks
```

## Public endpoints (no authentication)

| Endpoint | CLI | Description |
|----------|-----|-------------|
| `GET /health` | `pki health` | Health check |
| `GET /api/docs` | | Swagger UI |
| `GET /api/v1/openapi.json` | | OpenAPI spec |
| `GET /cas/{caId}.pem` | `pki ca pem` | CA certificate (`.pem`, `.crt`, `.der`, `.cer`) |
| `GET /crl/{caId}.crl` | `pki crl download` | CRL (`.crl` PEM, `.der`) |
| `GET /krl/{caId}.bin` | `pki ssh krl` | SSH KRL of a CA |
| `GET /ssh/trusted-user-ca-keys` | `pki ssh trusted-user-ca-keys` | `TrustedUserCAKeys` file |
| `GET /ssh/cert-authority` | `pki ssh cert-authority` | `@cert-authority` known_hosts lines |

## Revocation reasons

`--reason` accepts: `unspecified` (default), `keyCompromise`, `caCompromise`,
`affiliationChanged`, `superseded`, `cessationOfOperation`, `certificateHold`, `removeFromCRL`.

## Quick reference

| Operation | Command |
|-----------|---------|
| List CAs | `pki ca list` |
| Create CA | `pki ca create --cn "Name" --org "Org" --country XX` |
| CA certificate | `pki ca pem <id> -o ca.pem` |
| List certificates | `pki cert list` |
| Issue | `pki cert issue --ca <id> --cn "host.example.com" --type server` |
| Download | `pki cert download <id> -f chain-pem` |
| Renew | `pki cert renew <id>` |
| Revoke | `pki cert revoke <id> --reason <reason> -f` |
| New CRL | `pki crl generate <ca-id>` |
| Stats | `pki stats` |
| Expiring | `pki expiring` |
| Search | `pki search "query"` |
| Help | `pki <command> --help` |
