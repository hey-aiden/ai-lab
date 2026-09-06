# uv init 的两种模式与 `[build-system]` 配置

> 本文源于一次真实排查:执行 `uv run start` 报 `program not found`,根因是 `pyproject.toml` 缺少 `[build-system]`,导致项目没有被安装成包、`[project.scripts]` 里的入口点从未注册。
>
> 验证环境:uv **0.11.32**(2026-07)。

---

## 一、结论先行

| 创建方式 | 项目类型 | 是否生成 `[build-system]` | 默认布局 | `[project.scripts]` 入口点 |
|---|---|---|---|---|
| `uv init` | 应用(virtual project) | ❌ 不生成 | 扁平(根目录) | ❌ 不生效 |
| `uv init --package` | 包(package) | ✅ 自动生成 | `src/` | ✅ 生效 |
| `uv init --lib` | 库(library) | ✅ 自动生成 | `src/` | 一般不设 |

**核心要点:**

- `[build-system]` —— 一般**不用手动写**,用 `uv init --package` 会自动生成。
- `[tool.uv.build-backend]` —— 通常**不会自动生成**,只有当包目录名 ≠ 项目名、或使用扁平布局等非常规情况时才需要手动补。

---

## 二、两种模式的生成结果

### 1. `uv init`(默认,应用模式)

```bash
uv init my-app
```

生成的 `pyproject.toml`:

```toml
[project]
name = "my-app"
version = "0.1.0"
description = "Add your description here"
requires-python = ">=3.11"
dependencies = []
```

特征:

- **没有 `[build-system]`**,也没有 `[project.scripts]`。
- 这是一个"虚拟项目"(virtual project),uv 不会把它本身安装进 `.venv`。
- `uv run python xxx.py` 能跑(uv 会把项目根目录加进 `sys.path`),但 `[project.scripts]` 入口点**不会注册**。

### 2. `uv init --package`(包模式)

```bash
uv init --package my-pkg
```

生成的 `pyproject.toml`:

```toml
[project]
name = "my-pkg"
version = "0.1.0"
description = "Add your description here"
authors = [{ name = "...", email = "..." }]
requires-python = ">=3.11"
dependencies = []

[project.scripts]
my-pkg = "my_pkg:main"

[build-system]
requires = ["uv_build>=0.11.32,<0.12.0"]
build-backend = "uv_build"
```

生成的目录结构:

```
my-pkg/
├── pyproject.toml
└── src/
    └── my_pkg/
        └── __init__.py
```

特征:

- **自动生成 `[build-system]` 和 `[project.scripts]`**。
- 默认使用 **`src/` 布局**。
- 项目会被安装进 `.venv`,入口点脚本(如 `my-pkg`)可用。

---

## 三、关键配置段说明

### `[build-system]` —— 声明"怎么构建这个包"

```toml
[build-system]
requires = ["uv_build>=0.12.0,<0.13.0"]
build-backend = "uv_build"
```

- `requires` 里的版本指的是 **`uv_build` 构建后端包**的版本,与 uv CLI 自身的版本相互独立(uv 会单独下载 `uv_build`)。
- 没有这一段,uv 就把项目当作"虚拟项目",不安装、不注册脚本。

### `[tool.uv.build-backend]` —— 只有非常规时才需要

只有下面两种情况才需要手动补这段:

| 字段 | 什么时候需要 | 说明 |
|---|---|---|
| `module-name = "app"` | 包目录名 ≠ 项目名 | 项目叫 `langchain-camp`,但包目录是 `app`,必须显式指定导入名 |
| `module-root = "."` | 使用扁平布局 | 默认按 `src/` 找包,扁平布局需要指到根目录 |

---

## 四、布局:src vs 扁平

| 布局 | 目录结构 | `[tool.uv.build-backend]` |
|---|---|---|
| src 布局(默认) | `src/<包名>/__init__.py` | 不需要(除非包名≠项目名) |
| 扁平布局 | `<包名>/__init__.py` | 需要 `module-root = "."` |

`agent-server` 用的是 src 布局(`src/app/`),`langchain-camp` 用的是扁平布局(`app/` 在根目录),所以后者需要额外配置。

---

## 五、本项目(langchain-camp)的实际配置

它叠加了三个非常规点,所以 `[build-system]` 和 `[tool.uv.build-backend]` 两段都得手动补:

1. 用默认 `uv init` 创建 → 缺 `[build-system]`;
2. 项目名 `langchain-camp` ≠ 包目录 `app` → 需要 `module-name = "app"`;
3. 扁平布局 → 需要 `module-root = "."`。

```toml
[project]
name = "langchain-camp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langchain>=1.4.0",
    "langchain-deepseek>=1.1.0",
    "langgraph>=1.2.11",
    "python-dotenv>=1.2.3",
]

[project.scripts]
start = "app.main:main"

[tool.uv.build-backend]
module-name = "app"
module-root = "."

[build-system]
requires = ["uv_build>=0.12.0,<0.13.0"]
build-backend = "uv_build"
```

---

## 六、实践建议

- **想要可安装、带入口点脚本的项目**:直接 `uv init --package`,让 uv 自动生成 `[build-system]`,省去手动配置。
- **包目录名跟项目名保持一致**,能省掉 `module-name`。例如 `uv init --package --name app`,包目录就是 `app`。
- **维持扁平布局 + `app` 目录**(当前 langchain-camp 的做法):按上文手动保留 `[build-system]` 与 `[tool.uv.build-backend]` 两段即可。
