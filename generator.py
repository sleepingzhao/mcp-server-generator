"""Generate runnable Python MCP server projects from a declarative specification."""
from __future__ import annotations

import json
import keyword
import re
from dataclasses import dataclass
from typing import Any

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TOOL_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
TYPE_MAP = {"string": "str", "integer": "int", "number": "float", "boolean": "bool", "array": "list[Any]", "object": "dict[str, Any]"}

class SpecError(ValueError):
    """Raised when a project specification is invalid."""

@dataclass(frozen=True)
class GeneratedProject:
    slug: str
    files: dict[str, str]

def _identifier(value: Any, label: str) -> str:
    value = str(value or "").strip()
    if not IDENTIFIER.fullmatch(value) or keyword.iskeyword(value):
        raise SpecError(f"{label} 必须是合法的 Python 标识符")
    return value

def _json_object(value: Any, label: str) -> dict[str, Any]:
    if value in (None, ""): return {}
    if isinstance(value, str):
        try: value = json.loads(value)
        except json.JSONDecodeError as exc: raise SpecError(f"{label} 不是合法 JSON: {exc.msg}") from exc
    if not isinstance(value, dict): raise SpecError(f"{label} 必须是 JSON 对象")
    return value

def _json_array(value: Any, label: str) -> list[Any]:
    if value in (None, ""): return []
    if isinstance(value, str):
        try: value = json.loads(value)
        except json.JSONDecodeError as exc: raise SpecError(f"{label} 不是合法 JSON: {exc.msg}") from exc
    if not isinstance(value, list): raise SpecError(f"{label} 必须是 JSON 数组")
    return value

def validate_spec(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict): raise SpecError("请求必须是 JSON 对象")
    name = str(raw.get("name") or "").strip()
    if not name or len(name) > 80: raise SpecError("项目名称不能为空且不能超过 80 字符")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "mcp-server"
    package = _identifier(raw.get("package") or slug.replace("-", "_"), "包名")
    transport = raw.get("transport", "stdio")
    if transport not in ("stdio", "streamable-http"): raise SpecError("transport 仅支持 stdio 或 streamable-http")
    tools = raw.get("tools")
    if not isinstance(tools, list) or not tools: raise SpecError("至少需要定义一个 Tool")
    if len(tools) > 50: raise SpecError("单个项目最多支持 50 个 Tools")
    seen_tools, clean_tools = set(), []
    for index, tool in enumerate(tools, 1):
        if not isinstance(tool, dict): raise SpecError(f"Tool #{index} 格式错误")
        tool_name = str(tool.get("name") or "").strip()
        if not TOOL_NAME.fullmatch(tool_name): raise SpecError(f"Tool #{index} 名称只能包含字母、数字、点、短横线和下划线")
        if tool_name in seen_tools: raise SpecError(f"Tool 名称重复: {tool_name}")
        seen_tools.add(tool_name)
        function_name = _identifier(tool_name.replace("-", "_").replace(".", "_"), f"Tool {tool_name} 函数名")
        handler = tool.get("handler", "static")
        if handler not in ("static", "http", "command"): raise SpecError(f"Tool {tool_name} 的处理器类型无效")
        params = tool.get("params") or []
        if not isinstance(params, list): raise SpecError(f"Tool {tool_name} 的参数必须是数组")
        seen_params, clean_params, optional_started = set(), [], False
        for p in params:
            if not isinstance(p, dict): raise SpecError(f"Tool {tool_name} 存在无效参数")
            p_name = _identifier(p.get("name"), f"Tool {tool_name} 参数名")
            if p_name in seen_params: raise SpecError(f"Tool {tool_name} 参数重复: {p_name}")
            seen_params.add(p_name)
            p_type = p.get("type", "string")
            if p_type not in TYPE_MAP: raise SpecError(f"参数 {p_name} 类型无效")
            required = bool(p.get("required", True))
            if not required: optional_started = True
            elif optional_started: raise SpecError(f"Tool {tool_name} 的必填参数必须排在可选参数之前")
            clean_params.append({"name": p_name, "type": p_type, "description": str(p.get("description") or ""), "required": required})
        config = tool.get("config") or {}
        if not isinstance(config, dict): raise SpecError(f"Tool {tool_name} 配置格式错误")
        if handler == "http":
            method, url = str(config.get("method") or "GET").upper(), str(config.get("url") or "").strip()
            if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"): raise SpecError(f"Tool {tool_name} HTTP 方法无效")
            if not url.startswith(("http://", "https://")): raise SpecError(f"Tool {tool_name} 需要有效的 HTTP URL")
            params_mode = str(config.get("params_mode") or "auto")
            if params_mode not in ("auto", "query", "body", "none"): raise SpecError("HTTP 参数放置方式无效")
            response_mode = str(config.get("response_mode") or "auto")
            if response_mode not in ("auto", "json", "text"): raise SpecError("HTTP 响应模式无效")
            timeout = int(config.get("timeout") or 30)
            if not 1 <= timeout <= 300: raise SpecError("HTTP 超时必须在 1 到 300 秒之间")
            config = {"method": method, "url": url, "headers": _json_object(config.get("headers"), "Headers"), "query": _json_object(config.get("query"), "Query"), "body": _json_object(config.get("body"), "Body"), "params_mode": params_mode, "response_mode": response_mode, "timeout": timeout}
        elif handler == "command":
            executable = str(config.get("executable") or "").strip()
            if not executable: raise SpecError(f"Tool {tool_name} 缺少可执行命令")
            args = _json_array(config.get("args"), "命令参数")
            if not all(isinstance(x, str) for x in args): raise SpecError("命令参数必须全部是字符串")
            timeout = int(config.get("timeout") or 30)
            if not 1 <= timeout <= 600: raise SpecError("命令超时必须在 1 到 600 秒之间")
            env = _json_object(config.get("env"), "命令环境变量")
            if not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()): raise SpecError("命令环境变量的键和值必须是字符串")
            allowed_exit_codes = _json_array(config.get("allowed_exit_codes", [0]), "允许的退出码")
            if not allowed_exit_codes or not all(isinstance(x, int) for x in allowed_exit_codes): raise SpecError("允许的退出码必须是非空整数数组")
            config = {"executable": executable, "args": args, "timeout": timeout, "cwd": str(config.get("cwd") or "").strip(), "env": env, "stdin": str(config.get("stdin") or ""), "allowed_exit_codes": allowed_exit_codes}
        else: config = {"response": config.get("response", {"ok": True})}
        clean_tools.append({"name": tool_name, "function_name": function_name, "description": str(tool.get("description") or ""), "handler": handler, "params": clean_params, "config": config})
    return {"name": name, "slug": slug, "package": package, "description": str(raw.get("description") or "Generated MCP server"), "transport": transport, "host": str(raw.get("host") or "127.0.0.1"), "port": int(raw.get("port") or 8000), "tools": clean_tools}

def _function(tool: dict[str, Any]) -> str:
    signature = []
    for p in tool["params"]:
        hint = TYPE_MAP[p["type"]]
        signature.append(f'{p["name"]}: {hint}' if p["required"] else f'{p["name"]}: {hint} | None = None')
    args_dict = ", ".join(f'"{p["name"]}": {p["name"]}' for p in tool["params"])
    doc = tool["description"].replace('"""', "") or f'Execute {tool["name"]}.'
    lines = [f'@mcp.tool(name={tool["name"]!r})', f'def {tool["function_name"]}({", ".join(signature)}) -> dict[str, Any]:', f'    """{doc}"""', f'    values = {{{args_dict}}}']
    call = {"static": "_static_call", "http": "_http_call", "command": "_command_call"}[tool["handler"]]
    lines.append(f'    return {call}({tool["config"]!r}, values)')
    return "\n".join(lines)

def _server_source(spec: dict[str, Any]) -> str:
    functions = "\n\n\n".join(_function(t) for t in spec["tools"])
    return f'''"""{spec["description"]}"""
from __future__ import annotations
import json
import os
import re
import subprocess
from typing import Any
from urllib import parse, request
from mcp.server.fastmcp import FastMCP
mcp = FastMCP({spec["name"]!r}, host={spec["host"]!r}, port={spec["port"]})

def _format_value(value: Any, values: dict[str, Any]) -> Any:
    if isinstance(value, str):
        value = re.sub(r"\$\{{ENV:([A-Za-z_][A-Za-z0-9_]*)\}}", lambda m: os.environ.get(m.group(1), ""), value)
        try: return value.format_map(values)
        except (KeyError, ValueError) as exc: raise ValueError(f"Template placeholder error: {{exc}}") from exc
    if isinstance(value, list): return [_format_value(item, values) for item in value]
    if isinstance(value, dict): return {{key: _format_value(item, values) for key, item in value.items()}}
    return value

def _static_call(config: dict[str, Any], values: dict[str, Any]) -> Any:
    return _format_value(config["response"], values)

def _http_call(config: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    method, url = config["method"], _format_value(config["url"], values)
    headers = _format_value(config.get("headers", {{}}), values)
    query = _format_value(config.get("query", {{}}), values)
    body = _format_value(config.get("body", {{}}), values)
    mode = config.get("params_mode", "auto")
    used = {{name for name in values if "{{" + name + "}}" in config["url"]}}
    remaining = {{key: value for key, value in values.items() if key not in used and value is not None}}
    if mode == "query" or (mode == "auto" and method == "GET"): query = {{**query, **remaining}}
    elif mode == "body" or (mode == "auto" and method != "GET"): body = {{**body, **remaining}}
    if query: url += ("&" if "?" in url else "?") + parse.urlencode(query, doseq=True)
    data = None
    if method != "GET" and body:
        data = json.dumps(body).encode("utf-8"); headers.setdefault("Content-Type", "application/json")
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=config.get("timeout", 30)) as response:
            raw = response.read().decode("utf-8", errors="replace")
            mode = config.get("response_mode", "auto")
            if mode == "text": payload = raw
            else:
                try: payload = json.loads(raw)
                except json.JSONDecodeError:
                    if mode == "json": raise RuntimeError("HTTP 响应不是合法 JSON")
                    payload = raw
            return {{"status": response.status, "data": payload}}
    except Exception as exc: raise RuntimeError(f"HTTP request failed: {{exc}}") from exc

def _command_call(config: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    executable = _format_value(config["executable"], values)
    args = [_format_value(item, values) for item in config.get("args", [])]
    cwd = _format_value(config.get("cwd", ""), values) or None
    extra_env = _format_value(config.get("env", {{}}), values)
    stdin = _format_value(config.get("stdin", ""), values) or None
    try: result = subprocess.run([executable, *args], input=stdin, cwd=cwd, env={{**os.environ, **extra_env}}, capture_output=True, text=True, timeout=config["timeout"], check=False)
    except (OSError, subprocess.TimeoutExpired) as exc: raise RuntimeError(f"Command failed: {{exc}}") from exc
    payload = {{"exitCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}}
    if result.returncode not in config.get("allowed_exit_codes", [0]): raise RuntimeError(f"Command exited with {{result.returncode}}: {{result.stderr.strip()}}")
    return payload

{functions}

if __name__ == "__main__":
    mcp.run(transport={spec["transport"]!r})
'''

def generate_project(raw: Any) -> GeneratedProject:
    spec = validate_spec(raw)
    source = _server_source(spec)
    config = {"mcpServers": {spec["slug"]: {"command": "python", "args": ["server.py"]}}}
    run_hint = "python server.py" if spec["transport"] == "stdio" else f'python server.py  # endpoint: http://{spec["host"]}:{spec["port"]}/mcp'
    readme = f'''# {spec["name"]}

{spec["description"]}

由 MCP Server Generator 生成，包含 {len(spec["tools"])} 个工具。

## 运行

需要 Python 3.10+：

    python -m venv .venv
    pip install -r requirements.txt
    {run_hint}

## 接入客户端

stdio 模式可把 mcp-config.json 合并到 MCP Client 配置中，并把 server.py 改为绝对路径。

## Tools

''' + "\n".join(f'- {t["name"]}：{t["description"] or "无描述"}' for t in spec["tools"]) + "\n"
    public_spec = json.loads(json.dumps(spec))
    for tool in public_spec["tools"]: tool.pop("function_name", None)
    files = {"server.py": source, "requirements.txt": "mcp[cli]>=1.9.0,<2\n", "README.md": readme, "mcp-config.json": json.dumps(config, ensure_ascii=False, indent=2) + "\n", "server-spec.json": json.dumps(public_spec, ensure_ascii=False, indent=2) + "\n", ".gitignore": ".venv/\n__pycache__/\n*.py[cod]\n.env\n"}
    return GeneratedProject(spec["slug"], files)
