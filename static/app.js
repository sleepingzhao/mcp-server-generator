"use strict";
const state = { tools: [], selected: -1, files: {} };
const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function defaultConfig(handler) {
  if (handler === "http") return { method: "GET", url: "https://api.example.com/items/{id}", headers: {}, query: {}, body: {}, params_mode: "auto", response_mode: "auto", timeout: 30 };
  if (handler === "command") return { executable: "echo", args: ["{text}"], cwd: "", env: {}, stdin: "", timeout: 30, allowed_exit_codes: [0] };
  return { response: { ok: true } };
}
function freshTool() { return { name: "new_tool", description: "", handler: "static", params: [], config: defaultConfig("static") }; }
function addTool(tool = freshTool()) { state.tools.push(tool); state.selected = state.tools.length - 1; render(); }
function removeTool() { if (state.selected < 0) return; state.tools.splice(state.selected, 1); state.selected = Math.min(state.selected, state.tools.length - 1); render(); }
function selectTool(index) { state.selected = index; render(); }
function updateTool() { const tool = state.tools[state.selected]; if (!tool) return; const nextHandler = $("handler").value; tool.name = $("tn").value; tool.description = $("td").value; if (tool.handler !== nextHandler) { tool.handler = nextHandler; tool.config = defaultConfig(nextHandler); } renderToolList(); }
function render() { renderToolList(); renderEditor(); }
function renderToolList() {
  const root = $("tools"); root.replaceChildren();
  if (!state.tools.length) { root.innerHTML = '<div class="empty">暂无 Tool</div>'; return; }
  state.tools.forEach((tool, index) => { const item = document.createElement("div"); item.className = "tool" + (index === state.selected ? " active" : ""); item.innerHTML = `<b>${escapeHtml(tool.name || "未命名")}</b><div class="tiny">${escapeHtml(tool.handler)} · ${tool.params.length} params</div>`; item.addEventListener("click", () => selectTool(index)); root.appendChild(item); });
}
function renderEditor() { const tool = state.tools[state.selected]; $("noTool").hidden = Boolean(tool); $("editor").hidden = !tool; if (!tool) return; $("tn").value = tool.name; $("td").value = tool.description; $("handler").value = tool.handler; renderParams(); renderConfig(); }
function addParam() { const tool = state.tools[state.selected]; if (!tool) return; tool.params.push({ name: "param" + (tool.params.length + 1), type: "string", description: "", required: true }); render(); }
function deleteParam(index) { state.tools[state.selected].params.splice(index, 1); render(); }
function renderParams() {
  const root = $("params"); root.replaceChildren(); const params = state.tools[state.selected].params;
  if (!params.length) { root.innerHTML = '<div class="empty">无参数</div>'; return; }
  params.forEach((param, index) => { const wrap = document.createElement("div"); wrap.className = "param"; wrap.innerHTML = '<div class="paramgrid"><div><label>名称</label><input data-key="name"></div><div><label>类型</label><select data-key="type"><option>string</option><option>integer</option><option>number</option><option>boolean</option><option>array</option><option>object</option></select></div><div class="param-description"><label>描述</label><input data-key="description"></div><label class="check"><input data-key="required" type="checkbox">必填</label><button class="danger param-delete">删除</button></div>';
    wrap.querySelector('[data-key="name"]').value = param.name; wrap.querySelector('[data-key="type"]').value = param.type; wrap.querySelector('[data-key="description"]').value = param.description; wrap.querySelector('[data-key="required"]').checked = param.required;
    wrap.querySelectorAll("[data-key]").forEach((input) => input.addEventListener("change", () => { param[input.dataset.key] = input.type === "checkbox" ? input.checked : input.value; renderToolList(); })); wrap.querySelector("button").addEventListener("click", () => deleteParam(index)); root.appendChild(wrap); });
}
function addTextField(root, label, key, value, rows = 0) { const field = document.createElement("div"); field.className = "field"; const lab = document.createElement("label"); lab.textContent = label; const input = rows ? document.createElement("textarea") : document.createElement("input"); if (rows) input.rows = rows; input.value = value; input.addEventListener("change", () => { state.tools[state.selected].config[key] = input.value; }); field.append(lab, input); root.appendChild(field); }
function addSelectField(root, label, key, options, value) { const field = document.createElement("div"); field.className = "field"; const lab = document.createElement("label"), select = document.createElement("select"); lab.textContent = label; options.forEach((item) => select.add(new Option(item[1], item[0]))); select.value = value; select.addEventListener("change", () => state.tools[state.selected].config[key] = select.value); field.append(lab, select); root.appendChild(field); }
function renderConfig() {
  const tool = state.tools[state.selected], config = tool.config || (tool.config = defaultConfig(tool.handler)), root = $("config"); root.replaceChildren();
  const hint = document.createElement("p"); hint.className = "tiny"; hint.textContent = "文本和 JSON 值支持 {参数名}；敏感值支持 $" + "{ENV:变量名}，运行时从环境变量读取。"; root.appendChild(hint);
  if (tool.handler === "static") { addTextField(root, "响应 JSON 或文本", "responseText", config.responseText || JSON.stringify(config.response ?? { ok: true }, null, 2), 8); return; }
  if (tool.handler === "http") {
    Object.assign(config, { method: config.method || "GET", url: config.url || "https://api.example.com/items/{id}", headers: config.headers ?? {}, query: config.query ?? {}, body: config.body ?? {}, params_mode: config.params_mode || "auto", response_mode: config.response_mode || "auto", timeout: config.timeout || 30 });
    const row = document.createElement("div"); row.className = "row"; addSelectField(row, "Method", "method", [["GET","GET"],["POST","POST"],["PUT","PUT"],["PATCH","PATCH"],["DELETE","DELETE"]], config.method); addTextField(row, "URL", "url", config.url); root.appendChild(row);
    const modes = document.createElement("div"); modes.className = "row"; addSelectField(modes, "未引用参数放到", "params_mode", [["auto","自动：GET→Query，其余→Body"],["query","Query"],["body","JSON Body"],["none","忽略"]], config.params_mode); addSelectField(modes, "响应解析", "response_mode", [["auto","自动 JSON/文本"],["json","必须为 JSON"],["text","始终文本"]], config.response_mode); root.appendChild(modes);
    addTextField(root, "Query JSON", "query", typeof config.query === "string" ? config.query : JSON.stringify(config.query, null, 2), 3); addTextField(root, "Headers JSON", "headers", typeof config.headers === "string" ? config.headers : JSON.stringify(config.headers, null, 2), 3); addTextField(root, "Body JSON", "body", typeof config.body === "string" ? config.body : JSON.stringify(config.body, null, 2), 4); addTextField(root, "超时秒（1-300）", "timeout", config.timeout); return;
  }
  Object.assign(config, { executable: config.executable || "echo", args: config.args ?? ["{text}"], cwd: config.cwd || "", env: config.env ?? {}, stdin: config.stdin || "", timeout: config.timeout || 30, allowed_exit_codes: config.allowed_exit_codes ?? [0] });
  const row = document.createElement("div"); row.className = "row"; addTextField(row, "Executable", "executable", config.executable); addTextField(row, "工作目录（可空）", "cwd", config.cwd); root.appendChild(row); addTextField(root, "参数 JSON 数组（不经过 shell）", "args", typeof config.args === "string" ? config.args : JSON.stringify(config.args, null, 2), 4); addTextField(root, "环境变量 JSON", "env", typeof config.env === "string" ? config.env : JSON.stringify(config.env, null, 2), 3); addTextField(root, "stdin 模板（可空）", "stdin", config.stdin, 3); const tail = document.createElement("div"); tail.className = "row"; addTextField(tail, "超时秒（1-600）", "timeout", config.timeout); addTextField(tail, "允许的退出码 JSON", "allowed_exit_codes", typeof config.allowed_exit_codes === "string" ? config.allowed_exit_codes : JSON.stringify(config.allowed_exit_codes)); root.appendChild(tail);
}
function specification() { return { name: $("name").value, package: $("package").value, description: $("desc").value, transport: $("transport").value, host: $("host").value, port: Number($("port").value), tools: state.tools.map((tool) => { const copy = structuredClone(tool); if (copy.handler === "static" && copy.config.responseText !== undefined) { try { copy.config.response = JSON.parse(copy.config.responseText); } catch { copy.config.response = copy.config.responseText; } delete copy.config.responseText; } return copy; }) }; }
function setStatus(text, error = false) { $("status").textContent = text; $("status").className = "status" + (error ? " error" : ""); }
async function request(path) { const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(specification()) }); if (!response.ok) { const data = await response.json(); throw new Error(data.error || "请求失败"); } return response; }
async function preview() { try { setStatus("生成中…"); const data = await (await request("/api/preview")).json(); state.files = data.files; setStatus("已生成 " + Object.keys(state.files).length + " 个文件"); showFile(Object.keys(state.files)[0]); } catch (error) { setStatus(error.message, true); } }
function showFile(name) { const tabs = $("tabs"); tabs.replaceChildren(); Object.keys(state.files).forEach((file) => { const button = document.createElement("button"); button.textContent = file; button.className = file === name ? "active" : ""; button.addEventListener("click", () => showFile(file)); tabs.appendChild(button); }); $("code").textContent = state.files[name]; }
async function downloadZip() { try { setStatus("打包中…"); const response = await request("/api/download"); const blob = await response.blob(); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "mcp-server.zip"; link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000); setStatus("下载完成"); } catch (error) { setStatus(error.message, true); } }
function toggleHttp() { $("http").hidden = $("transport").value !== "streamable-http"; }
function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  $("themeBtn").textContent = next === "dark" ? "☀️ 浅色" : "🌙 深色";
  $("themeBtn").setAttribute("aria-pressed", String(next === "light"));
}
function toggleTheme() {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  localStorage.setItem("mcp_generator_theme", next);
  applyTheme(next);
}
function loadExample() { state.tools = [{ name: "greet", description: "向用户问好", handler: "static", params: [{ name: "name", type: "string", description: "用户名称", required: true }], config: { response: { message: "Hello, {name}!" } } }, { name: "get_post", description: "读取公开文章 API", handler: "http", params: [{ name: "id", type: "integer", description: "文章 ID", required: true }], config: { method: "GET", url: "https://jsonplaceholder.typicode.com/posts/{id}", headers: {}, body: {} } }, { name: "echo_text", description: "调用本地 echo", handler: "command", params: [{ name: "text", type: "string", description: "文字", required: true }], config: { executable: "echo", args: ["{text}"], timeout: 10 } }]; state.selected = 0; render(); preview(); }
$("themeBtn").addEventListener("click", toggleTheme); $("exampleBtn").addEventListener("click", loadExample); $("previewBtn").addEventListener("click", preview); $("downloadBtn").addEventListener("click", downloadZip); $("addToolBtn").addEventListener("click", () => addTool()); $("removeToolBtn").addEventListener("click", removeTool); $("addParamBtn").addEventListener("click", addParam); $("tn").addEventListener("input", updateTool); $("td").addEventListener("input", updateTool); $("handler").addEventListener("change", () => { updateTool(); renderEditor(); }); $("transport").addEventListener("change", toggleHttp);
applyTheme(localStorage.getItem("mcp_generator_theme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark")); toggleHttp(); loadExample();
