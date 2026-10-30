#!/usr/bin/env python3
"""MCP server (stdio, JSON-RPC 2.0 by hand: the `mcp` package is not installed in python3.14) over one polish Session (PIPELINE 31.L13-1).

    python3.14 tools/blender/polish_mcp.py --run <run dir> --id <id> [--budget-min 5] [--max-ops 12] [--rig spider] [--sheet <sheet.jpg>]

Tools: state, views, inspect(view, region), apply(python_code, why), done(summary). Newline-delimited JSON on stdin / stdout; every
tool error comes back as a result with isError, never as a crash. Headless: no Blender and no UI (polish_ops edits the GLB bytes).
"""
import argparse
import json
import pathlib
import sys
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import polish  # noqa: E402

PROTOCOL = "2025-06-18"
STR = {"type": "string"}
TOOLS = [
    {"name": "state", "description": "Parts (bone, vertices, bbox as fractions of H), tris, the per-view table (spill/bare/iou/contact), start table, gate, budget left.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "views", "description": "Writes the 6 overlays of the CURRENT state (yellow both, RED model outside the sheet, green sheet uncovered; spill % in the "
     "file name) plus all.png (the six together) and returns their paths: open them with Read.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "inspect", "description": "Magnified crop (x4) of one view's overlay. region = 'x0,y0,x1,y1' in canvas px (panel is 384 x 256) or a part name (bone).",
     "inputSchema": {"type": "object", "required": ["view", "region"], "properties": {"view": STR, "region": STR}}},
    {"name": "apply", "description": "Run Python on the clay (see the brief for `scene` and the helpers), re-measure the gate, revert by itself when a view gets worse. "
     "Returns accepted/rejected with the reason, the new table and the delta per view. dry_run=true: only say what the gate would say, spend no op.",
     "inputSchema": {"type": "object", "required": ["python_code", "why"], "properties": {"python_code": STR, "why": STR, "dry_run": {"type": "boolean"}}}},
    {"name": "done", "description": "Finish the session with a one-paragraph summary of what you changed and what is still red.",
     "inputSchema": {"type": "object", "required": ["summary"], "properties": {"summary": STR}}},
]


def call(session, name, args):
    if name == "state":
        return session.state()
    if name == "views":
        return session.views()
    if name == "inspect":
        return {"path": session.inspect(args["view"], args["region"])}
    if name == "apply":
        return session.apply(args["python_code"], args["why"], bool(args.get("dry_run")))
    if name == "done":
        session.done_summary = args["summary"]
        session.save()
        return {"result": "done", "accepted_ops": len(session.accepted())}
    raise KeyError(f"unknown tool {name}")


def handle(session, msg):
    """`session` is a function returning the Session: it is built on the first tools/call (the start measures the gate, seconds the
    handshake must not wait for). The reply to one JSON-RPC message, or None for a notification."""
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None
    if method == "initialize":
        result = {"protocolVersion": (msg.get("params") or {}).get("protocolVersion", PROTOCOL), "capabilities": {"tools": {}},
                  "serverInfo": {"name": "polish", "version": "1"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        p = msg.get("params") or {}
        try:
            out = call(session(), p.get("name"), p.get("arguments") or {})
            result = {"content": [{"type": "text", "text": json.dumps(out, indent=1)}], "isError": False}
        except Exception as err:            # a bad argument or a failed op is the agent's to read, not a crash
            result = {"content": [{"type": "text", "text": f"{type(err).__name__}: {err}\n{traceback.format_exc(limit=-3)}"}], "isError": True}
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def serve(session, stdin=sys.stdin, stdout=sys.stdout):
    for line in stdin:
        if not line.strip():
            continue
        try:
            reply = handle(session, json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=pathlib.Path, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--budget-min", type=float, default=5.0)
    ap.add_argument("--max-ops", type=int, default=12)
    ap.add_argument("--rig", default=None)
    ap.add_argument("--sheet", default=None)
    a = ap.parse_args()
    cell = []

    def session():
        if not cell:
            cell.append(polish.Session(a.run, a.id, a.sheet, a.rig, budget_min=a.budget_min, max_ops=a.max_ops))
        return cell[0]
    serve(session)


if __name__ == "__main__":
    main()
