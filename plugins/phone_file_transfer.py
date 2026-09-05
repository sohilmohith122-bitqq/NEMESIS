"""
NEMESIS Plugin - Phone File Transfer
Transfer files between phone and computer over WiFi.
Uses legitimate HTTP server on computer, phone connects via browser.
"""

import http.server
import threading
import socket
import json
from pathlib import Path
from urllib.parse import unquote

PLUGIN = {
    "name": "phone_file_transfer",
    "description": (
        "Transfer files between your phone and computer over WiFi. "
        "Starts a temporary web server on your computer. "
        "Phone connects via browser to upload/download files."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "start | stop | status",
            },
            "port": {
                "type": "INTEGER",
                "description": "Port number (default: 8888)",
            },
        },
        "required": ["action"],
    },
}

_server = None
_server_thread = None
_upload_dir = Path.home() / "Desktop" / "Phone_Transfers"

class TransferHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for phone file transfer."""
    
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self._get_upload_page().encode())
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == "/upload":
            content_length = int(self.headers["Content-Length"])
            content_type = self.headers["Content-Type"]
            
            # Parse multipart form data
            boundary = content_type.split("boundary=")[1].encode()
            body = self.rfile.read(content_length)
            
            # Simple multipart parser
            files = self._parse_multipart(body, boundary)
            
            saved_files = []
            for filename, file_data in files:
                if filename:
                    # Sanitize filename
                    safe_name = Path(filename).name
                    filepath = _upload_dir / safe_name
                    
                    # Save file
                    with open(filepath, "wb") as f:
                        f.write(file_data)
                    saved_files.append(str(filepath))
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "files": saved_files}).encode())
        else:
            self.send_error(404)
    
    def _parse_multipart(self, body, boundary):
        """Simple multipart parser."""
        files = []
        parts = body.split(b"--" + boundary)
        
        for part in parts[1:]:  # Skip first empty part
            if b"Content-Disposition" in part:
                header_end = part.find(b"\r\n\r\n")
                if header_end != -1:
                    header = part[:header_end].decode("utf-8", errors="ignore")
                    data = part[header_end + 4:]
                    
                    # Remove trailing boundary marker
                    if data.endswith(b"\r\n"):
                        data = data[:-2]
                    
                    # Extract filename
                    if 'filename="' in header:
                        filename = header.split('filename="')[1].split('"')[0]
                        files.append((filename, data))
        
        return files
    
    def _get_upload_page(self):
        """Generate upload page HTML."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>NEMESIS File Transfer</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #00ff41;
            margin: 40px;
            text-align: center;
        }}
        h1 {{ text-shadow: 0 0 10px rgba(0,255,65,0.5); }}
        .upload-zone {{
            border: 2px dashed #00ff41;
            padding: 40px;
            margin: 20px auto;
            max-width: 400px;
            cursor: pointer;
        }}
        .upload-zone:hover {{ background: rgba(0,255,65,0.1); }}
        input[type="file"] {{ display: none; }}
        button {{
            background: #00ff41;
            color: #000;
            border: none;
            padding: 10px 30px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            cursor: pointer;
            margin: 10px;
        }}
        button:hover {{ box-shadow: 0 0 15px rgba(0,255,65,0.5); }}
        #status {{ margin-top: 20px; color: #00aa2a; }}
    </style>
</head>
<body>
    <h1>NEMESIS FILE TRANSFER</h1>
    <p>Upload files from your phone to this computer</p>
    
    <div class="upload-zone" onclick="document.getElementById('files').click()">
        <p>📱 TAP TO SELECT FILES</p>
        <input type="file" id="files" multiple onchange="uploadFiles(this.files)">
    </div>
    
    <button onclick="document.getElementById('files').click()">SELECT FILES</button>
    
    <div id="status"></div>
    
    <script>
        async function uploadFiles(files) {{
            const status = document.getElementById('status');
            status.textContent = 'Uploading...';
            
            const formData = new FormData();
            for (let file of files) {{
                formData.append('files', file);
            }}
            
            try {{
                const response = await fetch('/upload', {{
                    method: 'POST',
                    body: formData
                }});
                const result = await response.json();
                
                if (result.ok) {{
                    status.textContent = `✓ Uploaded ${{result.files.length}} file(s) successfully!`;
                    status.style.color = '#00ff41';
                }} else {{
                    status.textContent = '✗ Upload failed';
                    status.style.color = '#ff0040';
                }}
            }} catch (e) {{
                status.textContent = '✗ Error: ' + e.message;
                status.style.color = '#ff0040';
            }}
        }}
    </script>
</body>
</html>"""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

def _get_local_ip():
    """Get local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def run(parameters: dict, player=None, session_memory=None) -> str:
    """Main plugin entry point."""
    global _server, _server_thread
    
    action = parameters.get("action", "status").lower()
    port = parameters.get("port", 8888)
    
    if action == "start":
        if _server and _server_thread and _server_thread.is_alive():
            return "File transfer server already running."
        
        # Create upload directory
        _upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Start server
        try:
            _server = http.server.HTTPServer(("0.0.0.0", port), TransferHandler)
            _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
            _server_thread.start()
            
            local_ip = _get_local_ip()
            return (
                f"📱 File Transfer Server Started!\n\n"
                f"Open this URL on your phone's browser:\n"
                f"http://{local_ip}:{port}\n\n"
                f"Files will be saved to:\n{_upload_dir}\n\n"
                f"Use 'phone_file_transfer action=stop' to shutdown."
            )
        except Exception as e:
            return f"Failed to start server: {e}"
    
    elif action == "stop":
        if _server:
            _server.shutdown()
            _server = None
            _server_thread = None
            return "File transfer server stopped."
        return "No server running."
    
    elif action == "status":
        if _server and _server_thread and _server_thread.is_alive():
            local_ip = _get_local_ip()
            return f"Server running at http://{local_ip}:{port}"
        return "Server not running."
    
    else:
        return (
            "Phone File Transfer Actions:\n"
            "• start - Start file transfer server (optional: port=8888)\n"
            "• stop - Stop server\n"
            "• status - Check server status\n\n"
            "How to use:\n"
            "1. Run 'start' to launch server\n"
            "2. Open the URL on your phone browser\n"
            "3. Upload files from phone to computer"
        )
