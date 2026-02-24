import http.server
import socketserver
import subprocess
import os
import time
import sys
import threading

PORT = 8888
received_data = None

class ReportHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global received_data
        if self.path.startswith('/report'):
            received_data = self.path.split('data=')[-1]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return # Silence logs

def start_server():
    with socketserver.TCPServer(("127.0.0.1", PORT), ReportHandler) as httpd:
        httpd.handle_request() # Handle one request and exit

print(f"--- Starting WebGL Feedback Listener on port {PORT} ---")
server_thread = threading.Thread(target=start_server)
server_thread.daemon = True # Ensure exit
server_thread.start()

# Launch Firefox
print("Launching Firefox for WebGL check...")
env = os.environ.copy()
libasan = subprocess.check_output(['find', '/usr/lib', '-name', 'libasan.so.8']).decode().strip()
env['LD_PRELOAD'] = libasan
env['DISPLAY'] = ':1'
# Log ASAN to /results
env['ASAN_OPTIONS'] = 'log_path=/results/firefox-asan.log:detect_leaks=0:abort_on_error=1'

cmd = [
    'firefox',
    '--headless',
    '--new-instance',
    'file:///fuzz/webgl-info.html?report=http://127.0.0.1:8888/report'
]

# We don't use DEVNULL so we might see something in the logs if it prints to stderr
proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# Function to read output in background
def pipe_reader(pipe, label):
    for line in pipe:
        print(f"[{label}] {line.strip()}")

threading.Thread(target=pipe_reader, args=(proc.stdout, "FF-OUT"), daemon=True).start()
threading.Thread(target=pipe_reader, args=(proc.stderr, "FF-ERR"), daemon=True).start()

# Wait for data
start_time = time.time()
while received_data is None and time.time() - start_time < 30:
    time.sleep(0.5)

if received_data:
    import urllib.parse
    decoded = urllib.parse.unquote(received_data)
    print("\n[SUCCESS] Firefox reported WebGL Status:")
    print(decoded)
else:
    print("\n[ERROR] Timed out waiting for Firefox to report WebGL status.")
    # Check for asan logs
    asan_logs = [f for f in os.listdir('/results') if 'firefox-asan.log' in f]
    if asan_logs:
        print(f"Found ASAN logs: {asan_logs}")
        with open(os.path.join('/results', asan_logs[0]), 'r') as f:
            print("--- ASAN LOG CONTENT ---")
            print(f.read())
    else:
        print("No ASAN logs found. Firefox might be hanging or failing at a lower level.")

# Cleanup
proc.terminate()
time.sleep(1)
proc.kill()
sys.exit(0 if received_data else 1)
