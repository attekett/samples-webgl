
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.firefox.launch()
        page = await browser.new_page()
        
        # This is a bit tricky since we can't easily get the gl context from JS and return it to Python
        # but we can print it to the console.
        page.on("console", lambda msg: print(msg.text))
        
        await page.evaluate("""() => {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
            if (gl) {
                console.log('WEBGL_RENDERER: ' + gl.getParameter(gl.RENDERER));
                console.log('WEBGL_VERSION: ' + gl.getParameter(gl.VERSION));
                const exts = gl.getSupportedExtensions();
                console.log('EXTENSIONS: ' + exts.join(', '));
            } else {
                console.log('WebGL not supported');
            }
        }""")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
