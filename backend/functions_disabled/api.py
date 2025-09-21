from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from mangum import Mangum

# 使用Mangum适配器将FastAPI应用转换为AWS Lambda处理程序
handler = Mangum(app)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        # 调用FastAPI应用
        response = handler(self._create_aws_event(), {})
        
        # 返回响应
        self.wfile.write(json.dumps(response).encode())
        return
    
    def _create_aws_event(self):
        # 创建一个简单的AWS Lambda事件对象
        return {
            "path": self.path,
            "httpMethod": self.command,
            "headers": dict(self.headers),
            "queryStringParameters": parse_qs(self.path.split("?")[1] if "?" in self.path else ""),
            "body": None,
            "isBase64Encoded": False,
        } 