import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

SERVICE_NAME = "reportes-api"

REQUEST_COUNT = Counter(
    "minimarket_reportes_requests_total",
    "Total de peticiones HTTP en servicio de reportes",
    ["service", "method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "minimarket_reportes_request_duration_seconds",
    "Duración de peticiones de reportes en segundos",
    ["service", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/metrics", "/health", "/ready"]:
            return await call_next(request)

        start_time = time.time()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = max(time.time() - start_time, 0.0001)
            endpoint = request.url.path
            REQUEST_LATENCY.labels(service=SERVICE_NAME, endpoint=endpoint).observe(duration)
            REQUEST_COUNT.labels(
                service=SERVICE_NAME,
                method=request.method,
                endpoint=endpoint,
                status_code=str(status_code),
            ).inc()

        return response


def metrics_endpoint():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
