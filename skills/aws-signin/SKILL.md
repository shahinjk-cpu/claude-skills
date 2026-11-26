---
name: aws-signin
description: Sign in to AWS from the command line and fix AWS credential errors without handling secrets. Use when an AWS CLI, CDK, SDK, Terraform or Docker command fails with an expired or missing session ("Token has expired and refresh failed", "Error loading SSO Token", "The SSO session associated with this profile has expired", "Unable to locate credentials", "ExpiredToken", "InvalidClientTokenId", CDK "Unable to resolve AWS account to use"); when the user asks to log in to AWS, refresh SSO, set up an AWS profile or switch accounts; or when the user is away from the machine (on the phone, Remote Control, SSH) and needs a sign-in link. Covers IAM Identity Center (aws sso login, device code), aws login with console credentials, IAM access keys, assume role with MFA, credentials for tools that can't read SSO profiles, CI with OIDC, and logout.
---

# AWS sign-in from the command line

Your job: find out why AWS credentials fail, pick the sign-in method that fits the profile and where the user
is, hand the user **one** thing to do (a link, a code, or one command), then verify and re-run the command that
failed. You start flows and check results; the user signs in. You never touch secrets.

Checked against AWS CLI v2.33. Flags change between versions: if a command here fails, read `aws <command> help`.
Run AWS commands with `AWS_PAGER=""` or `--no-cli-pager` so output never waits on a pager.

## Safety rules (always apply)

1. **The user signs in and approves.** Never type passwords, MFA codes, access keys or authorization codes, and
   never ask for them in chat. When a step needs one, the user types it into their own terminal or browser.
2. **Never print credentials.** Don't read `~/.aws/credentials` or the caches (`~/.aws/sso/cache`,
   `~/.aws/cli/cache`, `~/.aws/login/cache`). Don't run `aws configure export-credentials`,
   `aws sts get-session-token` or `aws iam create-access-key` where the output lands in the transcript. Don't dump
   the environment: list variable **names** only.
3. **Mask account IDs** in everything you show (`<account>`, or only the last 4 digits). Treat start URLs,
   role session names (often an email) and directory IDs the same way.
4. **The sign-in link goes only to the user**, in your reply to them. Never to other sessions, agents, chat
   channels, issues, PRs or logs. Tell the user to approve only if the page is on an AWS domain and the code
   matches the one you gave.
5. **Signing in is not approval for changes.** Read-only checks are fine afterwards. Deploys, writes and deletes
   still need the user's explicit yes for that action.
6. **Config edits:** show the user the block before adding it to `~/.aws/config`. Use only non-secret values they
   gave you. Never write keys anywhere.

## 1. Diagnose

First check (account masked):

```bash
aws sts get-caller-identity --profile <profile> --query Arn --output text | sed -E 's/[0-9]{12}/<account>/g'
```

PowerShell: `(aws sts get-caller-identity --profile <profile> --query Arn --output text) -replace '\d{12}','<account>'`

If it works, sign-in isn't the problem: check which profile and region the failing tool uses, and its permissions.
If it fails, match the error:

| Error text | Usual cause | Next |
|---|---|---|
| `Token has expired and refresh failed` | Identity Center session ended | §3, then §4a/§4b |
| `Error loading SSO Token: Token for <x> does not exist` | never signed in on this machine, or signed out | §4a/§4b |
| `The SSO session associated with this profile has expired or is otherwise invalid` | Identity Center session ended | §4a/§4b |
| `Unable to locate credentials` | no profile selected, misspelled profile, or nothing configured | §2 |
| `ExpiredToken` / `The security token included in the request is expired` | stale temporary credentials, very often in environment variables | §2 |
| `InvalidClientTokenId` / `The security token included in the request is invalid` | keys in env vars from another account, or a deleted key | §2 |
| CDK `Unable to resolve AWS account to use` | CDK got no credentials: expired session or no `--profile` | §1 check, retry with `--profile`, else §5 |
| Terraform `No valid credential sources found` | provider got no usable credentials | §1 check, else §5 |

## 2. See what the CLI is actually using

```bash
aws configure list --profile <profile>   # where each value comes from (env, sso, config-file...); keys masked
aws configure list-profiles
env | grep -o '^AWS_[A-Z_]*'             # names only, never values
```

- **Access-key environment variables beat `AWS_PROFILE`.** A leftover `AWS_ACCESS_KEY_ID` /
  `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` makes commands fail with `ExpiredToken` even right after a fresh
  sign-in, and `aws configure list` shows `env` as their type. An explicit `--profile` on the command line is used
  instead of them. Fix: `unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN` (the user may need to do
  it in their own terminal too).
- `AWS_REGION` beats `AWS_DEFAULT_REGION`, which beats the profile's `region`.
- Your shell may not keep variables between tool calls, and the user's terminal has its own. Put an `export` and
  the command that needs it in the same command line.

Full precedence order and variables: [tools-and-credentials.md](tools-and-credentials.md).

## 3. Pick the method

Find what the profile uses with non-secret keys only:

```bash
grep -nE '^\[|sso_session|sso_start_url|login_session|role_arn|source_profile|credential_source|mfa_serial|credential_process' ~/.aws/config \
  | sed -E 's/[0-9]{12}/<account>/g'
```

Then decide where the user is. Remote Control, "I'm on my phone", or an SSH session means **elsewhere**.
If you can't tell, use the device code flow: it works from any browser, including one on this machine.

| The profile has | User at this machine | User elsewhere |
|---|---|---|
| `sso_session` or `sso_start_url` (IAM Identity Center) | §4a | §4b device code |
| `login_session` (`aws login`) | §4c | §4c `--remote`, which needs the user at a terminal |
| `role_arn` with `mfa_serial` | §4e, the user runs one command | when they reach a terminal, or use an Identity Center profile |
| `role_arn` without MFA | sign in its `source_profile` | same |
| `credential_process` | sign in the profile it exports from | same |
| keys in `~/.aws/credentials` (IAM user) | §4d | §4d |
| nothing, or a new machine | first-time setup: [setup.md](setup.md) | same; `aws configure sso` takes `--use-device-code --no-browser` |

## 4a. IAM Identity Center, browser on this machine

```bash
aws sso login --sso-session <sso-session>     # or: --profile <profile>
```

Run it in the background: it waits until the user finishes. Since CLI 2.22 the default flow is authorization code
with PKCE. It opens the browser on this machine, the user signs in and allows access, and the command exits. Its
URL only works on this same device. One sign-in covers every profile that uses that `sso-session`. If no browser
opens or the user isn't here, stop it and use §4b.

## 4b. IAM Identity Center, user on another device (phone, Remote Control, SSH)

1. Start it in the background:
   ```bash
   aws sso login --sso-session <sso-session> --use-device-code --no-browser
   ```
2. After a few seconds, read its output **once**. It shows a verification URL and a code like `ABCD-EFGH`. If it
   also prints a URL with the code already filled in (it contains `user_code=`), prefer that one.
3. Reply to the user with the link (and the code as a fallback): open it, sign in, check the code matches, allow
   access. The code expires in about 10 minutes.
4. Don't poll. The background command exits by itself: successfully when the user approves, or with an error when
   the code expires. If it expired, start again for a new code.
5. Verify with the §1 check, then re-run the command that failed.

## 4c. `aws login` (console credentials, CLI 2.32.0 or later)

For root users, IAM users and federated console users. IAM Identity Center users use §4a or §4b instead. IAM
identities need the `SignInLocalDevelopmentAccess` managed policy (or equivalent permissions).

```bash
aws login --profile <profile>          # add --region <region> if the profile has none yet
```

It opens the browser on this machine, and the user signs in to the console. It writes `login_session` to the
profile and caches credentials in `~/.aws/login/cache`. The CLI and SDKs refresh them automatically for up to 12
hours (or the principal's session duration), then the user runs `aws login` again.

**From another device:** `aws login --remote` shows a URL. The user signs in on any device and gets an
authorization code to **paste into the CLI's prompt**. A background command can't answer that prompt, and the code
shouldn't go through chat. So the user runs `aws login --remote --profile <profile>` in a terminal they can type
into. If they only have a phone and the account also has an Identity Center profile, use §4b.

## 4d. IAM user access keys (last resort)

AWS recommends temporary credentials (`aws login`, Identity Center, roles) over long-term keys. If the user must
use keys, they run `aws configure --profile <profile>` in **their own terminal** and type the keys there. Keys
never pass through chat or your commands. For old or leaked keys, see rotation in
[setup.md](setup.md#iam-users-and-access-keys).

## 4e. Assume role and MFA

A profile with `role_arn` assumes that role with the credentials of its `source_profile` (or
`credential_source`). If `source_profile` is an Identity Center or `aws login` profile, sign that one in first.
With `mfa_serial`, the CLI asks `Enter MFA code for arn:...:`, a prompt only the user can answer. Ask the user to
run this in their own terminal:

```bash
aws sts get-caller-identity --profile <profile>
```

The CLI caches the role's temporary credentials in `~/.aws/cli/cache`, so your later CLI commands with that
profile work until they expire (`duration_seconds`, default 1 hour). SDK-based tools don't share that cache. Give
them credentials through §5. For more on MFA and `aws sts get-session-token`, see [setup.md](setup.md#assume-role-and-mfa).

## 5. Tools that can't use the profile

Some tools or versions can't read SSO or `aws login` profiles, or can't refresh them. Containers usually can't see
`~/.aws` at all. Give them temporary credentials from the CLI's own resolution without printing them.

One command in bash or Git Bash. The subshell keeps the values out of everything else, and `tr -d '\r'` is required
on Windows:

```bash
( eval "$(aws configure export-credentials --profile <profile> --format env | tr -d '\r')" && cdk deploy )
```

For a container, inside the same subshell, pass the values by name only:
`docker run -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN -e AWS_REGION <image> ...`

PowerShell: `aws configure export-credentials --profile <profile> --format powershell | Invoke-Expression; <command>`
(then remove the variables, see [windows.md](windows.md)). The `windows-cmd` format also exists.

**Persistent option.** Add a profile the tool calls back into whenever it needs fresh credentials. This is better
for long deploys, because exported values expire and don't refresh:

```ini
[profile <profile>-process]
credential_process = aws configure export-credentials --profile <profile> --format process
region = <region>
```

The underlying sign-in still has to be valid. Never run `export-credentials` on its own: its output is the secret.
For CDK, Terraform, Docker and SDK notes, see [tools-and-credentials.md](tools-and-credentials.md).

## 6. After signing in

- Run the §1 check, then re-run the command that failed.
- Tell the user which profile and role are active, with the account masked.
- Ask before anything that changes resources. The sign-in doesn't authorize it.

## 7. Sign out

- `aws sso logout` removes all cached Identity Center tokens and the credentials derived from them, for every
  profile.
- `aws logout --profile <profile>` (or `--all`) does the same for `aws login` profiles.
- Assumed-role credentials in `~/.aws/cli/cache` expire on their own. The user can delete that folder to drop them
  sooner.

The cache locations and their contents are listed in [setup.md](setup.md#sign-out-and-caches).

## Reference files

- [setup.md](setup.md): first-time setup and config blocks (Identity Center, several accounts and roles, `aws
  login`), IAM users and key rotation, assume role and MFA, CI and servers (GitHub Actions OIDC, instance and task
  roles), sign-out and caches.
- [tools-and-credentials.md](tools-and-credentials.md): credential precedence, environment variables,
  `export-credentials` formats, `credential_process`, notes for CDK, Terraform, Docker and SDKs.
- [windows.md](windows.md): Git Bash carriage returns and path conversion, PowerShell and cmd equivalents.
