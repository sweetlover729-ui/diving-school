"""
CORS 中间件配置
"""
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import logging

logger = logging.getLogger(__name__)

# 允许的 origins（生产环境应配置具体域名）
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "https://diving.alautoai.cn",
    "https://www.diving.alautoai.cn",
]


def setup_cors(app):
    """配置 CORS"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Range", "X-Content-Range"],
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的速率限制中间件"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next):
        # 简单实现：基于 IP 的限流
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # 清理过期记录
        self.requests = {
            ip: times 
            for ip, times in self.requests.items()
            if current_time - times[-1] < 60
        }
        
        # 检查请求数
        if client_ip in self.requests:
            recent_requests = [t for t in self.requests[client_ip] if current_time - t < 60]
            if len(recent_requests) >= self.requests_per_minute:
                return Response(
                    content="Too many requests",
                    status_code=429,
                    headers={"Retry-After": "60"}
                )
            self.requests[client_ip] = recent_requests + [current_time]
        else:
            self.requests[client_ip] = [current_time]
        
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 记录日志
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} "
            f"- {response.status_code} - {process_time:.3f}s"
        )
        
        return response
