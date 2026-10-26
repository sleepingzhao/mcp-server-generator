"""Local web UI for MCP Server Generator."""
from __future__ import annotations
import argparse
import io
import os
import zipfile
from flask import Flask, jsonify, request, send_file, send_from_directory
from generator import SpecError, generate_project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"))
app.json.sort_keys = False
@app.before_request
def csrf_protect():
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("Origin")
        if origin and origin not in (f"http://{request.host}", f"https://{request.host}"):
            return jsonify({"ok": False, "error": "跨站请求被拒绝"}), 403
    return None
@app.get("/")
def index(): return send_from_directory(app.static_folder, "index.html")


@app.get("/favicon.ico")
def favicon(): return ("", 204)
@app.post("/api/preview")
def preview():
    try:
        project = generate_project(request.get_json(force=True))
        return jsonify({"ok": True, "slug": project.slug, "files": project.files})
    except (SpecError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
@app.post("/api/download")
def download():
    try: project = generate_project(request.get_json(force=True))
    except (SpecError, TypeError, ValueError) as exc: return jsonify({"ok": False, "error": str(exc)}), 400
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in project.files.items(): archive.writestr(f"{project.slug}/{name}", content)
    output.seek(0)
    return send_file(output, mimetype="application/zip", as_attachment=True, download_name=f"{project.slug}.zip")
def main():
    parser=argparse.ArgumentParser(description="MCP Server Generator")
    parser.add_argument("--host",default="127.0.0.1"); parser.add_argument("--port",type=int,default=5050)
    args=parser.parse_args(); print(f"MCP Server Generator: http://{args.host}:{args.port}")
    app.run(host=args.host,port=args.port,threaded=True)
if __name__ == "__main__": main()
