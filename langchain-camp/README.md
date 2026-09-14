# langchain-camp

LangChain 学习 / 实验项目(基于 LangChain + DeepSeek + LangGraph),用于学习与验证 LangChain 的用法。

## 运行

```bash
uv sync      # 安装依赖
uv run start # 运行入口 app.main:main
```

配置通过 `.env` 提供 `API_KEY_DEEPSEEK` / `MODEL_DEEPSEEK` / `TEMPERATURE`(含密钥,已 gitignore)。

## 入口

- `app/main.py` — 入口,调用 `app.model.in_deep_seek()`
- `app/config.py` — 读取 `.env`,把 DeepSeek 配置装进 `global_config`

## 相关文档

- [LangGraph Checkpointer 的实现机制](../docs/langgraph-checkpointer.md) — 记忆持久化的机制说明与常见坑
- [uv init 的两种模式与 `[build-system]` 配置](../docs/uv-init.md)
