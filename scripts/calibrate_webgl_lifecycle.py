#!/usr/bin/env python3
"""Measure unmodified valid WebGL controls through the local Grizzly lifecycle."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import parse_qs


def sha(data):
    return hashlib.sha256(data).hexdigest()


def html_files(manifest):
    path = Path(manifest).resolve()
    files = [path] if path.is_file() else sorted(path.rglob('*.html'))
    return [p.resolve() for p in files if p.is_file() and p.suffix.lower() == '.html']


def load_ledger(path, browser):
    if not path:
        return None
    data = json.loads(Path(path).read_text())
    lane = data.get('lane', {})
    if lane.get('browser') != browser:
        raise ValueError(f"profile ledger browser {lane.get('browser')!r} does not match {browser!r}")
    identity = lane.get('browser_identity')
    if not isinstance(identity, dict):
        raise ValueError('profile ledger has no browser_identity')
    return data


def inject(source):
    instrumentation = r'''<script>(()=>{
const contexts=[]; const seen=new WeakSet();
const observe=(gl,type)=>{if(!gl||seen.has(gl)||!/^webgl(?:2)?$|^experimental-webgl$/.test(String(type)))return gl;seen.add(gl);contexts.push(()=>{
 let version=null,extensions=[],renderer=null,vendor=null,renderer_verified=false;
 try{const v=String(gl.getParameter(gl.VERSION)||'');version=/WebGL\s*2/.test(v)?2:/WebGL\s*1/.test(v)?1:null;extensions=gl.getSupportedExtensions()||[]}catch(e){}
 try{const info=/Firefox\//.test(navigator.userAgent||'')?null:gl.getExtension('WEBGL_debug_renderer_info');if(info){renderer=gl.getParameter(info.UNMASKED_RENDERER_WEBGL);vendor=gl.getParameter(info.UNMASKED_VENDOR_WEBGL);renderer_verified=!!renderer}}catch(e){}
 if(!renderer){try{renderer=gl.getParameter(gl.RENDERER);vendor=gl.getParameter(gl.VENDOR)}catch(e){}}
 return {version,extensions,renderer,vendor,renderer_verified};
});return gl};
for(const C of [window.HTMLCanvasElement,window.OffscreenCanvas].filter(Boolean)){const p=C.prototype,k='getContext',original=p[k];if(original)p[k]=function(type,...args){return observe(original.call(this,type,...args),type)}}
let done=false;Object.defineProperty(window,'__done',{configurable:true,get:()=>done,set:value=>{if(value!==true){done=value;return}done=true;if(window.__calibrationSent)return;window.__calibrationSent=true;
 const payload={done:true,contexts:contexts.map(f=>f())};
 fetch('/grzcalibration?sample=__SAMPLE__&payload='+encodeURIComponent(JSON.stringify(payload)),{cache:'no-store'}).catch(()=>{}).finally(()=>window.close());
}});
})();</script>'''
    def add(match):
        return match.group(0) + instrumentation
    if re.search(r'<head\b[^>]*>', source, re.I):
        return re.sub(r'<head\b[^>]*>', add, source, count=1, flags=re.I)
    if re.search(r'<html\b[^>]*>', source, re.I):
        return re.sub(r'<html\b[^>]*>', add, source, count=1, flags=re.I)
    return instrumentation + source


def pref_text(preferences):
    lines = []
    for key, value in preferences.items():
        lines.append(f"user_pref({json.dumps(key)}, {json.dumps(value, ensure_ascii=False)});")
    return '\n'.join(lines) + '\n'


def patch_firefox_launch_flags(browser_class, requested_flags):
    """Temporarily append profile-lane flags to browserpuppet's Firefox command."""
    original = browser_class.build_launch_cmd

    def build_with_flags(self, *args, **kwargs):
        command = original(self, *args, **kwargs)
        for flag in requested_flags:
            if flag not in command:
                command.append(flag)
        return command

    browser_class.build_launch_cmd = build_with_flags

    def restore():
        browser_class.build_launch_cmd = original

    return restore


def executable_identity(path):
    resolved = Path(path).resolve(strict=True)
    stat = resolved.stat()
    return {'path': str(resolved), 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def profile_identity_args(ledger, binary, browser):
    if not ledger:
        return [], {}, None
    identity = ledger['lane']['browser_identity']
    expected_exec = identity.get('executable', {})
    actual_exec = executable_identity(binary)
    expected_path = expected_exec.get('path')
    if expected_path and str(Path(expected_path).resolve()) != actual_exec['path']:
        raise ValueError(f"binary path differs from profile ledger: {actual_exec['path']} != {expected_path}")
    for key in ('size', 'mtime_ns'):
        if expected_exec.get(key) is not None and expected_exec[key] != actual_exec[key]:
            raise ValueError(f"binary {key} differs from profile ledger")
    launch_flags = identity.get('launch_flags', [])
    preferences = identity.get('preferences', {}) if browser == 'firefox' else {}
    if not isinstance(launch_flags, list) or not isinstance(preferences, dict):
        raise ValueError('profile lane launch flags/preferences have an unsupported shape')
    return launch_flags, preferences, identity


def browser_version(binary, browser):
    try:
        result = subprocess.run([binary, '--version'], capture_output=True, text=True, timeout=10)
        text = (result.stdout + '\n' + result.stderr).strip()
        pattern = r'(?:Google Chrome|Chromium|Firefox)\s+(\d+(?:\.\d+)+)'
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
        matches = re.findall(r'\d+(?:\.\d+)+', result.stdout)
        return matches[-1] if matches else text
    except Exception as exc:
        return f'unavailable:{type(exc).__name__}'


def compare_contexts(observed, lane):
    expected_contexts = lane.get('contexts', [])
    def normalize(rows):
        unique = {}
        for row in rows:
            context = {'version': row.get('version'), 'extensions': sorted(row.get('extensions') or []),
                       'renderer': row.get('renderer'), 'vendor': row.get('vendor'),
                       'renderer_verified': row.get('renderer_verified')}
            unique[json.dumps(context, sort_keys=True)] = context
        return [unique[key] for key in sorted(unique)]
    actual = normalize(observed)
    expected = normalize(expected_contexts)
    if actual != expected:
        return False, {'expected_contexts': expected, 'observed_contexts': actual}
    renderer = sorted({str(row.get('renderer', '')) for row in actual})
    if renderer != lane.get('renderer', []):
        return False, {'expected_renderer': lane.get('renderer'), 'observed_renderer': renderer}
    return True, {'contexts': actual, 'renderer': renderer}


def verify_lane(lane, browser, binary, observed_contexts, command_line, browser_version_value, completed):
    """Verify executable, requested flags, version and seed-context capability evidence."""
    identity = lane.get('browser_identity', {})
    try:
        actual_executable = executable_identity(binary)
        expected_executable = identity.get('executable', {})
        executable_ok = (str(Path(expected_executable.get('path', '')).resolve()) == actual_executable['path'] and
                         all(expected_executable.get(key) is None or expected_executable[key] == actual_executable[key]
                             for key in ('size', 'mtime_ns')))
    except (OSError, TypeError, ValueError):
        actual_executable, executable_ok = None, False
    flags = identity.get('launch_flags', [])
    flags_ok = isinstance(flags, list) and all(flag in (command_line or []) for flag in flags)
    expected_version = identity.get('browser_version')
    version_ok = (expected_version is None or expected_version in browser_version_value or
                  browser_version_value in str(expected_version))
    context_ok, context_check = compare_contexts(observed_contexts, lane)
    checks = {'browser_match': lane.get('browser') == browser,
              'executable_match': executable_ok, 'executable': actual_executable,
              'version_match': version_ok, 'launch_flags_observed': flags_ok,
              'context_match': context_ok, 'context_check': context_check,
              'all_completed': bool(completed) and all(completed)}
    return all((checks['browser_match'], executable_ok, version_ok, flags_ok,
                context_ok, checks['all_completed'])), checks


def make_record(item, payload, duration_s, served):
    """Pair a fixed source hash with its injected-page hash and Grizzly duration."""
    return {'source_path': item['path'], 'source_sha256': item['source_sha256'],
            'output_sha256': item['source_sha256'],
            'injected_testcase_sha256': item.get('output_sha256'),
            'duration_s': duration_s, 'duration_ms': round(duration_s * 1000, 3)
            if duration_s is not None else None,
            'completed': bool(payload and payload.get('done') is True),
            'contexts': payload.get('contexts') if payload else None,
            'served_entry_point': bool(served), 'sample_index': item['sample_index']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, help='directory or single HTML control')
    parser.add_argument('--binary', required=True, help='exact browser executable')
    parser.add_argument('--browser', required=True, choices=('firefox', 'chromium'))
    parser.add_argument('--output', required=True, help='calibration JSON destination')
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--profile-ledger', help='profile_ledger.json used to verify exact lane')
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('--rounds must be positive')
    files = html_files(args.manifest)
    if not files:
        parser.error('manifest contains no HTML controls')
    if not Path(args.binary).is_file():
        parser.error(f'browser executable does not exist: {args.binary}')
    ledger = load_ledger(args.profile_ledger, args.browser)
    flags, preferences, expected_identity = profile_identity_args(ledger, args.binary, args.browser)
    samples = [{'path': str(path), 'source_bytes': path.read_bytes(), 'source_sha256': sha(path.read_bytes())}
               for _ in range(args.rounds) for path in files]
    captured = {}
    records = []
    effective_command_line = None
    tempdir = tempfile.mkdtemp(prefix='periwinkle-grizzly-calibration-')
    prefs_path = Path(tempdir) / 'prefs.js'
    if args.browser == 'firefox' and preferences:
        prefs_path.write_text(pref_text(preferences))

    from grizzly.adapter.no_op_adapter import NoOpAdapter
    from grizzly.args import GrizzlyArgs
    import grizzly.main as grizzly_main

    class CalibrationAdapter(NoOpAdapter):
        def __init__(self, name):
            super().__init__(name)
            self.index = 0
            self.remaining = len(samples)

        def setup(self, input_path, server_map):
            self.enable_harness()
            def receive(query):
                params = parse_qs(query)
                try:
                    idx = int(params.get('sample', ['-1'])[0])
                    payload = json.loads(params.get('payload', ['{}'])[0])
                    captured[idx] = payload
                except Exception as exc:
                    captured[-1] = {'capture_error': str(exc)}
                return b'ok'
            server_map.set_dynamic_response('grzcalibration', receive, mime_type='application/json')

        def generate(self, testcase, server_map):
            idx = self.index
            if idx >= len(samples):
                raise RuntimeError('Grizzly requested more samples than configured')
            self.index += 1
            item = samples[idx]
            original = item['source_bytes'].decode('utf-8')
            transformed = inject(original).replace('__SAMPLE__', str(idx))
            item['output_sha256'] = sha(transformed.encode('utf-8'))
            item['sample_index'] = idx
            testcase.add_from_bytes(transformed.encode('utf-8'), testcase.entry_point, required=True)

        def on_served(self, testcase, served):
            nonlocal effective_command_line
            try:
                tree = self.monitor._puppet._proc_tree
                for process in tree.processes(recursive=True):
                    command = process.cmdline()
                    if command and Path(command[0]).resolve() == Path(args.binary).resolve():
                        effective_command_line = command
                        break
            except Exception:
                pass
            idx = len(records)
            item = samples[idx]
            payload = captured.get(idx)
            records.append(make_record(item, payload, testcase.duration,
                                       testcase.entry_point in set(served)))
            self.remaining = max(0, len(samples) - len(records))

    old_load = grizzly_main.load_plugin
    def patched_load(name, group, parent):
        if group == 'grizzly_adapters' and name == 'no-op':
            return CalibrationAdapter
        return old_load(name, group, parent)
    grizzly_main.load_plugin = patched_load

    argv = [str(Path(args.binary).resolve()), 'no-op', '--platform', args.browser,
            '--limit', str(len(samples)), '--relaunch', str(len(samples) + 1), '--timeout', '90',
            '--time-limit', '60', '--launch-timeout', '30', '--log-level', 'ERROR',
            '--output', tempdir]
    if expected_identity and expected_identity.get('headless'):
        argv.extend(['--display', 'headless'])
    for flag in flags:
        argv.append('--browser-flag=' + str(flag))
    if args.browser == 'firefox' and preferences:
        argv.extend(['--asset', 'prefs', str(prefs_path)])
    grizzly_args = GrizzlyArgs().parse_args(argv)
    started = time.perf_counter()
    restore_firefox_flags = None
    if args.browser == 'firefox' and flags:
        from browserpuppet.browser.firefox import FirefoxBrowser
        restore_firefox_flags = patch_firefox_launch_flags(FirefoxBrowser, flags)
    try:
        exit_code = grizzly_main.main(grizzly_args)
    finally:
        grizzly_main.load_plugin = old_load
        if restore_firefox_flags:
            restore_firefox_flags()
    elapsed = time.perf_counter() - started
    for idx in range(len(records), len(samples)):
        item = samples[idx]
        records.append({'source_path': item['path'], 'source_sha256': item['source_sha256'],
                        'output_sha256': item['source_sha256'],
                        'injected_testcase_sha256': item.get('output_sha256'), 'duration_s': None,
                        'duration_ms': None, 'completed': False, 'contexts': None,
                        'served_entry_point': False, 'sample_index': idx})
    observed_contexts = [context for row in records for context in (row.get('contexts') or [])]
    lane = None
    lane_verified = False
    verification = {'binary': executable_identity(args.binary),
                    'binary_version': browser_version(args.binary, args.browser),
                    'grizzly_exit_code': exit_code, 'elapsed_s': elapsed}
    if ledger:
        lane = ledger['lane']
        identity_matches = expected_identity == lane['browser_identity']
        lane_verified, lane_checks = verify_lane(lane, args.browser, args.binary,
                                                  observed_contexts, effective_command_line,
                                                  verification['binary_version'],
                                                  [row['completed'] for row in records])
        lane_verified = lane_verified and identity_matches
        verification.update(lane_checks,
                            profile_identity_copied=identity_matches,
                            lane_verified=lane_verified)
    verification['native_setup'] = {
        'binary': str(Path(args.binary).resolve()),
        'binary_identity': verification['binary'],
        'browser': args.browser,
        'profile_launch_flags': flags,
        'profile_preferences': preferences,
        'display_mode': 'headless' if expected_identity and expected_identity.get('headless') else 'default',
        'effective_browser_command_line': effective_command_line,
        'effective_command_line_captured': effective_command_line is not None,
    }
    output = {'schema_version': 1, 'kind': 'grizzly_calibration',
              'lane': lane if lane_verified else None, 'lane_verified': lane_verified,
              'verification': verification, 'records': records}
    Path(args.output).resolve().parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    shutil.rmtree(tempdir, ignore_errors=True)
    print(args.output)
    return 0 if exit_code == 0 and all(row['duration_s'] is not None for row in records) else 1

if __name__ == '__main__':
    raise SystemExit(main())
