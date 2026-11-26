# Credentials for tools, precedence and environment variables

## Precedence (AWS CLI v2)

The CLI uses the first source that has credentials:

1. Command line options (`--profile`, `--region`, ...)
2. Environment variables
3. Assume role (`role_arn` in the profile)
4. Assume role with web identity
5. IAM Identity Center
6. Credentials file (`~/.aws/credentials`)
7. Custom process (`credential_process`)
8. Config file (`~/.aws/config`)
9. Container credentials (ECS task role)
10. EC2 instance profile

How this plays out (checked with `aws configure list` on CLI 2.33):

- With `AWS_PROFILE=<profile>` **and** `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` set, the CLI uses the
  environment keys. `aws configure list` shows `env` as their type.
- With `--profile <profile>` on the command line, the CLI uses that profile's credentials instead of the
  environment keys.

SDKs and other tools follow a similar chain, but details differ by tool and version. The reliable fix for stale
values is to unset them.

## Environment variables

| Variable | Effect |
|---|---|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | Credentials. They override the profile's. Secret: list the names, never the values. |
| `AWS_PROFILE` | Profile to use when there's no `--profile`. |
| `AWS_REGION` | Region. Overrides `AWS_DEFAULT_REGION` and the profile's `region`. `--region` overrides both. |
| `AWS_DEFAULT_REGION` | Region, below `AWS_REGION`. |
| `AWS_CONFIG_FILE`, `AWS_SHARED_CREDENTIALS_FILE` | Other locations for `~/.aws/config` and `~/.aws/credentials`. |
| `AWS_LOGIN_CACHE_DIRECTORY` | Cache folder for `aws login`. |
| `AWS_ROLE_ARN`, `AWS_WEB_IDENTITY_TOKEN_FILE`, `AWS_ROLE_SESSION_NAME` | Web identity (CI, EKS). |
| `AWS_PAGER` | Set it to empty (`AWS_PAGER=""`) so output never waits on a pager. |

Check names without values:

```bash
env | grep -o '^AWS_[A-Z_]*'
```

```powershell
Get-ChildItem Env:AWS_* | Select-Object -ExpandProperty Name
```

Clear stale credentials:

```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
```

```powershell
Remove-Item Env:AWS_ACCESS_KEY_ID, Env:AWS_SECRET_ACCESS_KEY, Env:AWS_SESSION_TOKEN -ErrorAction SilentlyContinue
```

## `aws configure export-credentials`

This resolves credentials the way the CLI would (SSO, `aws login`, assume role, ...) and prints them in a format.
**The output is the secret.** Only ever use it piped into `eval`/`Invoke-Expression` or as a `credential_process`,
never on its own.

| `--format` | Output looks like | Use with |
|---|---|---|
| `process` (default) | JSON with `Version: 1` | `credential_process` |
| `env` | `export AWS_ACCESS_KEY_ID=...` | bash, zsh, Git Bash: `eval` |
| `env-no-export` | `AWS_ACCESS_KEY_ID=...` | shell variables that aren't exported |
| `powershell` | `$Env:AWS_ACCESS_KEY_ID="..."` | PowerShell: `Invoke-Expression` |
| `windows-cmd` | `set AWS_ACCESS_KEY_ID=...` | cmd: `for /f` |
| `fish` | `set -gx AWS_ACCESS_KEY_ID "..."` | fish: `eval` |

Scope the values to one command:

```bash
# bash / Git Bash. tr strips the \r that Windows builds of the CLI add.
( eval "$(aws configure export-credentials --profile <profile> --format env | tr -d '\r')" && <command> )
```

```powershell
aws configure export-credentials --profile <profile> --format powershell | Invoke-Expression
<command>
Remove-Item Env:AWS_ACCESS_KEY_ID, Env:AWS_SECRET_ACCESS_KEY, Env:AWS_SESSION_TOKEN, Env:AWS_CREDENTIAL_EXPIRATION -ErrorAction SilentlyContinue
```

```bat
for /f "delims=" %i in ('aws configure export-credentials --profile <profile> --format windows-cmd') do @%i
```

In a `.bat` file, write `%%i` instead of `%i`.

Exported values are temporary, often 1 hour for Identity Center role credentials, and they don't refresh. For long
jobs, use `credential_process`.

## `credential_process`

```ini
[profile <profile>-process]
credential_process = aws configure export-credentials --profile <profile> --format process
region = <region>
```

The tool runs the command whenever it needs credentials and reads JSON with `Version` (always `1`),
`AccessKeyId`, `SecretAccessKey`, `SessionToken` and `Expiration`. Nearly every SDK and tool supports
`credential_process`, including older versions that can't read SSO or `aws login` profiles. The CLI doesn't cache
process credentials. A process must never write secrets to stderr, because tools may log it.

## Tool notes

- **AWS CDK.** `cdk deploy --profile <profile>`. Current CDK v2 reads Identity Center profiles. `Unable to resolve
  AWS account to use` almost always means the session expired (run the first check in SKILL.md) or no profile
  reached CDK. If the profile is valid and CDK still fails, use the `export-credentials` one-liner or a
  `credential_process` profile.
- **Terraform (AWS provider).** Set `profile = "<profile>"` in the provider block or `AWS_PROFILE`. Recent provider
  versions read Identity Center profiles. Older ones fail with `No valid credential sources found`. Use a
  `credential_process` profile or the export one-liner.
- **Docker.** A container can't see the host's `~/.aws` unless you mount it. Pass values by name from a scoped
  export: `docker run -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN -e AWS_REGION ...`.
  Mounting `~/.aws` read-only works only if the image's SDK supports the profile type, and it exposes the token
  caches to the container.
- **SDKs** (boto3, JavaScript v3, Java v2, Go v2, .NET, PowerShell). Current versions read `sso-session` profiles.
  `aws login` profiles need recent versions. Otherwise use `credential_process`.
- **AWS Tools for PowerShell.** `-ProfileName <profile>` on cmdlets, or `Set-AWSCredential -ProfileName
  <profile>`.
