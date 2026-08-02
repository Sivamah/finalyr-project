"""Phase 9 — Security & Logging Middleware"""

import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aiorch")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Enable XSS filtering in browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Strict Transport Security (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Content Security Policy (Basic API restriction)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Incoming request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Log response metrics
        process_time = (time.time() - start_time) * 1000
        logger.info(f"Completed {request.method} {request.url.path} in {process_time:.2f}ms with status {response.status_code}")
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
