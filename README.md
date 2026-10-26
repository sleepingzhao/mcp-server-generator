# MCP Server Generator

一个无需前端构建流程的本地可视化 MCP Server 生成器。通过表单定义 Tools，实时预览并下载完整项目 ZIP。

## MVP 能力

- stdio 与 Streamable HTTP 两种传输
- Tool 参数：string、integer、number、boolean、array、object
- 三类处理器：JSON 模板响应、HTTP API、本地命令
- HTTP URL/Header/Body 和命令参数支持 `{参数名}` 占位符
- 命令通过参数数组执行，不经过 shell
- 输出 `server.py`、依赖、客户端配置、规格 JSON 和 README
- 后端校验 Tool/参数命名、重复项、JSON 配置、URL 和超时

## 启动生成器

需要 Python 3.10+：

```powershell
cd mcp-server-generator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

打开 http://127.0.0.1:5050 。页面启动时已载入三个示例 Tool。

## 生成项目

1. 设置项目名称与传输方式。
2. 新建 Tool、参数并选择处理器。
3. 点击“生成预览”检查文件。
4. 点击“下载 ZIP”。
5. 解压后按生成项目自身的 README 安装并运行。

stdio 项目可用相邻的 `../mcp-client` 验证：先安装生成项目依赖，再按其 `mcp-config.json` 设置绝对路径。

## 测试

```powershell
python -m unittest discover -s tests -v
```

> 本工具目前只绑定本机地址。若把生成的 HTTP Server 暴露到网络，请自行增加认证、授权、限流和严格的 Origin/Host 策略。
