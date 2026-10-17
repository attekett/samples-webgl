import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import calibrate_webgl_lifecycle as calibration


def _context():
    return {'version': 2, 'extensions': ['WEBGL_multi_draw'], 'renderer': 'ANGLE Vulkan',
            'vendor': 'Google Inc.', 'renderer_verified': True}


def _lane(binary):
    identity = calibration.executable_identity(binary)
    return {'browser': 'chromium', 'renderer': ['ANGLE Vulkan'], 'contexts': [_context()],
            'browser_identity': {'browser_name': 'chromium', 'browser_version': '155.0',
                                 'executable': identity, 'launch_flags': ['--use-angle=vulkan']}}


def test_injected_page_keeps_original_hash_and_records_completion_separately():
    original = b'<!doctype html><html><head><script>window.__done = true</script></head></html>'
    source_hash = hashlib.sha256(original).hexdigest()
    injected = calibration.inject(original.decode()).replace('__SAMPLE__', '0').encode()
    item = {'path': '/controls/valid.html', 'source_sha256': source_hash,
            'output_sha256': hashlib.sha256(injected).hexdigest(), 'sample_index': 0}
    record = calibration.make_record(item, {'done': True, 'contexts': [_context()]}, 0.25, True)
    assert record['source_sha256'] == source_hash
    assert record['output_sha256'] == source_hash
    assert record['injected_testcase_sha256'] == item['output_sha256']
    assert record['injected_testcase_sha256'] != source_hash
    assert record['completed'] is True
    assert record['duration_s'] == 0.25


def test_lane_verification_accepts_matching_executable_and_context(tmp_path):
    binary = tmp_path / 'browser'
    binary.write_bytes(b'local test executable')
    lane = _lane(binary)
    verified, checks = calibration.verify_lane(lane, 'chromium', binary, [_context()],
                                                ['/bin/browser', '--use-angle=vulkan'],
                                                '155.0.8059.79', [True, True])
    assert verified is True
    assert checks['executable_match'] is True
    assert checks['context_match'] is True
    assert checks['launch_flags_observed'] is True


def test_firefox_launch_hook_forwards_requested_flags_and_restores_class():
    class FakeFirefox:
        def build_launch_cmd(self, binary, profile_path=None, debugger_args=(), display_args=(), additional_args=None):
            return [binary, '-new-instance', *display_args]

    original = FakeFirefox.build_launch_cmd
    restore = calibration.patch_firefox_launch_flags(FakeFirefox, ['--new-instance', '--no-remote'])
    try:
        command = FakeFirefox().build_launch_cmd('/firefox', display_args=['-headless'])
        assert command == ['/firefox', '-new-instance', '-headless', '--new-instance', '--no-remote']
    finally:
        restore()
    assert FakeFirefox.build_launch_cmd is original


@pytest.mark.parametrize('change,failed_check', [
    ('browser', 'browser_match'),
    ('executable', 'executable_match'),
    ('capability', 'context_match'),
    ('renderer', 'context_match'),
    ('launch_flag', 'launch_flags_observed'),
    ('version', 'version_match'),
    ('completion', 'all_completed'),
])
def test_lane_verification_rejects_identity_or_observation_mismatches(tmp_path, change, failed_check):
    binary = tmp_path / 'browser'
    binary.write_bytes(b'local test executable')
    lane = _lane(binary)
    browser, observed, command, version, completed = 'chromium', [_context()], ['/bin/browser', '--use-angle=vulkan'], '155.0', [True]
    if change == 'browser':
        browser = 'firefox'
    elif change == 'executable':
        other = tmp_path / 'other-browser'
        other.write_bytes(b'different executable')
        lane['browser_identity']['executable'] = calibration.executable_identity(other)
    elif change == 'capability':
        observed = [{**_context(), 'extensions': []}]
    elif change == 'renderer':
        observed = [{**_context(), 'renderer': 'ANGLE OpenGL'}]
    elif change == 'launch_flag':
        command = ['/bin/browser']
    elif change == 'version':
        version = '154.0'
    elif change == 'completion':
        completed = [False]
    verified, checks = calibration.verify_lane(lane, browser, binary, observed, command, version, completed)
    assert verified is False
    assert checks[failed_check] is False
