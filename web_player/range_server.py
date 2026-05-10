import http.server
import socketserver
import os
import re
import sys

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    自定義伺服器處理程式，支援 HTTP Range 請求。
    這是讓 HTML5 Audio 能夠進行「進度條跳轉」的核心技術。
    """
    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        
        if not os.path.exists(path):
            return super().send_head()

        # 取得請求中的 Range 標頭
        range_header = self.headers.get('Range')
        if not range_header or not range_header.startswith('bytes='):
            return super().send_head()
        
        try:
            size = os.path.getsize(path)
            # 解析範圍，例如 bytes=0- 或 bytes=100-2000
            m = re.match(r'bytes=(\d+)-(\d+)?', range_header)
            if not m:
                return super().send_head()
            
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else size - 1
            
            if start >= size:
                self.send_error(416, 'Requested Range Not Satisfiable')
                return None
            
            # 限制範圍
            end = min(end, size - 1)
            content_length = end - start + 1
            
            # 發送 206 Partial Content 回應
            self.send_response(206)
            self.send_header('Content-Type', self.guess_type(path))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.send_header('Content-Length', str(content_length))
            self.send_header('Last-Modified', self.date_time_string(os.path.getmtime(path)))
            self.end_headers()
            
            f = open(path, 'rb')
            f.seek(start)
            return f
        except Exception as e:
            print(f"Error handling range request: {e}")
            return super().send_head()

if __name__ == "__main__":
    # 強制使用當前目錄
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    PORT = 8000
    # 解決端口被佔用的問題
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer(("", PORT), RangeRequestHandler) as httpd:
            print("--------------------------------------------------")
            print("   AURORA MUSIC PLAYER - PRO SERVER ACTIVE")
            print(f"   網址: http://localhost:{PORT}")
            print("   (支援進度條跳轉、SRT/LRC 自動讀取)")
            print("--------------------------------------------------")
            print("按 Ctrl+C 可停止伺服器")
            httpd.serve_forever()
    except Exception as e:
        print(f"無法啟動伺服器: {e}")
        input("按任意鍵退出...")
