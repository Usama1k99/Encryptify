import http.server
import socketserver
import os
import sys

PORT = 3000

class CleanURLHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        file_path = super().translate_path(path)
        if os.path.exists(file_path):
            return file_path
        if os.path.exists(file_path + ".html"):
            return file_path + ".html"
        clean = file_path.rstrip("/\\")
        if os.path.exists(clean + ".html"):
            return clean + ".html"
        return file_path

def run():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), CleanURLHandler) as httpd:
        print(f"Encryptify Dev Server running at http://localhost:{port}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    run()
