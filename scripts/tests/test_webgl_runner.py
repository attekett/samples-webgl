import asyncio
import time

from webgl_test_runner import TestResult as Result, WebGPUTestRunner


def test_warnings_and_context_loss_fail():
    result = Result('seed.html', 'chromium')
    result.add_console_log('warning', 'WebGL context lost')
    result.finish()
    assert not result.passed

    class Page:
        async def evaluate(self, _):
            return {'hasCanvas': True, 'contextLost': True, 'completed': False, 'errorMessages': []}

    result = Result('seed.html', 'chromium')
    runner = WebGPUTestRunner(capture_screenshots=False)
    asyncio.run(runner._check_test_completion(Page(), result))
    assert [error['message'] for error in result.errors + result.webgl_errors] == [
        'Test did not finish', 'WebGL context lost'
    ]
    assert result.to_dict()['completed'] is False


def test_missing_completion_is_recorded():
    class Page:
        async def evaluate(self, _):
            return {'hasCanvas': True, 'contextLost': False, 'completed': None, 'errorMessages': []}

    result = Result('seed.html', 'chromium')
    asyncio.run(WebGPUTestRunner(capture_screenshots=False)._check_test_completion(Page(), result))
    assert result.to_dict()['completed'] is None


def test_validation_error_is_recorded_separately():
    class Page:
        async def evaluate(self, _):
            return {'hasCanvas': True, 'contextLost': False, 'completed': True,
                    'validationError': 1281, 'errorMessages': []}

    result = Result('seed.html', 'chromium')
    asyncio.run(WebGPUTestRunner(capture_screenshots=False)._check_test_completion(Page(), result))
    assert result.to_dict()['validation_error'] == 1281
    assert result.webgl_errors == []


def test_absolute_test_directory_discovers_usable_paths(tmp_path):
    case = tmp_path / 'case.html'
    case.write_text('<canvas></canvas>')
    runner = WebGPUTestRunner(test_dir=str(tmp_path), capture_screenshots=False)
    assert runner.discover_tests() == [str(case)]


def test_profile_is_opt_in_and_requires_a_positive_event_cap():
    assert 'webgl_profile' not in Result('seed.html', 'chromium').to_dict()
    assert WebGPUTestRunner(profile_webgl=True, profile_event_cap=17).profile_event_cap == 17
    try:
        WebGPUTestRunner(profile_webgl=True, profile_event_cap=0)
    except ValueError as error:
        assert 'positive' in str(error)
    else:
        raise AssertionError('zero event cap must be rejected')


def test_profile_identity_changes_with_launch_configuration():
    class Browser:
        version = 'test-version'

    class Context:
        browser = Browser()

    runner = WebGPUTestRunner(profile_webgl=True, profile_event_cap=17)
    runner._remember_launch('chromium', '/usr/bin/python3', ['--use-angle=vulkan'], {})
    first = runner.get_profile_identity('chromium', Context())
    runner._remember_launch('chromium', '/usr/bin/python3', ['--use-angle=gl'], {})
    second = runner.get_profile_identity('chromium', Context())
    assert first['executable']['path'].startswith('/usr/bin/python3')
    assert first['profiler_version'] == 'webgl-trace-2'
    assert first['fingerprint'] != second['fingerprint']
    runner._remember_launch('firefox', '/usr/bin/python3', [], {'webgl.force-enabled': True})
    firefox = runner.get_profile_identity('firefox', Context())
    assert firefox['preferences']['webgl.force-enabled'] is True


def test_profile_outcomes_keep_an_explicit_overflow_marker():
    runner = WebGPUTestRunner(profile_webgl=True)
    profile = {'outcome_cap': 3, 'outcomes': []}
    for code in ['one', 'two', 'three', 'four']:
        runner._append_profile_outcome(profile, {'code': code})
    assert len(profile['outcomes']) == 3
    assert profile['outcomes'][-1] == {'code': 'outcome_buffer_full'}


def test_profile_navigation_failure_retains_lane_identity_and_outcome(tmp_path):
    class Browser:
        version = 'test-browser-version'

    class Page:
        def __init__(self):
            self.handlers = {}

        async def add_init_script(self, _):
            return None

        def on(self, event, callback):
            self.handlers[event] = callback

        async def goto(self, *_args, **_kwargs):
            raise TimeoutError('navigation timed out')

        async def evaluate(self, _):
            await asyncio.Future()

        async def close(self):
            return None

    class Context:
        browser = Browser()

        async def new_page(self):
            return Page()

    runner = WebGPUTestRunner(profile_webgl=True, capture_screenshots=False, timeout=20)
    runner._remember_launch('chromium', '/usr/bin/python3', ['--use-angle=vulkan'], {})
    before = time.perf_counter()
    result = asyncio.run(runner.run_test(str(tmp_path / 'control.html'), 'chromium', Context()))
    elapsed = time.perf_counter() - before
    profile = result.webgl_profile
    assert result.passed is False
    assert profile['identity']['browser_name'] == 'chromium'
    assert profile['identity']['launch_flags'] == ['--use-angle=vulkan']
    assert profile['contexts'] == []
    assert profile['events'] == []
    assert any(outcome['code'] == 'navigation_failed' for outcome in profile['outcomes'])
    assert profile['timing']['navigation_elapsed_ms'] >= 0
    assert elapsed < 0.5


def _run_profile_after_trace_failure(tmp_path, failure_stage):
    class Browser:
        version = 'test-browser-version'

    class Page:
        def __init__(self):
            self.trace = {'schema_version': 1, 'profiler_version': 'webgl-trace-2',
                          'outcome_cap': 2048, 'contexts': [{'id': 'c1', 'version': 2}],
                          'events': [{'seq': 1, 'context': 'c1', 'method': 'drawArrays'}],
                          'truncated': False, 'outcomes': []}

        async def add_init_script(self, _):
            return None

        def on(self, _event, _callback):
            return None

        async def goto(self, *_args, **_kwargs):
            return None

        async def wait_for_function(self, *_args, **_kwargs):
            return None

        async def evaluate(self, source):
            if '__webglProfiler' in source:
                return self.trace
            if 'webglContextLost' in source:
                return False
            if 'navigator.userAgent' in source:
                if failure_stage == 'browser_info':
                    raise TimeoutError('browser info evaluation timed out')
                return {'userAgent': 'fake', 'webglSupported': True, 'vendor': 'fake',
                        'platform': 'fake', 'language': 'en'}
            if 'const canvas' in source:
                return {'supported': True}
            return {'hasCanvas': True, 'contextLost': False, 'completed': True, 'errorMessages': []}

        async def close(self):
            if failure_stage == 'page_close':
                raise TimeoutError('page close timed out')

    class Context:
        browser = Browser()

        async def new_page(self):
            return Page()

    runner = WebGPUTestRunner(profile_webgl=True, capture_screenshots=False, timeout=1000)
    runner._remember_launch('chromium', '/usr/bin/python3', ['--use-angle=vulkan'], {})
    return asyncio.run(runner.run_test(str(tmp_path / 'control.html'), 'chromium', Context()))


def test_profile_post_trace_failure_appends_outcome_and_preserves_trace(tmp_path):
    result = _run_profile_after_trace_failure(tmp_path, 'browser_info')
    assert result.passed is False
    assert result.webgl_profile['contexts'] == [{'id': 'c1', 'version': 2}]
    assert result.webgl_profile['events'] == [{'seq': 1, 'context': 'c1', 'method': 'drawArrays'}]
    assert result.webgl_profile['identity']['browser_name'] == 'chromium'
    assert any(outcome['code'] == 'runner_error' for outcome in result.webgl_profile['outcomes'])


def test_profile_page_close_failure_appends_outcome_and_preserves_trace(tmp_path):
    result = _run_profile_after_trace_failure(tmp_path, 'page_close')
    assert result.passed is False
    assert result.webgl_profile['events'][0]['method'] == 'drawArrays'
    assert result.webgl_profile['identity']['browser_name'] == 'chromium'
    assert any(outcome['code'] == 'runner_error' for outcome in result.webgl_profile['outcomes'])
