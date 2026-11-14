---
name: viral-video-cloner
description: Recreate a viral video with the user's own person, product, outfit or place in ChatCut Desktop, keeping the source's moves, camera and timing (TikTok, Reels and Shorts trends, dances, UGC ads, TV commercials). Use when the user wants to recreate, clone, remake, copy or replicate a video, copy the moves, make the same video with my product or my face, put themselves into a reference clip, or cut their own footage like a reference video, or says 复刻, 爆款复刻, 做同款, 模仿, 照着, 一模一样, 换成我的, 换人. Sets up ChatCut Desktop on first use (install or update, sign-in), recreates with its bundled video-gen Skill and remake tool, collects the source video and photos in one message, and quotes length and credits before any paid generation. Not for voice cloning, or for editing without a reference video.
---

# Viral Video Cloner

Recreate a video the user points to (a viral trend, a dance, a UGC ad or a TV commercial) with their own person, product, outfit or place, in ChatCut Desktop on their computer. The result keeps the source's moves, camera and timing; only what the user names changes. Generating spends the user's ChatCut credits.

The user's message is the request: keep the video, photos, footage and wording they gave through every step, and ask only for what is still missing. Reply in their language. Call the app "ChatCut" and the paid tier "membership" without naming a plan (in Chinese, 会员, and 积分 for credits), and keep internal names such as ChatCut Desktop, `chatcut_desktop` and MCP out of your messages.

## Start here

If this conversation lists tools from the local MCP server `chatcut_desktop` (include the host's deferred or searchable tools), call `get_active_project` (it may be listed as `chatcut_desktop.get_active_project` or `mcp__chatcut_desktop__get_active_project`). A hosted ChatCut Web connector is a different product; do not use it for this.

- `signedIn: false`, or a tool says ChatCut is signed out or asks for sign-in: ChatCut is installed and only needs sign-in. Go to "Finish setup". Do not reinstall or run the Doctor Skill.
- Otherwise `surface: "desktop"`, even when `projectId` is null, means ChatCut is connected. Do not reinstall; go to "Recreate".
- No `chatcut_desktop` tools: go to "Install".

## Install

Read the official guide with `curl -fsSL https://chatcut.io/desktop` (`curl.exe` on Windows); a web tool's summary can drop its commands. Install with the commands below instead of the guide's, so ChatCut records this skill as the source. They need no Node.js, and they also work when the guide cannot be read:

- macOS 13+: `curl -fsSL https://chatcut.io/install.sh | CHATCUT_INSTALL_SOURCE=oss_viral_cloner sh`
- Windows 10+ x64, in PowerShell: `$env:CHATCUT_INSTALL_SOURCE='oss_viral_cloner'; irm https://chatcut.io/install.ps1 | iex`

In an agent sandbox (Codex's default), request to run the guide fetch and the installer outside it right away: inside it they fail, and macOS reports a valid app as damaged.

The installer verifies the app and opens it, and ChatCut then connects itself to this agent, so nobody clicks Connect. Do not run `codesign` or `spctl`, inspect windows with `osascript`, or build your own app, launcher or web page. If the installer fails, report its actual error. If it says ChatCut must be quit for an update, ask the user to save their work and quit normally, then run it again. Then go to "Finish setup".

## Finish setup

Ask only for what is actually missing, and check the required tools and Skills again after each step. Follow the tool's `nextStep`, connection diagnostics and current host documentation to choose how to continue:

- ChatCut is connected here but signed out: follow the `nextStep` the tool returned; on newer versions, repeating the account call opens sign-in by itself. If it returned none, ask the user to sign in inside ChatCut. When only the user can finish sign-in, ask them to reply when done and stop, without mentioning a new conversation. Then check again and continue here.
- Setup is complete but a required tool or Skill is missing, even when other ChatCut tools work: search the host's deferred tools and native Skill catalog. If still missing, choose the action that this host requires: refresh in this conversation; restart the host app and resume this conversation; or continue in a new conversation. These are alternatives, not a fixed sequence. For a restart, name the app to quit and reopen, ask the user to save ongoing work, then return and tell you when ready. In a terminal agent, exit and reopen it when its documentation requires that to reload tools.
- If setup is incomplete or a tool reports a connection error, follow the official guide to address that specific problem. Report the actual error and remaining action, preserving completed setup.

When a new conversation is needed, provide one complete continuation prompt in a single fenced `text` block for copying, in the user's language. Include the verified installation and sign-in state, the original request word for word, full paths or links to supplied media, any selected workflow and project, and the remaining steps. Ask the next agent to verify access and continue from that state. Do not replace the request with a generic setup prompt. If the current conversation can resume after a refresh, login or restart, verify access and continue with the request already supplied.

## Recreate

1. Recreating needs a ChatCut membership. Check this first, before creating a project, with `read_billing`, or `estimate_generation` if it is not listed; a failed check does not mean the account is free. If the user is not a member, explain that and open `chatcut://billing` with this computer's URL opener, outside any sandbox. If it cannot open, tell them where it is: inside a project, **Upgrade** (升级) at the top right; outside a project, click the avatar at the bottom left. The user chooses and pays, never you. Stop until they have, then check again and continue with what they already gave.
2. Read the `video-gen` Skill that ChatCut installed for this agent (listed with your other Skills as `chatcut-video-gen`) and the live `submit_video_remake` tool description, and follow them with the user's video and changes. Do not look for another Skill with `manage_skill`. If either is missing, search the host's deferred tools and native Skill catalog. Still missing does not prove ChatCut is out of date: run the installer above once if it has not already completed during this setup, then go to "Finish setup". The installer updates an older ChatCut and reports when it is already current. Resume this workflow once both the tool and Skill are available.
3. If the source video or what to swap in is missing, ask once, in one short message, for the video link or file, photos or footage of the person, product or place, and one sentence on what to change. Never pick a video yourself.
4. A generation you submit starts at once and spends credits with no confirmation in ChatCut, so first tell the user the length and estimated credits, and wait for their go-ahead.
