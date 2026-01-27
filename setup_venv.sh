#!/bin/bash
# WebGL Test Runner - Virtual Environment Setup Script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 WebGL Test Runner - Virtual Environment Setup${NC}"
echo "=" * 50

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is not installed or not in PATH${NC}"
    echo "Please install Python3 and try again."
    exit 1
fi

echo -e "${GREEN}✅ Python3 found: $(python3 --version)${NC}"

# Check if python3-venv is available
if ! python3 -m venv --help &> /dev/null; then
    echo -e "${RED}❌ Python3 venv module is not available${NC}"
    echo ""
    echo -e "${YELLOW}💡 To fix this on Debian/Ubuntu systems, run:${NC}"
    echo -e "${BLUE}   sudo apt install python3-venv${NC}"
    echo ""
    echo -e "${YELLOW}💡 Or on other systems, install the python3-venv package${NC}"
    echo ""
    echo "After installing, run this script again."
    exit 1
fi

# Check if we're already in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${YELLOW}⚠️  You are already in a virtual environment: $VIRTUAL_ENV${NC}"
    echo "Deactivating current environment..."
    deactivate
fi

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}🔄 Removing existing virtual environment...${NC}"
    rm -rf venv
fi

# Create new virtual environment
echo -e "${BLUE}📦 Creating virtual environment...${NC}"
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to create virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment created successfully${NC}"

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to activate virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Upgrade pip
echo -e "${BLUE}⬆️  Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}📚 Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, skipping dependency installation${NC}"
fi

# Verify installation
echo -e "${BLUE}🔍 Verifying installation...${NC}"
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Check if playwright is installed
if python -c "import playwright" 2>/dev/null; then
    echo -e "${GREEN}✅ Playwright is installed${NC}"
    
    # Install playwright browsers
    echo -e "${BLUE}🌐 Installing Playwright browsers...${NC}"
    playwright install
    
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠️  Failed to install Playwright browsers${NC}"
        echo "You may need to install them manually later with: playwright install"
    else
        echo -e "${GREEN}✅ Playwright browsers installed${NC}"
    fi
else
    echo -e "${RED}❌ Playwright is not installed${NC}"
fi

# Check if beautifulsoup4 is installed
if python -c "import bs4" 2>/dev/null; then
    echo -e "${GREEN}✅ BeautifulSoup4 is installed${NC}"
else
    echo -e "${RED}❌ BeautifulSoup4 is not installed${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "1. To activate the virtual environment manually: ${YELLOW}source venv/bin/activate${NC}"
echo "2. To run tests: ${YELLOW}./run_tests.sh --test-file [your_test_file.html] --browsers chromium${NC}"
echo "3. To deactivate when done: ${YELLOW}deactivate${NC}"
echo ""
echo -e "${BLUE}💡 Note: The run_tests.sh script will automatically use this virtual environment${NC}"
echo -e "${BLUE}   if it exists, so you don't need to manually activate it each time.${NC}"
echo ""

# Deactivate the virtual environment
deactivate
echo -e "${GREEN}✅ Virtual environment setup complete and deactivated${NC}"
