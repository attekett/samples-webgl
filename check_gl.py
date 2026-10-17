import asyncio
import sys
from playwright.async_api import async_playwright

OUT_PATH = 'docs/browser_webgl_info.txt'

PROBE_JS = """
    (browserLabel) => {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
        if (!gl) {
            console.log('WebGL not supported');
            return;
        }
        console.log('=== ' + browserLabel + ' ===');
        console.log('WEBGL_RENDERER: ' + gl.getParameter(gl.RENDERER));
        console.log('WEBGL_VENDOR: ' + gl.getParameter(gl.VENDOR));
        console.log('WEBGL_VERSION: ' + gl.getParameter(gl.VERSION));
        console.log('GLSL_VERSION: ' + gl.getParameter(gl.SHADING_LANGUAGE_VERSION));
        const exts = gl.getSupportedExtensions() || [];
        console.log('EXTENSION_COUNT: ' + exts.length);
        console.log('EXTENSIONS: ' + exts.join(' '));
        const limits = {};
        ['MAX_TEXTURE_SIZE', 'MAX_CUBE_MAP_TEXTURE_SIZE', 'MAX_3D_TEXTURE_SIZE',
         'MAX_ARRAY_TEXTURE_LAYERS', 'MAX_RENDERBUFFER_SIZE', 'MAX_VIEWPORT_DIMS',
         'MAX_VERTEX_ATTRIBS', 'MAX_TEXTURE_IMAGE_UNITS', 'MAX_COMBINED_TEXTURE_IMAGE_UNITS',
         'MAX_COLOR_ATTACHMENTS', 'MAX_DRAW_BUFFERS', 'MAX_TRANSFORM_FEEDBACK_SEPARATE_COMPONENTS']
            .forEach(k => { try { limits[k] = gl.getParameter(gl[k]); } catch(e) {} });
        console.log('LIMITS: ' + JSON.stringify(limits));
    }
"""

async def probe(p, browser_name, launch):
    try:
        browser = await launch()
    except Exception as e:
        return f"=== {browser_name} ===\nLAUNCH_FAILED: {e}\n"
    page = await browser.new_page()
    lines = []
    page.on("console", lambda msg: lines.append(msg.text))
    await page.evaluate(PROBE_JS, browser_name)
    await browser.close()
    return "\n".join(lines) + "\n"

async def main():
    out = sys.argv[1] if len(sys.argv) > 1 else OUT_PATH
    async with async_playwright() as p:
        ff = await probe(p, 'Firefox', p.firefox.launch)
        cr = await probe(p, 'Chromium', p.chromium.launch)
    text = ff + "\n" + cr
    with open(out, 'w') as f:
        f.write(text)
    print(text)

if __name__ == "__main__":
    asyncio.run(main())
