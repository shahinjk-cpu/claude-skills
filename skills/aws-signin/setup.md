# Setup and configuration reference

All values in angle brackets are placeholders. Account IDs, start URLs and role names aren't secrets, but they're
private: mask them when you show them. Keys and tokens are secrets and never go in `~/.aws/config` through you.

On Windows the files live in `%USERPROFILE%\.aws\` (Git Bash shows the same folder as `~/.aws/`).

## IAM Identity Center (recommended for organizations)

### Interactive setup

```bash
aws configure sso                                   # browser on this machine
aws configure sso --use-device-code --no-browser    # user signs in from another device
```

It asks for a session name, the start URL, the Identity Center region and the registration scopes (accept
`sso:account:access`). Then it signs in, lists the accounts and roles the user can pick, and asks for the default
region, output format and profile name. It's interactive, so the user runs it in their own terminal. Or you write
the blocks below with values the user gives you, then run `aws sso login`.

`aws configure sso-session` creates only the `[sso-session]` block.

### Config blocks

```ini
[sso-session <sso-session>]
sso_start_url = https://<your-subdomain>.awsapps.com/start
sso_region = <identity-center-region>
sso_registration_scopes = sso:account:access

[profile <profile>]
sso_session = <sso-session>
sso_account_id = <account-id>
sso_role_name = <role-name>
region = <region>
output = json
```

`sso_start_url` and `sso_region` are required in the session block. The account and role go in the profile, not
in the session.

### Several accounts and roles under one session

```ini
[profile <dev-profile>]
sso_session = <sso-session>
sso_account_id = <dev-account-id>
sso_role_name = <role-name>
region = <region>

[profile <prod-readonly-profile>]
sso_session = <sso-session>
sso_account_id = <prod-account-id>
sso_role_name = <read-only-role-name>
region = <region>
```

One `aws sso login --sso-session <sso-session>` signs in all of them. Pick one per command with `--profile`, or for
a shell with `export AWS_PROFILE=<profile>`. List them with `aws configure list-profiles`.

### Legacy form

A profile that holds `sso_start_url` and `sso_region` itself, with no `sso_session`, is the legacy
non-refreshable form. The CLI can't refresh its token automatically, so the user signs in more often. Move it to an
`[sso-session]` block as above.

### How long a sign-in lasts

The Identity Center administrator sets this: the portal session duration, and the permission set's session
duration for the role credentials. The CLI can't extend it. When it ends, sign in again.

## `aws login` (console credentials)

- CLI 2.32.0 or later.
- For root users, IAM users and federated console sessions. IAM Identity Center users use `aws sso login`.
- IAM identities need the `SignInLocalDevelopmentAccess` AWS managed policy (or equivalent `signin:` permissions).
  The root user needs nothing extra.
- `aws login --profile <profile>` writes the profile for you:

  ```ini
  [profile <profile>]
  login_session = arn:aws:iam::<account-id>:user/<user-name>
  region = <region>
  ```

- Credentials are cached in `~/.aws/login/cache` (`%USERPROFILE%\.aws\login\cache` on Windows). Change the folder
  with `AWS_LOGIN_CACHE_DIRECTORY`.
- They refresh automatically, every 15 minutes as needed, for up to 12 hours or the principal's session duration.
  After that, run `aws login` again.
- `aws login --remote` is for a CLI on a machine without a browser. It shows a URL, the user signs in on any
  device, and the page shows an authorization code the user pastes into the CLI prompt.
- Older SDKs and tools may not support these profiles yet. Use `credential_process` (see
  [tools-and-credentials.md](tools-and-credentials.md)).

## IAM users and access keys

Discouraged. AWS's guidance is to use temporary credentials (`aws login`, Identity Center, roles) instead of
long-term access keys. If the user still needs them:

- **Set up:** the user runs `aws configure --profile <profile>` in their own terminal and types the access key ID
  and secret there. They're stored in plain text in `~/.aws/credentials`.
- **Never** through chat, never as command arguments you run, never in `~/.aws/config` by you.
- **Better for an IAM user:** `aws login` (CLI 2.32+) gives the same identity with temporary credentials.

### Rotation

The user does this in the IAM console or their own terminal, because creating a key prints its secret once:

1. Create a second access key. A user can have at most two.
2. Update every place that uses the old key, then confirm they work.
3. Deactivate the old key, watch for failures, then delete it.

Rotate on a schedule and right away if a key may have leaked. See "Manage access keys for IAM users" in the IAM
User Guide. Don't run `aws iam create-access-key` yourself: its output contains the secret.

## Assume role and MFA

```ini
[profile <role-profile>]
role_arn = arn:aws:iam::<account-id>:role/<role-name>
source_profile = <base-profile>
mfa_serial = arn:aws:iam::<account-id>:mfa/<device-name>
duration_seconds = 3600
role_session_name = <session-name>
region = <region>
```

- `source_profile`: the profile whose credentials assume the role. It can be an Identity Center or `aws login`
  profile, which must be signed in first.
- `credential_source`: use instead of `source_profile` on AWS compute or CI: `Environment`,
  `Ec2InstanceMetadata` or `EcsContainer`.
- `mfa_serial`: the MFA device ARN or a hardware token's serial number. The CLI then prompts
  `Enter MFA code for ...`, and only the user answers it, in their own terminal.
- `duration_seconds`: from 900 up to the role's maximum session duration (at most 43200). Default 3600. Role
  chaining (a role assuming another role) is limited to 1 hour.
- `external_id`: only when the role's trust policy requires it.
- `role_session_name`: optional. The CLI generates one if it's missing.

The CLI caches assumed-role credentials in `~/.aws/cli/cache` until they expire. So once the user has run one
command and typed the MFA code, your CLI commands with that profile work without prompting. SDK-based tools don't
read that cache. Give them credentials with `export-credentials` or `credential_process`.

### `aws sts get-session-token`

This is for IAM users whose policies require MFA for API calls:

```bash
aws sts get-session-token --serial-number <mfa-device-arn> --token-code <code-from-device> --duration-seconds 43200
```

The user runs it, because the code comes from their device and the output contains temporary keys. The duration is
900 to 129600 seconds, default 43200 for IAM users. Root sessions are limited to 1 hour. A role profile with
`mfa_serial` is usually simpler, because the CLI handles the code prompt and the caching.

## CI and servers

No long-lived keys in CI secrets or on servers.

### GitHub Actions with OIDC

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v6
    with:
      role-to-assume: arn:aws:iam::<account-id>:role/<ci-role-name>
      aws-region: <region>
```

One-time setup in the AWS account:

1. Add an IAM OIDC identity provider for `token.actions.githubusercontent.com`.
2. Create a role whose trust policy restricts `token.actions.githubusercontent.com:sub` to your repository and
   branch or environment, for example `repo:<org>/<repo>:ref:refs/heads/main`.

`role-duration-seconds` defaults to 3600. Other CI systems (GitLab, Bitbucket, CircleCI and others) offer OIDC
too.

### AWS compute

EC2 instance profiles, ECS task roles, Lambda execution roles and EKS (Pod Identity or IRSA) supply credentials
automatically. They're at the end of the credential chain, so a stray environment variable or `~/.aws` file on the
host overrides them.

## Sign out and caches

| What | Command | Cache (Windows: under `%USERPROFILE%\.aws\`) |
|---|---|---|
| IAM Identity Center | `aws sso logout` (all profiles) | `~/.aws/sso/cache` (tokens), `~/.aws/cli/cache` (role credentials) |
| `aws login` | `aws logout --profile <profile>`, or `aws logout --all` | `~/.aws/login/cache`, or `AWS_LOGIN_CACHE_DIRECTORY` |
| Assume role | expires on its own; delete the folder to drop it sooner | `~/.aws/cli/cache` |
| IAM user keys | remove the profile from `~/.aws/credentials`; deactivate the key in IAM | `~/.aws/credentials` |

These caches hold live tokens. Never read, print or copy them. Signing out of the CLI doesn't end the browser's
portal or console session.
