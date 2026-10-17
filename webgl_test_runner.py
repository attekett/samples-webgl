#!/usr/bin/env python3
"""
WebGL Test Runner using Playwright
===================================

A comprehensive test runner for WebGL/WebGL2 test cases that uses Playwright to run tests
in real browsers and capture detailed error information.

Features:
- Run tests in Chrome, Firefox, and Edge
- Capture JavaScript errors, WebGL errors, and console output
- Generate detailed HTML and JSON reports
- Support for batch testing and individual test execution
- Browser-specific feature detection and compatibility reporting
- Parallel test execution with configurable worker count

Requirements:
    pip install playwright beautifulsoup4
    playwright install
"""

import asyncio
import json
import os
import sys
import subprocess
import shutil
import tempfile
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import logging
import hashlib

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright && playwright install")
    sys.exit(1)

# Suppress asyncio subprocess cleanup warnings
warnings.filterwarnings("ignore", message=".*BaseSubprocessTransport.*")
warnings.filterwarnings("ignore", message=".*Event loop is closed.*")

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Warning: beautifulsoup4 not installed. HTML parsing may be limited.")
    BeautifulSoup = None


class TestResult:
    """Represents the result of running a single test case."""
    
    def __init__(self, test_path: str, browser_name: str):
        self.test_path = test_path
        self.browser_name = browser_name
        self.start_time = datetime.now()
        self.end_time = None
        self.duration_ms = 0
        self.passed = False
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.console_logs: List[Dict[str, Any]] = []
        self.webgl_errors: List[Dict[str, Any]] = []
        self.javascript_errors: List[Dict[str, Any]] = []
        self.network_errors: List[Dict[str, Any]] = []
        self.browser_info = {}
        self.completed: Optional[bool] = None
        self.validation_error: Optional[int] = None
        self.screenshot_path: Optional[str] = None
        self.webgl_profile: Optional[Dict[str, Any]] = None
        
    def finish(self, passed: bool = None):
        """Mark the test as finished."""
        self.end_time = datetime.now()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        if passed is not None:
            self.passed = passed
        else:
            self.passed = not (self.errors or self.javascript_errors or self.webgl_errors or self.warnings)
    
    def add_error(self, error_type: str, message: str, details: Dict[str, Any] = None):
        """Add an error to the test result."""
        error = {
            'type': error_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if error_type == 'webgl':
            self.webgl_errors.append(error)
        elif error_type == 'javascript':
            self.javascript_errors.append(error)
        elif error_type == 'network':
            self.network_errors.append(error)
        else:
            self.errors.append(error)
    
    def add_console_log(self, level: str, message: str, location: str = None):
        """Add a console log entry."""
        log_entry = {
            'level': level,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'location': location
        }
        
        self.console_logs.append(log_entry)

        if level in ['error', 'assert']:
            self.add_error('console', message, {'level': level, 'location': location})
        elif level in ['warn', 'warning']:
            self.warnings.append(log_entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary for JSON serialization."""
        data = {
            'test_path': self.test_path,
            'browser_name': self.browser_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'passed': self.passed,
            'errors': self.errors,
            'warnings': self.warnings,
            'console_logs': self.console_logs,
            'webgl_errors': self.webgl_errors,
            'javascript_errors': self.javascript_errors,
            'network_errors': self.network_errors,
            'browser_info': self.browser_info,
            'completed': self.completed,
            'validation_error': self.validation_error,
            'screenshot_path': self.screenshot_path,
            'summary': {
                'total_errors': len(self.errors) + len(self.javascript_errors) + len(self.webgl_errors),
                'total_warnings': len(self.warnings),
                'console_entries': len(self.console_logs)
            }
        }
        if self.webgl_profile is not None:
            data['webgl_profile'] = self.webgl_profile
        return data


class WebGPUTestRunner:
    """Main test runner class."""
    PROFILE_OUTCOME_CAP = 2048
    
    def __init__(self, test_dir: str = "testcases", timeout: int = 30000, headless: bool = False, browser_config: Dict[str, str] = None, force_firefox: bool = False, capture_screenshots: bool = True, max_workers: int = 1, profile_webgl: bool = False, profile_event_cap: int = 20000):
        self.test_dir = Path(test_dir)
        self.timeout = timeout
        self.headless = headless
        self.browser_config = browser_config or {}
        self.force_firefox = force_firefox
        self.capture_screenshots = capture_screenshots
        self.max_workers = max_workers
        self.profile_webgl = profile_webgl
        self.profile_event_cap = profile_event_cap
        self.launch_metadata: Dict[str, Dict[str, Any]] = {}
        if profile_event_cap < 1:
            raise ValueError("profile_event_cap must be positive")
        self.profiler_source = (Path(__file__).parent / 'scripts/api_audit/webgl_trace.js').read_text() if profile_webgl else None
        self.results: List[TestResult] = []
        self.logger = self._setup_logging()
    
    @staticmethod
    def load_browser_config(config_file: str) -> Dict[str, Any]:
        """Load browser configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            print(f"Warning: Config file {config_file} not found, using defaults")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file {config_file}: {e}")
            return {}
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('webgl_test_runner.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    def discover_tests(self) -> List[str]:
        """Discover all HTML test files in the test directory."""
        test_files = []
        
        if not self.test_dir.exists():
            self.logger.error(f"Test directory {self.test_dir} does not exist")
            return test_files
        
        # Recursively find all .html files
        for html_file in self.test_dir.rglob("*.html"):
            test_files.append(str(html_file if self.test_dir.is_absolute()
                                  else html_file.relative_to(self.test_dir.parent)))
        
        self.logger.info(f"Discovered {len(test_files)} test files")
        return sorted(test_files)
    
    async def setup_browser(self, browser_name: str) -> tuple[Browser, BrowserContext]:
        """Set up browser with WebGPU enabled."""
        playwright = await async_playwright().__aenter__()
        
        # Browser-specific arguments for WebGPU
        browser_args = []
        
        # Get custom browser path if configured
        browser_path = self.browser_config.get(f'{browser_name}_path')
        
        if browser_name == 'chromium':
            browser_args = [
                '--enable-features=Vulkan,UseSkiaRenderer',
                '--disable-vulkan-fallback-to-gl-for-testing',
                '--enable-dawn-features=allow_unsafe_apis',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu-sandbox',
                '--enable-gpu-rasterization',
                '--ignore-gpu-blocklist',
                '--enable-experimental-extension-apis',
                '--enable-experimental-web-platform-features'
            ]
            
            # Add custom arguments if configured
            custom_args = self.browser_config.get('chromium_args', [])
            if custom_args:
                browser_args.extend(custom_args)
            
            launch_options = {
                'headless': self.headless,
                'args': browser_args
            }
            if browser_path:
                launch_options['executable_path'] = browser_path
                self.logger.info(f"Using custom Chromium path: {browser_path}")
            
            browser = await playwright.chromium.launch(**launch_options)
            self._remember_launch(browser_name, launch_options.get('executable_path') or playwright.chromium.executable_path,
                                  browser_args, {})
            
        elif browser_name == 'firefox':
            # Create a temporary Firefox profile to avoid profile conflicts
            firefox_profile_dir = tempfile.mkdtemp(prefix='webgpu_test_firefox_profile_')
            self.logger.debug(f"Created temporary Firefox profile: {firefox_profile_dir}")

            # Firefox-specific arguments (without profile since we use user_data_dir)
            firefox_args = [
                '--new-instance',  # Start a new Firefox instance
                '--no-remote',     # Don't connect to existing instance
            ]

            # Add custom arguments if configured
            custom_args = self.browser_config.get('firefox_args', [])
            if custom_args:
                firefox_args.extend(custom_args)

            # Prepare launch options for persistent context
            context_options = {
                'headless': self.headless,
                'args': firefox_args,
                'user_data_dir': firefox_profile_dir,  # Firefox uses user_data_dir instead of profile args
                'firefox_user_prefs': {
                    # --- UNLOCK WEBGL FEATURES ---
                    # 1. Disable Fingerprinting Protection
                    # This is the #1 cause of missing OES_texture_float.
                    # When enabled, it blocks float textures to prevent hardware identification.
                    'privacy.resistFingerprinting': False,

                    # 2. Force WebGL 2 and Extensions
                    'webgl.enable-webgl2': True,
                    'webgl.force-enabled': True,
                    'webgl.disable-extensions': False,
                    'webgl.enable-draft-extensions': True,
                    'webgl.enable-privileged-extensions': True,

                    # 3. Disable "Safe Mode" & Performance Throttling
                    # Automation defaults to "min_capability_mode" which strips features.
                    'webgl.min_capability_mode': False,
                    'webgl.disable-fail-if-major-performance-caveat': True,

                    # 4. Force Hardware Acceleration (Linux specific)
                    'layers.acceleration.force-enabled': True,
                    'gfx.webrender.all': True,
                    'gfx.x11-egl.force-enabled': True, # Force EGL backend (matches Ubuntu native)
                    'gl.provider': 'EGL',

                    # 5. Ensure Shared Memory is enabled (required for large texture operations)
                    'dom.ipc.processCount.web_isolated': 1,
                    'dom.ipc.keepProcessesAlive.web': 1,
                }
            }

            if browser_path:
                # Check if the custom Firefox supports Playwright automation
                if self.force_firefox or await self._check_firefox_compatibility(browser_path):
                    context_options['executable_path'] = browser_path
                    if self.force_firefox:
                        self.logger.info(f"Force using custom Firefox path: {browser_path}")
                    else:
                        self.logger.info(f"Using custom Firefox path: {browser_path}")
                else:
                    self.logger.warning(f"Custom Firefox at {browser_path} may not support Playwright automation")
                    self.logger.info("Falling back to system Firefox or skipping Firefox tests")
                    self.logger.info("Use --force-firefox to override compatibility check")
                    # Try to fall back to system Firefox
                    system_firefox = await self._find_system_firefox()
                    if system_firefox:
                        context_options['executable_path'] = system_firefox
                        self.logger.info(f"Using system Firefox: {system_firefox}")
                    else:
                        # Clean up the temporary profile directory before raising error
                        shutil.rmtree(firefox_profile_dir, ignore_errors=True)
                        raise ValueError(f"No compatible Firefox found. Custom Firefox at {browser_path} doesn't support automation. Use --force-firefox to try anyway.")

            # Use launch_persistent_context for Firefox profile management
            context = await playwright.firefox.launch_persistent_context(**context_options)
            context._temp_profile_dir = firefox_profile_dir  # Store for cleanup
            self._remember_launch(browser_name, context_options.get('executable_path') or playwright.firefox.executable_path,
                                  firefox_args, context_options['firefox_user_prefs'])
            
        elif browser_name == 'webkit':
            launch_options = {'headless': self.headless}
            if browser_path:
                launch_options['executable_path'] = browser_path
                self.logger.info(f"Using custom WebKit path: {browser_path}")
            
            browser = await playwright.webkit.launch(**launch_options)
            self._remember_launch(browser_name, launch_options.get('executable_path') or playwright.webkit.executable_path, [], {})
        else:
            raise ValueError(f"Unsupported browser: {browser_name}")
        
        # Handle Firefox differently since it uses launch_persistent_context
        if browser_name == 'firefox':
            # For Firefox, context is already created by launch_persistent_context
            # Skip context creation and preference setting
            pass
        else:
            # Create context with browser-specific permissions for other browsers
            context_options = {
                'ignore_https_errors': True
            }

            # Only add permissions for browsers that support them
            if browser_name == 'chromium':
                context_options['permissions'] = ['camera', 'microphone']

            context = await browser.new_context(**context_options)
        
        # Handle Firefox differently since it uses launch_persistent_context
        if browser_name == 'firefox':
            return None, context
        else:
            return browser, context

    def _remember_launch(self, browser_name: str, executable: str, args: List[str], preferences: Dict[str, Any]):
        path = str(Path(executable).resolve()) if executable else None
        binary_path = Path(path) if path else None
        chrome_binary = binary_path.with_name('chrome') if binary_path and binary_path.name != 'chrome' else None
        if chrome_binary and chrome_binary.is_file():
            try:
                with chrome_binary.open('rb') as binary_file:
                    if binary_file.read(4) == b'\x7fELF':
                        binary_path = chrome_binary
            except OSError:
                pass
        identity = {'path': str(binary_path) if binary_path else None}
        if path and binary_path and str(binary_path) != path:
            identity['launched_path'] = path
        if binary_path:
            try:
                stat = os.stat(binary_path)
                identity.update(size=stat.st_size, mtime_ns=stat.st_mtime_ns)
            except OSError:
                identity['available'] = False
        self.launch_metadata[browser_name] = {
            'executable': identity, 'launch_flags': list(args), 'preferences': preferences,
            'headless': self.headless,
        }

    def get_profile_identity(self, browser_name: str, context: BrowserContext) -> Dict[str, Any]:
        """Return the stable lane identity used to validate a cached WebGL profile."""
        browser = context.browser
        identity = {'browser_name': browser_name, 'browser_version': browser.version if browser else None,
                    'profiler_version': 'webgl-trace-2', 'event_cap': self.profile_event_cap,
                    'outcome_cap': self.PROFILE_OUTCOME_CAP,
                    'context': {'ignore_https_errors': True,
                                'permissions': ['camera', 'microphone'] if browser_name == 'chromium' else []},
                    **self.launch_metadata.get(browser_name, {})}
        identity['fingerprint'] = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return identity

    def _append_profile_outcome(self, profile: Dict[str, Any], outcome: Dict[str, Any]):
        outcomes = profile.setdefault('outcomes', [])
        outcome_cap = profile.get('outcome_cap', self.PROFILE_OUTCOME_CAP)
        if len(outcomes) < outcome_cap - 1:
            outcomes.append(outcome)
        elif not any(item.get('code') == 'outcome_buffer_full' for item in outcomes):
            marker = {'code': 'outcome_buffer_full'}
            if len(outcomes) >= outcome_cap:
                outcomes[-1] = marker
            else:
                outcomes.append(marker)

    async def _attach_profile_failure(self, result: TestResult, browser_name: str,
                                      context: BrowserContext, code: str, message: str,
                                      page: Optional[Page] = None, elapsed_ms: Optional[float] = None):
        """Retain lane identity and an explicit failure outcome on every profiled error path."""
        profile = None
        if page is not None:
            try:
                profile = await asyncio.wait_for(
                    page.evaluate('''() => window.__webglProfiler?.finish() || null'''),
                    timeout=min(0.1, max(0.001, self.timeout / 1000)))
            except Exception:
                pass
        if not isinstance(profile, dict):
            profile = {'schema_version': 1, 'profiler_version': 'webgl-trace-2',
                       'outcome_cap': self.PROFILE_OUTCOME_CAP,
                       'contexts': [], 'events': [], 'truncated': False, 'outcomes': []}
        profile.setdefault('contexts', [])
        profile.setdefault('events', [])
        profile.setdefault('truncated', False)
        profile.setdefault('timing', {})
        if elapsed_ms is not None:
            profile['timing']['navigation_elapsed_ms'] = elapsed_ms
        profile['identity'] = self.get_profile_identity(browser_name, context)
        self._append_profile_outcome(profile, {'code': code, 'message': message})
        result.webgl_profile = profile
    
    async def _check_firefox_compatibility(self, firefox_path: str) -> bool:
        """Check if a Firefox installation supports Playwright automation."""
        try:
            # Test Firefox version and check for automation support
            result = subprocess.run([firefox_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False
            
            version_output = result.stdout.lower()
            self.logger.debug(f"Firefox version output: {version_output}")
            
            # Check if it's a known problematic version or installation
            # Developer edition, nightly, and recent stable versions usually work
            problematic_indicators = [
                'esr',  # ESR versions sometimes have issues
                'snap', # Snap versions may have sandboxing issues
            ]
            
            # For now, let's be permissive and try most Firefox versions
            # The real test is whether Playwright can launch it
            return True
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    async def _find_system_firefox(self) -> str:
        """Find a system Firefox installation that works with Playwright."""
        candidates = [
            '/usr/bin/firefox',
            '/usr/bin/firefox-esr', 
            '/snap/bin/firefox',
            '/usr/bin/firefox-developer-edition',
            '/opt/firefox/firefox'
        ]
        
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                if await self._check_firefox_compatibility(candidate):
                    return candidate
        
        return None
    
    async def run_test(self, test_path: str, browser_name: str, context: BrowserContext) -> TestResult:
        """Run a single test case and capture results."""
        result = TestResult(test_path, browser_name)
        page = None
        profile_deadline = time.perf_counter() + self.timeout / 1000 if self.profile_webgl else None

        async def profile_await(awaitable):
            if profile_deadline is None:
                return await awaitable
            remaining = profile_deadline - time.perf_counter()
            if remaining <= 0:
                close = getattr(awaitable, 'close', None)
                if close:
                    close()
                raise asyncio.TimeoutError('WebGL profiling case deadline exceeded')
            return await asyncio.wait_for(awaitable, timeout=remaining)
        
        try:
            self.logger.info(f"Running test: {test_path} in {browser_name}")
            
            page = await profile_await(context.new_page())
            await profile_await(page.add_init_script("document.addEventListener('webglcontextlost', () => { window.__webglContextLost = true; }, true)"))
            if self.profile_webgl:
                profiler_source = self.profiler_source.replace('__WEBGL_EVENT_CAP__', str(self.profile_event_cap))
                await profile_await(page.add_init_script(profiler_source.replace('__WEBGL_OUTCOME_CAP__', str(self.PROFILE_OUTCOME_CAP))))
            
            # Set up error handlers
            page.on('pageerror', lambda error: self._handle_page_error(result, error))
            page.on('console', lambda msg: self._handle_console_message(result, msg))
            page.on('requestfailed', lambda request: self._handle_network_error(result, request))
            
            # Navigate to test file
            file_url = f"file://{os.path.abspath(test_path)}"
            navigation_started = time.perf_counter()
            
            try:
                await profile_await(page.goto(file_url, timeout=self.timeout,
                                              wait_until='domcontentloaded' if self.profile_webgl else 'networkidle'))
            except Exception as e:
                result.add_error('navigation', f"Failed to load test: {str(e)}")
                if self.profile_webgl:
                    elapsed_ms = round((time.perf_counter() - navigation_started) * 1000, 3)
                    await self._attach_profile_failure(result, browser_name, context,
                                                       'navigation_failed', str(e), page, elapsed_ms)
                result.finish(False)
                return result

            if self.profile_webgl:
                completed = False
                try:
                    await profile_await(page.wait_for_function('window.__done === true', timeout=self.timeout))
                    completed = True
                except Exception:
                    pass
                navigation_to_completion_ms = round((time.perf_counter() - navigation_started) * 1000, 3)
                profile = None
                try:
                    profile = await profile_await(page.evaluate('''() => window.__webglProfiler?.finish() || null'''))
                    if profile is None:
                        profile = {'schema_version': 1, 'profiler_version': 'webgl-trace-2',
                                   'outcome_cap': self.PROFILE_OUTCOME_CAP,
                                   'contexts': [], 'events': [], 'truncated': False, 'outcomes': []}
                    profile['timing'] = ({'navigation_to_completion_ms': navigation_to_completion_ms}
                                          if completed else {'navigation_elapsed_ms': navigation_to_completion_ms})
                    profile['identity'] = self.get_profile_identity(browser_name, context)
                    if not completed:
                        self._append_profile_outcome(profile, {'code': 'missing_completion'})
                        result.add_error('completion', 'Profiling requires window.__done === true')
                    if await profile_await(page.evaluate('Boolean(window.__webglContextLost)')):
                        self._append_profile_outcome(profile, {'code': 'context_lost'})
                    for outcome in profile['outcomes']:
                        if outcome.get('code') in {'seed_webgl_error', 'remaining_webgl_error', 'error_drain_incomplete', 'context_lost', 'outcome_buffer_full'}:
                            result.add_error('webgl', f"Profile observed {outcome['code']}: {outcome}")
                    result.webgl_profile = profile
                except Exception as e:
                    if not isinstance(profile, dict):
                        profile = {'schema_version': 1, 'profiler_version': 'webgl-trace-2',
                                   'outcome_cap': self.PROFILE_OUTCOME_CAP,
                                   'contexts': [], 'events': [], 'truncated': False, 'outcomes': []}
                    profile.setdefault('contexts', [])
                    profile.setdefault('events', [])
                    profile.setdefault('truncated', False)
                    profile['timing'] = ({'navigation_to_completion_ms': navigation_to_completion_ms}
                                         if completed else {'navigation_elapsed_ms': navigation_to_completion_ms})
                    profile['identity'] = self.get_profile_identity(browser_name, context)
                    self._append_profile_outcome(profile, {'code': 'profiler_error', 'message': str(e)})
                    result.webgl_profile = profile
                    result.add_error('profiler', f'WebGL profiler failed: {e}')
            
            # Get browser info
            browser_info = await profile_await(page.evaluate('''
                () => {
                    return {
                        userAgent: navigator.userAgent,
                        webglSupported: !!document.createElement('canvas').getContext('webgl') || !!document.createElement('canvas').getContext('experimental-webgl'),
                        vendor: navigator.vendor,
                        platform: navigator.platform,
                        language: navigator.language
                    };
                }
            '''))
            result.browser_info = browser_info
            
            # Check WebGPU availability
            webgl_info = await profile_await(self._check_webgl_support(page, result))
            result.browser_info['webgl'] = webgl_info
            
            # Wait for test execution (give it time to run)
            if not self.profile_webgl:
                await asyncio.sleep(5)
            
            # Check for any runtime errors by examining the page state
            await profile_await(self._check_test_completion(page, result))
            
            # Capture screenshot before finishing (if enabled)
            if self.capture_screenshots:
                await profile_await(self._capture_screenshot(page, result))
                if self.profile_webgl and result.screenshot_path and result.webgl_profile:
                    try:
                        from PIL import Image
                        pixels = Image.open(result.screenshot_path).convert('RGBA').tobytes()
                        result.webgl_profile['image_sha256'] = hashlib.sha256(pixels).hexdigest()
                        result.webgl_profile['image_hash_kind'] = 'rgba_pixels'
                    except ImportError:
                        result.webgl_profile['image_hash_kind'] = 'unavailable_no_pixel_decoder'
            
            result.finish()
            
        except Exception as e:
            self.logger.error(f"Error running test {test_path}: {str(e)}")
            result.add_error('runner', f"Test runner error: {str(e)}")
            if self.profile_webgl:
                if result.webgl_profile is None:
                    await self._attach_profile_failure(result, browser_name, context,
                                                       'runner_error', str(e), page)
                else:
                    self._append_profile_outcome(result.webgl_profile,
                                                 {'code': 'runner_error', 'message': str(e)})
            result.finish(False)
        
        finally:
            if page:
                try:
                    close_timeout = min(0.25, max(0.01, self.timeout / 1000)) if self.profile_webgl else None
                    if close_timeout is None:
                        await page.close()
                    else:
                        await asyncio.wait_for(page.close(), timeout=close_timeout)
                except Exception as e:
                    if not self.profile_webgl:
                        raise
                    result.add_error('runner', f"Failed to close browser page: {str(e)}")
                    if result.webgl_profile is None:
                        await self._attach_profile_failure(result, browser_name, context,
                                                           'runner_error', str(e), page)
                    else:
                        self._append_profile_outcome(result.webgl_profile,
                                                     {'code': 'runner_error', 'message': str(e)})
                    result.finish(False)
        
        return result
    
    async def _check_webgl_support(self, page: Page, result: TestResult) -> Dict[str, Any]:
        """Check WebGL support and get context info."""
        try:
            webgl_info = await page.evaluate('''
                () => {
                    const canvas = document.createElement('canvas');

                    // Try WebGL2 first, then WebGL1
                    let gl = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl');

                    if (!gl) {
                        return { supported: false, error: 'WebGL not supported' };
                    }

                    // Get basic WebGL info
                    const debugInfo = navigator.userAgent.includes('Firefox') ? null : gl.getExtension('WEBGL_debug_renderer_info');
                    const renderer = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
                    const vendor = debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);

                    // Check for common extensions
                    const extensions = gl.getSupportedExtensions() || [];

                    // Get WebGL limits/parameters
                    const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
                    const maxViewportDims = gl.getParameter(gl.MAX_VIEWPORT_DIMS);

                    return {
                        supported: true,
                        version: gl instanceof WebGL2RenderingContext ? 'WebGL2' : 'WebGL1',
                        renderer: renderer,
                        vendor: vendor,
                        extensions: extensions,
                        limits: {
                            maxTextureSize: maxTextureSize,
                            maxViewportWidth: maxViewportDims[0],
                            maxViewportHeight: maxViewportDims[1]
                        }
                    };
                }
            ''')

            if not webgl_info['supported']:
                result.add_error('webgl', webgl_info['error'])

            return webgl_info

        except Exception as e:
            error_msg = f"Failed to check WebGL support: {str(e)}"
            result.add_error('webgl', error_msg)
            return {'supported': False, 'error': error_msg}
    
    async def _check_test_completion(self, page: Page, result: TestResult):
        """Check if the test completed successfully by examining page state."""
        try:
            # Check for common success indicators
            test_state = await page.evaluate('''
                () => {
                    // Look for canvas element
                    const canvas = document.querySelector('canvas');
                    
                    // Check if there are any error messages in the DOM
                    const errorElements = document.querySelectorAll('.error, [class*="error"]');
                    const errorMessages = Array.from(errorElements).map(el => el.textContent);
                    
                    // Check if WebGPU context was created
                    let webgpuContext = null;
                    if (canvas) {
                        try {
                            webgpuContext = canvas.getContext('webgpu');
                        } catch (e) {
                            // Ignore context creation errors here
                        }
                    }
                    
                    return {
                        hasCanvas: !!canvas,
                        hasWebGPUContext: !!webgpuContext,
                        contextLost: !!window.__webglContextLost || !!(canvas && canvas.getContext('webgl2')?.isContextLost()),
                        completed: typeof window.__done === 'boolean' ? window.__done : null,
                        validationError: typeof window.__validationError === 'number' ? window.__validationError : null,
                        errorMessages: errorMessages,
                        title: document.title,
                        bodyText: document.body ? document.body.textContent.slice(0, 500) : ''
                    };
                }
            ''')

            result.completed = test_state.get('completed')
            result.validation_error = test_state.get('validationError')
            
            # Add any DOM error messages to result
            for error_msg in test_state.get('errorMessages', []):
                if error_msg.strip():
                    result.add_error('dom', f"Error found in DOM: {error_msg.strip()}")
            if test_state.get('contextLost'):
                result.add_error('webgl', 'WebGL context lost')
            if test_state.get('completed') is False:
                result.add_error('completion', 'Test did not finish')
            if test_state.get('hasCanvas') is False:
                result.add_error('completion', 'Test canvas missing')
            
        except Exception as e:
            result.add_error('completion', f"Could not check test completion state: {str(e)}")
    
    async def _capture_screenshot(self, page: Page, result: TestResult):
        """Capture a screenshot of the test page."""
        try:
            # Generate screenshot filename based on test path and browser (no timestamp)
            test_name = Path(result.test_path).stem
            browser_name = result.browser_name
            screenshot_filename = f"{test_name}_{browser_name}.png"
            
            # Create screenshots directory if it doesn't exist
            screenshots_dir = Path("screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            screenshot_path = screenshots_dir / screenshot_filename
            
            # Capture full page screenshot (this will overwrite existing file)
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Store the relative path in the result
            result.screenshot_path = str(screenshot_path)
            
            self.logger.info(f"Screenshot captured: {screenshot_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to capture screenshot for {result.test_path}: {str(e)}")
            result.add_error('screenshot', f"Screenshot capture failed: {str(e)}")
    
    def _handle_page_error(self, result: TestResult, error):
        """Handle JavaScript page errors."""
        result.add_error('javascript', str(error))
        self.logger.warning(f"Page error in {result.test_path}: {str(error)}")
    
    def _handle_console_message(self, result: TestResult, msg):
        """Handle console messages."""
        level = msg.type
        text = msg.text
        location = f"{msg.location['url']}:{msg.location['lineNumber']}"
        
        result.add_console_log(level, text, location)
        
        if level in ['error', 'assert']:
            self.logger.warning(f"Console {level} in {result.test_path}: {text}")
    
    def _handle_network_error(self, result: TestResult, request):
        """Handle network request failures."""
        error_msg = f"Failed to load: {request.url} ({request.failure})"
        result.add_error('network', error_msg)
        self.logger.warning(f"Network error in {result.test_path}: {error_msg}")
    
    async def run_tests(self, test_files: List[str] = None, browsers: List[str] = None) -> List[TestResult]:
        """Run all specified tests in specified browsers."""
        if test_files is None:
            test_files = self.discover_tests()
        
        if browsers is None:
            browsers = ['chromium']  # Default to Chromium
        
        parallel_mode = self.max_workers > 1
        self.logger.info(f"Starting test run: {len(test_files)} tests in {len(browsers)} browsers (parallel: {parallel_mode}, workers: {self.max_workers})")
        
        for browser_name in browsers:
            self.logger.info(f"Testing with browser: {browser_name}")
            
            try:
                browser, context = await self.setup_browser(browser_name)
                
                if parallel_mode:
                    # Run tests in parallel with semaphore to limit concurrency
                    semaphore = asyncio.Semaphore(self.max_workers)
                    
                    async def run_test_with_semaphore(test_file: str):
                        async with semaphore:
                            result = await self.run_test(test_file, browser_name, context)
                            self.results.append(result)
                            # Log result
                            status = "PASS" if result.passed else "FAIL"
                            self.logger.info(f"{status}: {test_file} ({result.duration_ms}ms)")
                            return result
                    
                    # Run all tests in parallel (limited by semaphore)
                    await asyncio.gather(*[run_test_with_semaphore(test_file) for test_file in test_files])
                else:
                    # Sequential execution (original behavior)
                    for test_file in test_files:
                        result = await self.run_test(test_file, browser_name, context)
                        self.results.append(result)
                        
                        # Log result
                        status = "PASS" if result.passed else "FAIL"
                        self.logger.info(f"{status}: {test_file} ({result.duration_ms}ms)")
                
                await context.close()
                if browser:  # browser is None for Firefox
                    await browser.close()

                # Clean up temporary Firefox profile if it exists
                temp_profile_dir = None
                if browser_name == 'firefox':
                    # For Firefox, profile dir is stored on context
                    if hasattr(context, '_temp_profile_dir'):
                        temp_profile_dir = context._temp_profile_dir
                else:
                    # For other browsers, check browser object
                    if hasattr(browser, '_temp_profile_dir'):
                        temp_profile_dir = browser._temp_profile_dir

                if temp_profile_dir:
                    try:
                        shutil.rmtree(temp_profile_dir, ignore_errors=True)
                        self.logger.debug(f"Cleaned up temporary Firefox profile: {temp_profile_dir}")
                    except Exception as e:
                        self.logger.warning(f"Failed to clean up Firefox profile {temp_profile_dir}: {str(e)}")
                
            except ValueError as e:
                # Handle browser compatibility issues gracefully
                if "No compatible Firefox found" in str(e):
                    self.logger.error(f"Firefox compatibility issue: {str(e)}")
                    self.logger.info("Tip: Try using system Firefox or install Firefox through your package manager")
                    # Skip this browser but continue with others
                    continue
                else:
                    self.logger.error(f"Browser setup error for {browser_name}: {str(e)}")
                    continue
            except Exception as e:
                self.logger.error(f"Failed to run tests in {browser_name}: {str(e)}")
                # Add browser-specific troubleshooting tips
                if browser_name == 'firefox':
                    self.logger.info("Firefox troubleshooting tips:")
                    self.logger.info("1. Use system Firefox: --firefox-path /usr/bin/firefox")
                    self.logger.info("2. Try Firefox Developer Edition")
                    self.logger.info("3. Check that Firefox supports automation (not all custom builds do)")
                continue
        
        return self.results
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate HTML test report."""
        if output_file is None:
            output_file = f"webgpu_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Calculate summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        browsers = list(set(r.browser_name for r in self.results))
        
        html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <title>WebGPU Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .test-result {{ margin: 10px 0; padding: 15px; border-radius: 5px; border-left: 5px solid #ddd; }}
        .pass {{ border-left-color: #28a745; background: #d4edda; }}
        .fail {{ border-left-color: #dc3545; background: #f8d7da; }}
        .error {{ color: #dc3545; font-family: monospace; margin: 5px 0; }}
        .warning {{ color: #856404; font-family: monospace; margin: 5px 0; }}
        .console {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 3px; }}
        .details {{ margin-top: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>WebGPU Test Report</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Tests:</strong> {total_tests}</p>
        <p><strong>Passed:</strong> {passed_tests}</p>
        <p><strong>Failed:</strong> {failed_tests}</p>
        <p><strong>Browsers:</strong> {', '.join(browsers)}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <h2>Test Results</h2>
'''
        
        for result in self.results:
            status_class = 'pass' if result.passed else 'fail'
            status_text = 'PASS' if result.passed else 'FAIL'
            
            html_content += f'''
    <div class="test-result {status_class}">
        <h3>{result.test_path} - {result.browser_name} - {status_text}</h3>
        <p><strong>Duration:</strong> {result.duration_ms}ms</p>
        
        <div class="details">
'''
            
            # Add errors
            if result.errors or result.javascript_errors or result.webgl_errors:
                html_content += '<h4>Errors:</h4>'
                for error in result.errors + result.javascript_errors + result.webgl_errors:
                    html_content += f'<div class="error">[{error["type"]}] {error["message"]}</div>'
            
            # Add warnings
            if result.warnings:
                html_content += '<h4>Warnings:</h4>'
                for warning in result.warnings:
                    html_content += f'<div class="warning">{warning["message"]}</div>'
            
            # Add console logs (limited)
            if result.console_logs:
                html_content += '<h4>Console Output (first 10 entries):</h4>'
                html_content += '<div class="console">'
                for log in result.console_logs[:10]:
                    html_content += f'<div>[{log["level"]}] {log["message"]}</div>'
                html_content += '</div>'
            
            # Add screenshot if available
            if result.screenshot_path and Path(result.screenshot_path).exists():
                html_content += f'<h4>Screenshot:</h4>'
                html_content += f'<img src="{result.screenshot_path}" alt="Test Screenshot" style="max-width: 100%; border: 1px solid #ddd; border-radius: 3px;">'
            
            html_content += '''
        </div>
    </div>
'''
        
        html_content += '''
</body>
</html>
'''
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML report generated: {output_file}")
        return output_file
    
    def _convert_html_path_to_json(self, html_path: str) -> str:
        """Convert HTML file path to corresponding JSON file path."""
        if html_path.endswith('.html'):
            return html_path[:-5] + '.json'
        return html_path + '.json'
    
    def _convert_test_path_to_json(self, test_path: str) -> str:
        """Convert test file path to JSON output path."""
        if test_path.endswith('.html'):
            return test_path[:-5] + '.json'
        return test_path + '.json'
    
    def export_json(self, output_file: str = None, test_file_path: str = None) -> str:
        """Export results to JSON file and copy screenshots alongside."""
        if output_file is None:
            if test_file_path:
                # Convert test file path to JSON path (e.g., testcases/test.html -> testcases/test.json)
                output_file = self._convert_test_path_to_json(test_file_path)
            else:
                output_file = f"webgpu_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_tests': len(self.results),
                'browsers': list(set(r.browser_name for r in self.results)),
                'summary': {
                    'passed': sum(1 for r in self.results if r.passed),
                    'failed': sum(1 for r in self.results if not r.passed),
                    'total_errors': sum(len(r.errors) + len(r.javascript_errors) + len(r.webgl_errors) for r in self.results),
                    'total_warnings': sum(len(r.warnings) for r in self.results)
                }
            },
            'results': [result.to_dict() for result in self.results]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        # Copy screenshots to be alongside the JSON file (if screenshots are enabled)
        if self.capture_screenshots:
            self._copy_screenshots_to_output(output_file)
        
        self.logger.info(f"JSON results exported: {output_file}")
        return output_file
    
    def _copy_screenshots_to_output(self, json_output_file: str):
        """Copy screenshots to be alongside the JSON output file."""
        try:
            json_path = Path(json_output_file)
            output_dir = json_path.parent
            
            # Create a screenshots subdirectory next to the JSON file
            local_screenshots_dir = output_dir / "screenshots"
            local_screenshots_dir.mkdir(exist_ok=True)
            
            # Copy each screenshot to the local directory
            for result in self.results:
                if result.screenshot_path and Path(result.screenshot_path).exists():
                    source_screenshot = Path(result.screenshot_path)
                    dest_screenshot = local_screenshots_dir / source_screenshot.name
                    
                    # Copy the screenshot
                    shutil.copy2(source_screenshot, dest_screenshot)
                    
                    # Update the screenshot path in the result to be relative to the JSON file
                    result.screenshot_path = str(dest_screenshot.relative_to(output_dir))
                    
                    self.logger.info(f"Screenshot copied to: {dest_screenshot}")
            
        except Exception as e:
            self.logger.warning(f"Failed to copy screenshots to output directory: {str(e)}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='WebGPU Test Runner')
    parser.add_argument('--test-dir', default='testcases', help='Directory containing test files')
    parser.add_argument('--test-file', help='Run specific test file')
    parser.add_argument('--browsers', nargs='+', default=['chromium'], 
                       choices=['chromium', 'firefox', 'webkit'],
                       help='Browsers to test with')
    parser.add_argument('--timeout', type=int, default=30000, help='Test timeout in milliseconds')
    parser.add_argument('--output-dir', default='.', help='Output directory for reports')
    parser.add_argument('--json', action='store_true', help='Export JSON results (default)')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--headless', action='store_true', help='Run browsers in headless mode (default: False for WebGPU compatibility)')
    parser.add_argument('--browser-config', help='Path to browser configuration JSON file')
    parser.add_argument('--chromium-path', help='Path to custom Chromium/Chrome executable')
    parser.add_argument('--firefox-path', help='Path to custom Firefox executable')
    parser.add_argument('--webkit-path', help='Path to custom WebKit executable')
    parser.add_argument('--force-firefox', action='store_true', help='Force use of custom Firefox even if compatibility check fails')
    parser.add_argument('--no-screenshots', action='store_true', help='Disable screenshot capture')
    parser.add_argument('--profile-webgl', action='store_true', help='Record seed WebGL calls and state metadata')
    parser.add_argument('--profile-event-cap', type=int, default=20000, help='Maximum recorded WebGL calls per test')
    parser.add_argument('--parallel', '--workers', type=int, default=1, metavar='N', 
                       help='Number of parallel workers for running tests (default: 1, sequential)')
    
    args = parser.parse_args()
    
    # Load browser configuration
    browser_config = {}
    if args.browser_config:
        browser_config = WebGPUTestRunner.load_browser_config(args.browser_config)
    
    # Override with command line arguments
    if args.chromium_path:
        browser_config['chromium_path'] = args.chromium_path
    if args.firefox_path:
        browser_config['firefox_path'] = args.firefox_path
    if args.webkit_path:
        browser_config['webkit_path'] = args.webkit_path
    
    # Initialize test runner
    runner = WebGPUTestRunner(
        args.test_dir, 
        args.timeout, 
        args.headless, 
        browser_config, 
        args.force_firefox, 
        not args.no_screenshots,
        max_workers=args.parallel,
        profile_webgl=args.profile_webgl,
        profile_event_cap=args.profile_event_cap
    )
    
    # Determine which tests to run
    if args.test_file:
        test_files = [args.test_file]
    else:
        test_files = runner.discover_tests()
    
    if not test_files:
        print("No test files found!")
        return
    
    # Run tests
    results = await runner.run_tests(test_files, args.browsers)
    
    # Generate reports
    os.chdir(args.output_dir)
    
    # Generate HTML report first if requested
    if args.html:
        html_file = runner.generate_report()
        print(f"HTML report: {html_file}")
    
    # Always generate JSON (default behavior), use test file path as base if available
    if len(test_files) == 1:
        # For single test file, use the test file path to determine JSON output location
        json_file = runner.export_json(test_file_path=test_files[0])
    else:
        # For multiple test files, use default timestamped name
        json_file = runner.export_json()
    print(f"JSON results: {json_file}")
    
    # Print summary
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    
    print(f"\nTest Summary:")
    print(f"  Total: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    
    if failed > 0:
        print(f"\nFailed tests:")
        for result in results:
            if not result.passed:
                print(f"  {result.test_path} ({result.browser_name})")


if __name__ == '__main__':
    asyncio.run(main())
