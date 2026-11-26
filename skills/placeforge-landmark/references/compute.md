# Compute: this machine, a rented GPU, or your own remote machine

`P/.env` (copied from `.env.example`) sets `PF_COMPUTE`.

| Mode | Use when | Needs |
|---|---|---|
| `local` | Stills and short previews; any machine with Blender | Blender 4.2+ (tested: 5.2). GPU picked automatically: Apple Metal, NVIDIA OptiX then CUDA, AMD HIP, Intel oneAPI, else CPU. `device=CPU` forces one |
| `vast` | Films, many views, fast loops | `VAST_API_KEY` in `.env`, a few dollars of credit, `VAST_MAX_PRICE` |
| `ssh` | A machine you already have (RunPod, Lambda, a workstation) | `PF_SSH_HOST`, `PF_SSH_PORT`, `PF_SSH_USER`, `PF_SSH_KEY` |

Rough speeds (Lotus Tower scene): a 1920 x 1280 preview at 64 to 96 samples takes 6 to 90 s on an RTX 4090; a 4K
final a few minutes; a film frame about 10 s with two Blenders per GPU. Ten loops and a 4K final cost well under
$1; a 30 s film (720 frames at 1080p) on three RTX 4090s cost $1.64. A CPU is 20 to 50 times slower: fine for a still overnight, not for a film.

## A rented session

```bash
pf gpu P offers                 # prices now
pf gpu P up                     # says the GPU and price, waits for boot, installs Blender
pf assets P --remote            # models and textures, downloaded by the machine itself
pf render P --name loop01 --view photo,close
...
pf gpu P down && pf gpu P status
```

A second machine: `PF_GPU_NAME=b pf gpu P up` (and the same variable before `pf render` / `pf film render`).

## Traps

- **A machine stuck booting.** After about five minutes, `pf gpu P down` and rent again; put the country in
  `VAST_NOT_GEO`. A few cents lost beats waiting.
- **A host that drops every SSH session.** `pf gpu P bad` records the machine so it is not rented again; then down, up.
- **OptiX fails** (`OPTIX_ERROR_INTERNAL_COMPILER_ERROR`): add `device=CUDA` (about half the speed at night).
- **Uploads stall** on some links: only small text files are sent up (scripts, the map, JSON). Models and textures
  are fetched on the machine (`pf assets P --remote`), one at a time with a pause; some sites answer with a web
  page when hit too fast.
- **Big downloads arrive truncated.** Previews come down as JPEG. Film frames are encoded to one MP4 on the
  machine and only that is pulled; do not pull hundreds of PNGs.
- **Stopping a background job.** Kill the job's shell before its Blenders or it starts the next one:
  `pf gpu P run 'for p in $(pgrep -x blender); do kill $(ps -o ppid= -p $p); done; pkill -x blender'`.
  Never `pkill -f` with text that is also in your own command line.
- **Empty frame files** left by a killed render make the next run skip those frames:
  `pf gpu P run 'find pf/proj/*/film/frames -size -1k -delete'` (the film command does this at its start).
- **Keep the GPU busy.** One Blender leaves a fast GPU idle while the CPU prepares a frame: films run two per GPU
  (`--jobs`). Do not do that on a laptop GPU.
- **External drives.** rsync to or from exFAT drives can truncate files; `pf` stages through a temp folder for
  this reason.
- **Always end with `pf gpu P status`.** A forgotten machine bills by the hour.
