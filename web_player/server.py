import http.server
import socketserver
import os
import urllib.parse
import shutil
import re

# 定義虛擬下載目錄 (指向專案根目錄外的 downloads)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "../../downloads"))

class AuroraHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 處理虛擬路徑 /downloads/
        if self.path.startswith('/downloads/'):
            # 解碼 URL (處理空白字元等)
            rel_path = urllib.parse.unquote(self.path[11:])
            local_path = os.path.join(DOWNLOADS_PATH, rel_path)
            
            if os.path.exists(local_path) and os.path.isfile(local_path):
                self.serve_file_with_range(local_path)
                return
            else:
                self.send_error(404, "File not found")
                return
        
        # 其他路徑交給原有的處理器 (index.html, index.js 等)
        return super().do_GET()

    def serve_file_with_range(self, file_path):
        """核心技術：支援 HTTP Range 請求，讓進度條可以跳轉"""
        size = os.path.getsize(file_path)
        content_type = self.guess_type(file_path)
        
        range_header = self.headers.get('Range')
        if range_header:
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = match.group(2)
                end = int(end) if end else size - 1
                
                if start >= size:
                    self.send_error(416, "Requested Range Not Satisfiable")
                    return

                length = end - start + 1
                self.send_response(206) # Partial Content
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                self.send_header('Content-Length', str(length))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                
                with open(file_path, 'rb') as f:
                    f.seek(start)
                    # 傳送指定區段
                    shutil.copyfileobj(io_bytes_wrapper(f.read(length)), self.wfile)
                return

        # 如果沒有 Range 要求，正常傳送全檔
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(size))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        with open(file_path, 'rb') as f:
            shutil.copyfileobj(f, self.wfile)

# 輔助工具：處理內容傳輸
def io_bytes_wrapper(data):
    import io
    return io.BytesIO(data)

if __name__ == '__main__':
    PORT = 8888
    # 這裡主要是給 start_player.py 調用的邏輯，如果是單獨執行：
    with socketserver.TCPServer(("", PORT), AuroraHandler) as httpd:
        print(f"Aurora Server running on port {PORT}")
        httpd.serve_forever()
