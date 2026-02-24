# WebGPU Test Runner Setup

This document explains how to set up the virtual environment and dependencies for the WebGPU Test Runner.

## Quick Setup

### Option 1: Automated Setup (Recommended)

Run the automated setup script:

```bash
./setup_venv.sh
```

This script will:
- Create a Python virtual environment in the `venv/` directory
- Install all required dependencies from `requirements.txt`
- Install Playwright browsers
- Verify the installation

### Option 2: Manual Setup

If you prefer to set up manually or the automated script fails:

1. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   ```

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install
   ```

5. **Deactivate when done**:
   ```bash
   deactivate
   ```

### Option 3: Global Installation (Fallback)

If you can't create a virtual environment (e.g., missing `python3-venv` package):

```bash
./install_dependencies.sh
```

**Note**: This installs dependencies globally, which is not recommended but will work.

## Troubleshooting

### Missing python3-venv Package

If you get an error about `ensurepip` not being available:

**On Debian/Ubuntu:**
```bash
sudo apt install python3-venv
```

**On other systems:**
Install the equivalent package for your distribution.

### Missing System Dependencies for Playwright

If Playwright shows warnings about missing system dependencies:

```bash
sudo playwright install-deps
```

Or manually install the required packages:
```bash
sudo apt-get install libevent-2.1-7t64 libgstreamer-plugins-bad1.0-0 libflite1 libavif16 gstreamer1.0-libav
```

## Running Tests

Once setup is complete, you can run tests using:

```bash
./run_tests.sh --test-file [your_test_file.html] --browsers chromium
```

The `run_tests.sh` script automatically detects and uses the virtual environment if it exists.

## Files Created

After successful setup, you should have:
- `venv/` - Virtual environment directory
- All dependencies installed and ready to use

## Requirements

- Python 3.7 or higher
- pip
- python3-venv package (for virtual environment creation)
- Internet connection (for downloading Playwright browsers)
