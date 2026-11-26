"""Auto-generate a voiceover for an ai-content-creator project.

python auto_voice.py <project_dir> [--provider auto|elevenlabs|kokoro] [--preview N]

Reads work/script_full.txt and work/voices.json. Narration uses the narrator voice;
quoted dialogue is split out and spoken by a mapped character voice. Writes
work/voice_segments.json, work/preview_voice.mp3 (preview) or voice.mp3 + work/voice_duration.json.
ElevenLabs is used only when ELEVENLABS_API_KEY is set; otherwise Kokoro (offline) is used.
"""
import argparse, json, os, re, shutil, subprocess, sys, urllib.request
from pathlib import Path

QUOTE = re.compile(r'["\u201c]([^"\u201d]+)["\u201d]')
PRON = re.compile(r'\b(he|she|I)\b', re.I)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def segments_from_script(path, cfg):
    """Return [(text, speaker, emotions, line_no)] in spoken order."""
    pron = cfg.get('pronouns', {})
    out = []
    for lineno, raw in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith('[[['):
            continue
        emotions = []
        while s.startswith('['):
            end = s.find(']')
            if end < 0:
                break
            emotions.append(s[1:end].strip())
            s = s[end + 1:].strip()
        parts, pos = [], 0
        for m in QUOTE.finditer(s):
            if m.start() > pos:
                parts.append((s[pos:m.start()], None))
            left, right = s[max(0, m.start() - 120):m.start()], s[m.end():m.end() + 40]
            speaker = None
            rm = PRON.search(right)
            lm = list(PRON.finditer(left))
            if rm and rm.group(1).lower() in pron:
                speaker = pron[rm.group(1).lower()]
            elif lm and lm[-1].group(1).lower() in pron:
                speaker = pron[lm[-1].group(1).lower()]
            parts.append((m.group(1), speaker))
            pos = m.end()
        if pos < len(s):
            parts.append((s[pos:], None))
        for text, speaker in parts:
            text = text.strip().strip(',')
            if text:
                out.append((text, speaker or 'narrator', emotions, lineno))
    return out


def voice_for(cfg, speaker, provider):
    if speaker == 'narrator':
        row = cfg.get('narrator', {})
    else:
        row = cfg.get('characters', {}).get(speaker, cfg.get('narrator', {}))
    value = row.get('elevenlabs', '') if provider == 'elevenlabs' else row.get('kokoro', 'af_bella')
    if value.startswith('ENV:'):
        return os.environ.get(value[4:])
    return value or None


def choose_provider(wanted, cfg, segments):
    key = os.environ.get('ELEVENLABS_API_KEY')
    if wanted == 'auto':
        provider = 'elevenlabs' if key else 'kokoro'
    else:
        provider = wanted
    if provider == 'elevenlabs' and not key:
        print('auto_voice: no ELEVENLABS_API_KEY; falling back to offline Kokoro.', file=sys.stderr)
        provider = 'kokoro'
    if provider == 'elevenlabs':
        missing = sorted({sp for _, sp, _, _ in segments if not voice_for(cfg, sp, provider)})
        if missing:
            print('auto_voice: missing ElevenLabs voice id for ' + ', '.join(missing) + '; using Kokoro.', file=sys.stderr)
            provider = 'kokoro'
    return provider


def python_for(lib):
    for candidate in (lib / '.venv' / 'Scripts' / 'python.exe', lib / '.venv' / 'bin' / 'python'):
        if candidate.exists():
            return str(candidate)
    return shutil.which('python') or 'python'


def generate_elevenlabs(segments, cfg, work, dest):
    key = os.environ['ELEVENLABS_API_KEY']
    for i, (text, speaker, emotions, _) in enumerate(segments, 1):
        vid = voice_for(cfg, speaker, 'elevenlabs')
        tagged = ''.join('[%s] ' % e for e in emotions) + text
        body = json.dumps({'text': tagged, 'model_id': 'eleven_turbo_v2_5',
                           'output_format': 'mp3_44100_128'}).encode('utf-8')
        req = urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/' + vid, body,
                                     {'xi-api-key': key, 'Content-Type': 'application/json',
                                      'Accept': 'audio/mpeg'})
        with urllib.request.urlopen(req, timeout=180) as response:
            dest[i].write_bytes(response.read())
        print('elevenlabs', i, speaker, tagged)


def generate_kokoro(segments, cfg, work, dest):
    lib = Path(os.environ.get('LEMO_OPUSCAR_HOME') or Path.home() / 'lemo-opuscar')
    payload = []
    for i, (text, speaker, _, _) in enumerate(segments, 1):
        row = cfg['narrator'] if speaker == 'narrator' else cfg.get('characters', {}).get(speaker, cfg['narrator'])
        payload.append({'id': 'l%02d' % i, 'text': text, 'voice': row.get('kokoro', 'af_bella'),
                        'speed': row.get('speed', 0.92), 'lang': 'en-us'})
    lines_json = work / 'tts_lines.json'
    lines_json.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    raw = work / 'tts_raw'
    subprocess.run([python_for(lib), str(lib / 'core' / 'tts' / 'tts.py'), str(lines_json), str(raw)], check=True)
    for i in range(1, len(segments) + 1):
        dest[i] = raw / ('l%02d.wav' % i)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def assemble(clips, gaps, out_wav):
    """clips: dict index->Path, gaps: dict index->seconds before that clip."""
    norm = out_wav.parent / 'norm'
    norm.mkdir(exist_ok=True)
    silence_short, silence_long = norm / 'gap_short.wav', norm / 'gap_long.wav'
    for target, seconds in ((silence_short, 0.06), (silence_long, 0.18)):
        run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono',
             '-t', str(seconds), str(target)])
    ordered = []
    for index in sorted(clips):
        if index > 1:
            ordered.append(silence_short if gaps.get(index, 0.18) < 0.1 else silence_long)
        target = norm / ('n%03d.wav' % index)
        run(['ffmpeg', '-y', '-i', str(clips[index]), '-ar', '44100', '-ac', '1',
             '-c:a', 'pcm_s16le', str(target)])
        ordered.append(target)
    listfile = norm / 'concat.txt'
    listfile.write_text(''.join("file '%s'\n" % p.as_posix().replace("'", "'\\''") for p in ordered),
                        encoding='utf-8')
    run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(listfile),
         '-c:a', 'pcm_s16le', str(out_wav)])


def duration_of(path):
    text = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                    '-of', 'default=nw=1:nk=1', str(path)], text=True)
    return round(float(text.strip()), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--provider', choices=['auto', 'elevenlabs', 'kokoro'], default='auto')
    ap.add_argument('--preview', type=int, default=0, help='first N script lines only')
    args = ap.parse_args()
    project, work = Path(args.project), Path(args.project) / 'work'
    cfg = load(work / 'voices.json')
    segments = segments_from_script(work / 'script_full.txt', cfg)
    if args.preview:
        segments = segments[:args.preview]
    if not segments:
        sys.exit('auto_voice: no spoken lines found in script_full.txt')
    provider = choose_provider(args.provider, cfg, segments)
    clips, gaps = {}, {}
    last_line = None
    for i, (_, _, _, lineno) in enumerate(segments, 1):
        gaps[i] = 0.06 if lineno == last_line else 0.18
        last_line = lineno
    if provider == 'elevenlabs':
        generate_elevenlabs(segments, cfg, work, clips)
    else:
        generate_kokoro(segments, cfg, work, clips)
    manifest = [{'id': i, 'text': s[0], 'speaker': s[1], 'emotion': s[2], 'line': s[3],
                 'provider': provider} for i, s in enumerate(segments, 1)]
    (work / 'voice_segments.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                              encoding='utf-8')
    wav = work / ('preview_voice.wav' if args.preview else 'voice.wav')
    assemble(clips, gaps, wav)
    mp3 = work / ('preview_voice.mp3' if args.preview else 'voice.mp3')
    run(['ffmpeg', '-y', '-i', str(wav), '-c:a', 'libmp3lame', '-b:a', '192k', str(mp3)])
    secs = duration_of(mp3)
    if not args.preview:
        (work / 'voice_duration.json').write_text(json.dumps({'seconds': secs, 'provider': provider},
                                                             indent=1), encoding='utf-8')
        shutil.copyfile(mp3, project / 'voice.mp3')
        shutil.copyfile(wav, project / 'voice.wav')
    print('auto_voice: %s, %d segments, %.2f s -> %s' % (provider, len(segments), secs, mp3))


if __name__ == '__main__':
    main()
