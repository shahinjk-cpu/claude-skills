#!/bin/bash
# gpu.sh: one remote render machine for a placeforge project. `pf gpu ...` calls this; you can call it directly too.
#
#   PF_PROJECT=<project dir> gpu.sh <command>
#
#   status                  credit and machines (vast) or the configured host (ssh)
#   offers [maxprice]       GPUs on offer under the price cap (vast)
#   up [gpu ...]            vast: rent the cheapest matching offer (default RTX_5090 RTX_4090), wait, install Blender
#                           ssh:  install Blender on the machine you already have
#   push <local> <remote>   copy a folder up          pull <remote> <local>   copy a folder down
#   run <command>           run a command there       bg <name> <command>     run it in the background (log: ~/<name>.log)
#   log <name> [lines]      tail a background job's log
#   down                    vast: DESTROY the machine (billing stops). ssh: nothing to destroy.
#   PF_GPU_NAME=b gpu.sh ...   the same commands for a second machine (each name = its own rented machine)
#
# Settings come from <project>/.env (see .env.example): PF_COMPUTE=vast|ssh, VAST_API_KEY, VAST_MAX_PRICE, VAST_SSH_KEY,
# VAST_NOT_GEO, PF_SSH_HOST, PF_SSH_PORT, PF_SSH_USER, PF_SSH_KEY. Keys are read, never printed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PROJ="${PF_PROJECT:?set PF_PROJECT to the project folder}"
die() { echo "gpu: $*" >&2; exit 1; }
envget() { # value of KEY from the environment, else from the project's .env, else from ~/.config/placeforge/.env
  local k="$1" v="${!1:-}" f
  if [ -z "$v" ]; then
    for f in "$PROJ/.env" "$HOME/.config/placeforge/.env"; do
      [ -f "$f" ] || continue
      v=$(sed -nE "s/^[[:space:]]*(export[[:space:]]+)?$k=//p" "$f" | head -1 | tr -d '"'"'"'\r' | sed 's/[[:space:]]*$//')
      [ -n "$v" ] && break
    done
  fi
  printf '%s' "$v"
}
MODE="$(envget PF_COMPUTE)"; MODE="${MODE:-vast}"
[ "$MODE" = local ] && die "PF_COMPUTE=local: renders run on this machine, there is no remote machine to manage"
MAXP="$(envget VAST_MAX_PRICE)"; MAXP="${MAXP:-0.60}"
BLENDER_VER="${BLENDER_VER:-$(envget BLENDER_VER)}"; BLENDER_VER="${BLENDER_VER:-5.2.3}"
STATE="$PROJ/.pf/gpu${PF_GPU_NAME:+-$PF_GPU_NAME}"; mkdir -p "$STATE"
VENV="$HOME/.cache/placeforge/vast-venv"
TEMPLATE="72a351f3d7a2eac98fd3af979c79fb03"  # Vast's "NVIDIA CUDA" template (vastai/base-image)
expand() { case "$1" in "~/"*) printf '%s' "$HOME/${1#\~/}";; *) printf '%s' "$1";; esac; }
if [ "$MODE" = ssh ]; then
  SSHKEY="$(expand "$(envget PF_SSH_KEY)")"; RUSER="$(envget PF_SSH_USER)"; RUSER="${RUSER:-root}"
else
  SSHKEY="$(expand "$(envget VAST_SSH_KEY)")"; SSHKEY="${SSHKEY:-$HOME/.ssh/placeforge_ed25519}"; RUSER=root
fi

key() { local k; k="$(envget VAST_API_KEY)"; [ -n "$k" ] || die "no VAST_API_KEY (add it to $PROJ/.env; get one at https://cloud.vast.ai/account/)"; printf '%s' "$k"; }
cli() {
  if [ ! -x "$VENV/bin/vastai" ]; then
    local py=""; for c in python3.13 python3.12 python3.11 python3.10 python3; do
      command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null && { py="$c"; break; }; done
    [ -n "$py" ] || die "the Vast CLI needs Python 3.10 or newer"
    { mkdir -p "$(dirname "$VENV")" && "$py" -m venv "$VENV" && "$VENV/bin/pip" install -q vastai; } >&2
  fi
  "$VENV/bin/vastai" "$@" --api-key "$(key)"
}
iid() { [ -s "$STATE/instance" ] && cat "$STATE/instance" || die "no machine rented (pf gpu up)"; }
target() { # sets HOST PORT
  if [ "$MODE" = ssh ]; then
    HOST="$(envget PF_SSH_HOST)"; PORT="$(envget PF_SSH_PORT)"; PORT="${PORT:-22}"
    [ -n "$HOST" ] || die "PF_COMPUTE=ssh needs PF_SSH_HOST in $PROJ/.env"; return
  fi
  local j; j=$(cli show instance "$(iid)" --raw 2>/dev/null)
  read -r HOST PORT < <(python3 -I -c '
import json,sys
d=json.loads(sys.stdin.read()); p=(d.get("ports") or {}).get("22/tcp")
if p and d.get("public_ipaddr"): print(d["public_ipaddr"].strip(), p[0]["HostPort"])
else: print(d.get("ssh_host",""), d.get("ssh_port",""))' <<<"$j")
  [ -n "$HOST" ] && [ -n "$PORT" ] || die "machine has no ssh address yet"
}
sshopts() { SSHO=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ServerAliveInterval=30); [ -n "$SSHKEY" ] && SSHO+=(-i "$SSHKEY"); return 0; }
sshopts
rsh() { target; ssh "${SSHO[@]}" -p "$PORT" "$RUSER@$HOST" "$@"; }
RSYNC=(rsync -az --partial --no-perms --no-owner --no-group --omit-dir-times --exclude '._*' --exclude '.DS_Store' --exclude '__pycache__')

install() {
  local f=blender-${BLENDER_VER}-linux-x64.tar.xz d=Blender${BLENDER_VER%.*} k
  local script="SUDO=; [ \"\$(id -u)\" = 0 ] || SUDO=sudo
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null || echo 'no NVIDIA GPU seen (CPU or another vendor)'
command -v rsync >/dev/null || (\$SUDO apt-get update -qq && \$SUDO apt-get install -y -qq rsync >/dev/null)
\$SUDO apt-get install -y -qq libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 libgl1 libegl1 libglu1-mesa xz-utils ffmpeg >/dev/null 2>&1 || true
if ! command -v blender >/dev/null; then
  for u in https://download.blender.org/release/$d/$f https://mirror.nju.edu.cn/blender/release/$d/$f https://mirrors.aliyun.com/blender/release/$d/$f; do
    curl -fsSL --speed-limit 2000000 --speed-time 15 \$u -o \$HOME/blender.tar.xz && break
  done
  \$SUDO rm -rf /opt/blender /opt/blender-${BLENDER_VER}-linux-x64 && \$SUDO tar -xJf \$HOME/blender.tar.xz -C /opt && \$SUDO mv /opt/blender-${BLENDER_VER}-linux-x64 /opt/blender && \$SUDO ln -sf /opt/blender/blender /usr/local/bin/blender
fi
blender --version | head -1
python3 -c 'import PIL' 2>/dev/null || pip install -q pillow >/dev/null 2>&1 || true
echo INSTALL DONE"
  for k in 1 2 3 4 5; do rsh "cat > \$HOME/pf-install.sh <<'XEOF'
$script
XEOF
nohup bash \$HOME/pf-install.sh > \$HOME/pf-install.log 2>&1 < /dev/null & echo started" 2>/dev/null && break; sleep 15; done
  for k in $(seq 1 80); do
    rsh "grep -q 'INSTALL DONE' \$HOME/pf-install.log" 2>/dev/null && { rsh "tail -2 \$HOME/pf-install.log" 2>/dev/null || true; return 0; }
    sleep 15
  done
  die "Blender install did not finish (pf gpu install to retry, pf gpu down to stop billing)"
}

cmd="${1:-status}"; shift || true
case "$cmd" in
status)
  if [ "$MODE" = ssh ]; then target; echo "ssh machine: $RUSER@$HOST:$PORT"; rsh "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null; blender --version 2>/dev/null | head -1" || echo "not reachable"; exit 0; fi
  cli show user --raw 2>/dev/null | python3 -I -c 'import json,sys;d=json.load(sys.stdin);print("credit: $%.2f" % d.get("credit",0))'
  cli show instances 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g'
  [ -s "$STATE/instance" ] && echo "this project's machine: $(cat "$STATE/instance") ($(cat "$STATE/offer" 2>/dev/null))" || echo "this project has no machine rented" ;;
offers)
  [ "$MODE" = vast ] || die "offers: only with PF_COMPUTE=vast"
  p="${1:-$MAXP}"
  cli search offers "num_gpus=1 dph_total<$p reliability>0.98 verified=true rentable=true inet_down>300 cpu_ram>=16 disk_space>=40 gpu_name in [RTX_5090,RTX_4090,RTX_3090,L40S]" -o dph_total 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | head -20 ;;
up)
  if [ "$MODE" = ssh ]; then echo "installing Blender $BLENDER_VER on the ssh machine"; install; exit 0; fi
  [ -s "$STATE/instance" ] && die "a machine is already rented: $(cat "$STATE/instance") (pf gpu down first)"
  if [ ! -f "$SSHKEY" ]; then mkdir -p "$(dirname "$SSHKEY")"; ssh-keygen -q -t ed25519 -N "" -C placeforge -f "$SSHKEY"; fi
  cli create ssh-key "$(cat "$SSHKEY.pub")" >/dev/null 2>&1 || true        # registers the key on the account (no-op if it is there)
  gpus="${*:-RTX_5090 RTX_4090}"; gl=$(echo $gpus | tr ' ' ',')
  bad=$(grep -E '^[0-9]+$' "$PROJ/.pf/bad-machines" 2>/dev/null | tr '\n' ',' | sed 's/,$//'); xq=""; [ -n "$bad" ] && xq=" machine_id notin [$bad]"
  ng="$(envget VAST_NOT_GEO)"; [ -n "$ng" ] && xq="$xq geolocation notin [$ng]"
  pick=$(cli search offers "num_gpus=1 dph_total<$MAXP reliability>0.98 verified=true rentable=true inet_down>300 cpu_ram>=16 disk_space>=40 gpu_name in [$gl]$xq" -o dph_total --raw 2>/dev/null | python3 -I -c '
import json,sys
d=json.load(sys.stdin)
if d: o=d[0]; print(o["id"], o["gpu_name"].replace(" ","_"), "%.3f" % o["dph_total"], o.get("geolocation","?").replace(" ","_"), o.get("machine_id",""))')
  [ -n "$pick" ] || die "no offer under \$$MAXP/h for: $gpus (raise VAST_MAX_PRICE in .env or name other GPUs)"
  read -r OID GPU PRICE GEO MID <<<"$pick"
  echo "renting offer $OID: 1x $GPU at \$$PRICE/h ($GEO)"
  out=$(cli create instance "$OID" --template_hash "$TEMPLATE" --ssh --direct --disk 32 --label placeforge --raw 2>/dev/null)
  id=$(python3 -I -c 'import json,sys;print(json.load(sys.stdin).get("new_contract",""))' <<<"$out")
  [ -n "$id" ] || die "create failed: $out"
  echo "$id" > "$STATE/instance"; echo "1x $GPU \$$PRICE/h $GEO" > "$STATE/offer"; date +%s > "$STATE/started"; echo "$MID" > "$STATE/machine"
  echo "instance $id: waiting for it to boot (billing has started)"
  st=""
  for i in $(seq 1 60); do
    st=$(cli show instance "$id" --raw 2>/dev/null | python3 -I -c 'import json,sys;print(json.load(sys.stdin).get("actual_status") or "")' || true)
    [ "$st" = running ] && break; sleep 10
  done
  [ "$st" = running ] || die "machine $id not running after 10 min (status: $st). Slow host: pf gpu down, then pf gpu up again (add its country to VAST_NOT_GEO)"
  for i in $(seq 1 30); do rsh true 2>/dev/null && break; sleep 10; done
  echo "installing Blender $BLENDER_VER"
  install
  echo "ready: instance $id, 1x $GPU at \$$PRICE/h. Destroy it when the frames are down: pf gpu down" ;;
push)
  [ $# -ge 2 ] || die "usage: push <local dir> <remote dir> [rsync args]"
  src="${1%/}/"; dst="$2"; shift 2; target
  rsh "mkdir -p $dst"
  "${RSYNC[@]}" "$@" -e "ssh ${SSHO[*]} -p $PORT" "$src" "$RUSER@$HOST:$dst/" ;;
pull)
  [ $# -ge 2 ] || die "usage: pull <remote dir> <local dir> [rsync args]"
  src="${1%/}/"; dst="$2"; shift 2; target; mkdir -p "$dst"
  "${RSYNC[@]}" "$@" -e "ssh ${SSHO[*]} -p $PORT" "$RUSER@$HOST:$src" "$dst/" ;;
install) install ;;
run)  rsh "cd \$HOME; $*" ;;
bg)   n="$1"; shift; rsh "cd \$HOME; nohup bash -c $(printf %q "$*") > \$HOME/$n.log 2>&1 < /dev/null & echo started $n" ;;
log)  rsh "tail -n ${2:-15} \$HOME/$1.log" ;;
ssh)  target; exec ssh "${SSHO[@]}" -p "$PORT" "$RUSER@$HOST" ;;
bad)  [ -s "$STATE/machine" ] && cat "$STATE/machine" >> "$PROJ/.pf/bad-machines" && echo "machine $(cat "$STATE/machine") will not be rented again" ;;
down)
  [ "$MODE" = ssh ] && { echo "ssh machine: nothing to destroy (it is yours; stop it wherever you rent it)"; exit 0; }
  id=$(iid); cli destroy instance "$id" -y >/dev/null 2>&1 || cli destroy instance "$id"
  s=$(cat "$STATE/started" 2>/dev/null || date +%s); echo "destroyed $id after $(( ( $(date +%s) - s ) / 60 )) min ($(cat "$STATE/offer" 2>/dev/null))"
  rm -f "$STATE/instance" "$STATE/offer" "$STATE/started" "$STATE/machine" ;;
*) sed -n '2,16p' "$0"; exit 1 ;;
esac
