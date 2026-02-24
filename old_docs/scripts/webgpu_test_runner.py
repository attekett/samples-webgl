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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
import logging

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright && playwright install")
    sys.exit(1)

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
        self.screenshot_path: Optional[str] = None
        
    def finish(self, passed: bool = None):
        """Mark the test as finished."""
        self.end_time = datetime.now()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        if passed is not None:
            self.passed = passed
        else:
            # Auto-determine pass/fail based on errors and warnings
            self.passed = len(self.errors) == 0 and len(self.javascript_errors) == 0 and len(self.webgl_errors) == 0 and len(self.warnings) == 0
    
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
        return {
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
            'screenshot_path': self.screenshot_path,
            'summary': {
                'total_errors': len(self.errors) + len(self.javascript_errors) + len(self.webgl_errors),
                'total_warnings': len(self.warnings),
                'console_entries': len(self.console_logs)
            }
        }


class WebGPUTestRunner:
    """Main test runner class."""
    
    def __init__(self, test_dir: str = "testcases", timeout: int = 30000, headless: bool = False, browser_config: Dict[str, str] = None, force_firefox: bool = False, capture_screenshots: bool = True, max_workers: int = 1):
        self.test_dir = Path(test_dir)
        self.timeout = timeout
        self.headless = headless
        self.browser_config = browser_config or {}
        self.force_firefox = force_firefox
        self.capture_screenshots = capture_screenshots
        self.max_workers = max_workers
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
            # Convert to relative path from test directory
            relative_path = html_file.relative_to(self.test_dir.parent)
            test_files.append(str(relative_path))
        
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
                'user_data_dir': firefox_profile_dir  # Firefox uses user_data_dir instead of profile args
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
            
        elif browser_name == 'webkit':
            launch_options = {'headless': self.headless}
            if browser_path:
                launch_options['executable_path'] = browser_path
                self.logger.info(f"Using custom WebKit path: {browser_path}")
            
            browser = await playwright.webkit.launch(**launch_options)
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
        
        try:
            self.logger.info(f"Running test: {test_path} in {browser_name}")
            
            page = await context.new_page()
            
            # Set up error handlers
            page.on('pageerror', lambda error: self._handle_page_error(result, error))
            page.on('console', lambda msg: self._handle_console_message(result, msg))
            page.on('requestfailed', lambda request: self._handle_network_error(result, request))
            
            # Navigate to test file
            file_url = f"file://{os.path.abspath(test_path)}"
            
            try:
                await page.goto(file_url, timeout=self.timeout, wait_until='networkidle')
            except Exception as e:
                result.add_error('navigation', f"Failed to load test: {str(e)}")
                result.finish(False)
                return result
            
            # Get browser info
            browser_info = await page.evaluate('''
                () => {
                    return {
                        userAgent: navigator.userAgent,
                        webglSupported: !!document.createElement('canvas').getContext('webgl') || !!document.createElement('canvas').getContext('experimental-webgl'),
                        vendor: navigator.vendor,
                        platform: navigator.platform,
                        language: navigator.language
                    };
                }
            ''')
            result.browser_info = browser_info
            
            # Check WebGPU availability
            webgl_info = await self._check_webgl_support(page, result)
            
            # Wait for test execution (give it time to run)
            await asyncio.sleep(5)
            
            # Check for any runtime errors by examining the page state
            await self._check_test_completion(page, result)
            
            # Capture screenshot before finishing (if enabled)
            if self.capture_screenshots:
                await self._capture_screenshot(page, result)
            
            result.finish()
            
        except Exception as e:
            self.logger.error(f"Error running test {test_path}: {str(e)}")
            result.add_error('runner', f"Test runner error: {str(e)}")
            result.finish(False)
        
        finally:
            if page:
                await page.close()
        
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
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    const renderer = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'Unknown';
                    const vendor = debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : 'Unknown';

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
                        errorMessages: errorMessages,
                        title: document.title,
                        bodyText: document.body ? document.body.textContent.slice(0, 500) : ''
                    };
                }
            ''')
            
            # Add any DOM error messages to result
            for error_msg in test_state.get('errorMessages', []):
                if error_msg.strip():
                    result.add_error('dom', f"Error found in DOM: {error_msg.strip()}")
            
        except Exception as e:
            self.logger.warning(f"Could not check test completion state: {str(e)}")
    
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
            if result.errors or result.javascript_errors or result.webgpu_errors:
                html_content += '<h4>Errors:</h4>'
                for error in result.errors + result.javascript_errors + result.webgpu_errors:
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
                    'total_errors': sum(len(r.errors) + len(r.javascript_errors) + len(r.webgpu_errors) for r in self.results),
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
        max_workers=args.parallel
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
