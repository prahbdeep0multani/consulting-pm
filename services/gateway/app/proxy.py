import httpx
from fastapi import Request
from fastapi.responses import Response

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


async def proxy_request(
    request: Request,
    upstream_url: str,
    http_client: httpx.AsyncClient,
) -> Response:
    path = request.url.path
    query = request.url.query
    target = f"{upstream_url}{path}" + (f"?{query}" if query else "")

    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}

    # Inject user context from gateway's JWT validation
    if hasattr(request.state, "user_id"):
        headers["X-User-ID"] = request.state.user_id
        headers["X-Tenant-ID"] = request.state.tenant_id
        headers["X-User-Roles"] = ",".join(request.state.roles)

    if hasattr(request.state, "correlation_id"):
        headers["X-Correlation-ID"] = request.state.correlation_id

    body = await request.body()

    upstream_resp = await http_client.request(
        method=request.method,
        url=target,
        headers=headers,
        content=body,
        follow_redirects=False,
    )

    response_headers = {
        k: v for k, v in upstream_resp.headers.items() if k.lower() not in _HOP_BY_HOP
    }
    response_headers["X-Correlation-ID"] = headers.get("X-Correlation-ID", "")

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=response_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )
