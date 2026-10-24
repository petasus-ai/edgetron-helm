"""
 Copyright 2026-present SK Telecom
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
     http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

The pull agent: how far a node's containerd has come pulling an image.

A catalog or bundle image is pulled by the node (CDI's pullMethod node), not
by the importer pod, and Kubernetes says only when the pull started and when
it ended. containerd keeps what it is downloading in its content store: each
layer in flight under ingest/<id>/ (`ref` names the layer, `total` its size,
`data` holds what has come), each finished one as blobs/sha256/<hex>, and
the image's manifest (and index) as blobs before any layer. So an agent on
every node (a DaemonSet), with the content store mounted read-only, can say
how much of an image has come: it reads the manifest for the layers and
their sizes, and looks only at the sizes of the layers, never their content.

    python3 pull_agent.py

edgetron-helm runs this same file on every node from a ConfigMap
(files/pull-agent.py) on a stock Python image: node DaemonSets pull public
images only, and edgetron's image comes from a private registry. Keep the
two copies the same.

GET /pull?digest=sha256:<hex> answers {found, total, bytes, layers, done,
active, completed_at}: found false while containerd holds no manifest of
that digest; completed_at (epoch seconds) once every layer has come, when
containerd goes on to unpack them. GET /healthz answers ok.

Only the standard library is used, and nothing is written.
"""
import json
import logging
import os
import platform
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

CONTENT_ENV = "PULL_AGENT_CONTENT"
PORT_ENV = "PULL_AGENT_PORT"
DEFAULT_CONTENT = "/containerd-content"
DEFAULT_PORT = 8095
# A manifest or an index is a small JSON document; anything larger is not one.
MANIFEST_LIMIT = 4 * 1024 * 1024

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
REF_DIGEST = re.compile(r"(sha256:[0-9a-f]{64})")
INDEX_TYPES = ("application/vnd.oci.image.index.v1+json",
               "application/vnd.docker.distribution.manifest.list.v2+json")
# The node's architecture as an image platform names it.
ARCHES = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}


def node_arch() -> str:
    machine = platform.machine().lower()
    return ARCHES.get(machine, machine)


def blob_path(root: str, digest: str) -> Optional[str]:
    """Where containerd keeps a blob; None for anything but a sha256 digest."""
    if not DIGEST.match(digest or ""):
        return None
    return os.path.join(root, "blobs", "sha256", digest.split(":", 1)[1])


def _read_json(root: str, digest: str) -> Optional[Dict[str, Any]]:
    path = blob_path(root, digest)
    if not path:
        return None
    try:
        if os.path.getsize(path) > MANIFEST_LIMIT:
            return None
        with open(path, "rb") as f:
            return json.loads(f.read())
    except (OSError, ValueError):
        return None


def layers_of(root: str, digest: str, arch: str) -> Optional[List[Tuple[str, int]]]:
    """
    The layers of the image a digest names, with their sizes: a manifest's
    own, or for an index the manifest of the node's platform.
    :return     [(digest, size)]; None while containerd holds no such manifest
    """
    document = _read_json(root, digest)
    if document is None:
        return None
    if document.get("mediaType") in INDEX_TYPES or "manifests" in document:
        chosen = None
        for item in document.get("manifests") or []:
            target = item.get("platform") or {}
            if target.get("os", "linux") == "linux" and target.get("architecture") == arch:
                chosen = item.get("digest")
                break
        if not chosen:
            return None
        document = _read_json(root, chosen)
        if document is None:
            return None
    layers = []
    for layer in document.get("layers") or []:
        if DIGEST.match(layer.get("digest") or "") and isinstance(layer.get("size"), int):
            layers.append((layer["digest"], layer["size"]))
    return layers


def in_flight(root: str) -> Dict[str, Tuple[int, int]]:
    """The layers being downloaded now: digest -> (bytes come, total)."""
    found: Dict[str, Tuple[int, int]] = {}
    ingest = os.path.join(root, "ingest")
    try:
        entries = os.listdir(ingest)
    except OSError:
        return found
    for entry in entries:
        base = os.path.join(ingest, entry)
        try:
            with open(os.path.join(base, "ref")) as f:
                match = REF_DIGEST.search(f.read())
            if not match:
                continue
            size = os.path.getsize(os.path.join(base, "data"))
            total = 0
            try:
                with open(os.path.join(base, "total")) as f:
                    total = int(f.read().strip() or 0)
            except (OSError, ValueError):
                pass
            found[match.group(1)] = (size, total)
        except OSError:
            continue
    return found


def progress(root: str, digest: str, arch: Optional[str] = None) -> Dict[str, Any]:
    """How much of the image a digest names has come to this node."""
    layers = layers_of(root, digest, arch or node_arch())
    if layers is None:
        return {"found": False}
    active = in_flight(root)
    answer = {"found": True, "total": 0, "bytes": 0, "layers": len(layers), "done": 0, "active": 0}
    newest = 0.0
    for layer, size in layers:
        answer["total"] += size
        path = blob_path(root, layer)
        try:
            stat = os.stat(path)
            answer["bytes"] += size
            answer["done"] += 1
            newest = max(newest, stat.st_mtime)
            continue
        except OSError:
            pass
        if layer in active:
            answer["bytes"] += min(active[layer][0], size)
            answer["active"] += 1
    if layers and answer["done"] == len(layers):
        answer["completed_at"] = newest
    return answer


class _Handler(BaseHTTPRequestHandler):
    root = DEFAULT_CONTENT

    def _send(self, status: int, body: Dict[str, Any]):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802 - the http.server name
        url = urlparse(self.path)
        if url.path == "/healthz":
            self._send(200, {"ok": True})
            return
        if url.path != "/pull":
            self._send(404, {"error": "not found"})
            return
        digest = (parse_qs(url.query).get("digest") or [""])[0]
        if not DIGEST.match(digest):
            self._send(400, {"error": "digest must be sha256:<64 hex>"})
            return
        self._send(200, progress(self.root, digest))

    def log_message(self, fmt, *args):
        logging.debug("pull agent: " + fmt, *args)


def serve(root: str, port: int):
    handler = type("Handler", (_Handler,), {"root": root})
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    logging.info("pull agent: reading %s, listening on %s", root, port)
    server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve(os.environ.get(CONTENT_ENV, DEFAULT_CONTENT), int(os.environ.get(PORT_ENV, DEFAULT_PORT)))
