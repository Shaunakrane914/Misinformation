"""Conservative retrieval identity; raw URLs/text/IDs remain in observations."""
import hashlib
from urllib.parse import urlsplit, urlunsplit


def source_url_key(url):
    try:
        p = urlsplit(url or "")
        if not p.hostname or p.username or p.password:
            return url
        host = p.hostname.lower()
        port = p.port
        if port and not (p.scheme == "https" and port == 443 or p.scheme == "http" and port == 80):
            host += ":" + str(port)
        return urlunsplit((p.scheme.lower(), host, p.path or "/", p.query, ""))
    except ValueError:
        return url


def unique_captures(items, audit):
    urls, bodies, retained = {}, {}, []
    for item in items:
        key = source_url_key(item.canonical_url)
        # Exact substantive captured bytes only; no fuzzy merging of claims.
        body = hashlib.sha256(item.content.encode()).hexdigest() if len(item.content or "") >= 100 else None
        original = urls.get(key) or (bodies.get(body) if body else None)
        if original:
            item.metadata["duplicate_of"] = original.id
            original.metadata.setdefault("duplicate_observation_ids", []).append(item.id)
            audit.append({"duplicate_id": item.id, "retained_id": original.id,
                          "reason": "CANONICAL_URL" if key in urls else "IDENTICAL_CAPTURE"})
            continue
        urls[key] = item
        if body:
            bodies[body] = item
        retained.append(item)
    return retained
