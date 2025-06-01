from requests import Request, Response
from requests.sessions import Session

class ResponseCache:
    def __init__(self):
        self.cache: dict[Request, Response] = {}

    def __contains__(self, req: Request):
        return req in self.cache

    def invalidate(self, req: Request):
        self.cache.pop(req, None)

    def send(self, req: Request, use_cached: bool = True):
        if not use_cached or req not in self:
            self.cache[req] = Session().send(req.prepare())
        return self.cache[req]
