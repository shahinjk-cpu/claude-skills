# Windows notes

Checked with AWS CLI 2.33 and Git for Windows.

## Git Bash

### Output ends in `\r\n`

The Windows build of the CLI ends lines with a carriage return. Command substitution in bash strips the `\n` but
keeps the `\r`, so a captured value carries an invisible `\r`. Tokens, IDs and approval values then fail
validation, and `eval` sets variables with a trailing `\r`.

```bash
aws configure get region --profile <profile> | od -c      # shows: u s - e a s t - 1 \r \n
```

Strip it every time you capture or eval CLI output:

```bash
value=$(aws <service> <command> ... --output text | tr -d '\r')
( eval "$(aws configure export-credentials --profile <profile> --format env | tr -d '\r')" && <command> )
```

### Arguments that start with `/` get rewritten

Git Bash turns an argument that looks like a Unix path into a Windows path before the CLI sees it. That includes
the `--name=/...` form:

```text
/app/prod/key   ->   C:/Program Files/Git/app/prod/key
```

This breaks SSM parameter names, CloudWatch log group names (`/aws/lambda/<fn>`), IAM paths and similar. Turn off
the conversion for that command:

```bash
MSYS_NO_PATHCONV=1 aws ssm get-parameter --name /<app>/<env>/<key> --query Parameter.Name --output text
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/<function-name>
```

A leading `//` isn't a fix: it reaches the CLI as `//app/...`. With `MSYS_NO_PATHCONV=1`, give file arguments as
relative paths (`file://policy.json`) or Windows paths (`file://C:/path/policy.json`).

### Home folder

`~/.aws` in Git Bash is the same folder as `%USERPROFILE%\.aws`, which the CLI uses.

## PowerShell

PowerShell splits native output into lines and drops the `\r\n`, so there's no carriage-return problem.

```powershell
# First check, account masked
(aws sts get-caller-identity --profile <profile> --query Arn --output text) -replace '\d{12}','<account>'

# Names of AWS variables, never values
Get-ChildItem Env:AWS_* | Select-Object -ExpandProperty Name

# Clear stale credentials
Remove-Item Env:AWS_ACCESS_KEY_ID, Env:AWS_SECRET_ACCESS_KEY, Env:AWS_SESSION_TOKEN -ErrorAction SilentlyContinue

# Select a profile; turn off the pager
$env:AWS_PROFILE = '<profile>'
$env:AWS_PAGER = ''

# What each profile uses, without secrets
Select-String -Path "$HOME\.aws\config" -Pattern '^\[|sso_session|sso_start_url|login_session|role_arn|source_profile|credential_source|mfa_serial|credential_process' |
  ForEach-Object { $_.Line -replace '\d{12}','<account>' }

# Export credentials into this session
aws configure export-credentials --profile <profile> --format powershell | Invoke-Expression
```

Exported variables stay for the whole PowerShell session. Remove them when the command is done (the "clear"
line, plus `Env:AWS_CREDENTIAL_EXPIRATION`), or run the command in a child process:

```powershell
pwsh -NoProfile -Command { aws configure export-credentials --profile <profile> --format powershell | Invoke-Expression; <command> }
```

Use single quotes around JMESPath queries: a backtick is PowerShell's escape character inside double quotes but is
literal inside single quotes.

```powershell
aws ec2 describe-instances --query 'Reservations[].Instances[?State.Name==`running`].InstanceId' --output text
```

## cmd

| Task | cmd |
|---|---|
| Select a profile | `set AWS_PROFILE=<profile>` |
| Clear stale credentials | `set AWS_ACCESS_KEY_ID=` and the same for `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` |
| Export to the session | `for /f "delims=" %i in ('aws configure export-credentials --profile <profile> --format windows-cmd') do @%i` (`%%i` in a `.bat`) |

## Paths

| | Windows |
|---|---|
| Config | `%USERPROFILE%\.aws\config` |
| Credentials (IAM user keys) | `%USERPROFILE%\.aws\credentials` |
| Identity Center tokens | `%USERPROFILE%\.aws\sso\cache` |
| Assumed-role and SSO role credentials | `%USERPROFILE%\.aws\cli\cache` |
| `aws login` | `%USERPROFILE%\.aws\login\cache` |

Never open or print the files in the cache folders or the credentials file.
