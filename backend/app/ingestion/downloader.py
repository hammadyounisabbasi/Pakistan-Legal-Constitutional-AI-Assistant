import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

ALLOWED_HOSTS = {
    "na.gov.pk", "www.na.gov.pk", "pakistancode.gov.pk", "www.pakistancode.gov.pk",
    "senate.gov.pk", "www.senate.gov.pk", "supremecourt.gov.pk", "www.supremecourt.gov.pk",
    "federalshariatcourt.gov.pk", "www.federalshariatcourt.gov.pk",
    "lhc.gov.pk", "www.lhc.gov.pk", "sindhhighcourt.gov.pk", "www.sindhhighcourt.gov.pk",
    "peshawarhighcourt.gov.pk", "www.peshawarhighcourt.gov.pk", "bhc.gov.pk", "www.bhc.gov.pk",
    "mis.ihc.gov.pk", "ihc.gov.pk", "www.ihc.gov.pk", "molaw.gov.pk", "www.molaw.gov.pk",
}


@dataclass(slots=True)
class Downloaded:
    content: bytes
    content_type: str
    final_url: str


class SafeDownloader:
    def __init__(self, user_agent: str, timeout: float, max_bytes: int, delay: float):
        self.headers = {"User-Agent": user_agent, "Accept": "text/html,application/pdf,text/plain"}
        self.timeout, self.max_bytes, self.delay = timeout, max_bytes, delay

    @staticmethod
    def validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.hostname.casefold() not in ALLOWED_HOSTS:
            raise ValueError("URL is not an allow-listed HTTPS official source")
        for info in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
            address = ipaddress.ip_address(info[4][0])
            if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
                raise ValueError("Source resolved to a non-public address")

    async def fetch(self, url: str) -> Downloaded:
        self.validate_url(url)
        await asyncio.sleep(max(0, self.delay))
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False, headers=self.headers) as client:
            current = url
            for attempt in range(3):
                try:
                    response = await client.get(current)
                    if response.is_redirect:
                        target = str(response.next_request.url)
                        self.validate_url(target)
                        current = target
                        continue
                    response.raise_for_status()
                    if len(response.content) > self.max_bytes:
                        raise ValueError("Document exceeds configured maximum size")
                    return Downloaded(response.content, response.headers.get("content-type", ""), current)
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)
            raise RuntimeError("Too many redirects")

