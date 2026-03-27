from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

IMAGE_PROXY_MAX_BYTES = 5 * 1024 * 1024
IMAGE_PROXY_ALLOWED_HOSTS = {"res.wx.qq.com"}
IMAGE_PROXY_ALLOWED_HOST_SUFFIXES = (".qpic.cn", ".qlogo.cn", ".weixin.qq.com")


class ImageProxyRequestError(ValueError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def validate_image_proxy_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    hostname = (parsed.hostname or "").lower()

    if parsed.scheme != "https" or not hostname:
        raise ImageProxyRequestError(400, "unsupported image url")

    if hostname in IMAGE_PROXY_ALLOWED_HOSTS:
        return parsed.geturl()

    if hostname.endswith(IMAGE_PROXY_ALLOWED_HOST_SUFFIXES):
        return parsed.geturl()

    raise ImageProxyRequestError(400, "unsupported image url")


def read_image_proxy_response(response: Any) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            parsed_length = int(content_length)
        except ValueError:
            parsed_length = None
        if parsed_length is not None and parsed_length > IMAGE_PROXY_MAX_BYTES:
            raise ImageProxyRequestError(413, "image too large")

    data = response.read(IMAGE_PROXY_MAX_BYTES + 1)
    if len(data) > IMAGE_PROXY_MAX_BYTES:
        raise ImageProxyRequestError(413, "image too large")
    return data
