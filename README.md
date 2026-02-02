<div align="center">

# Paper2Post · 从论文到多平台爆款内容 📄✨

</div>

把一篇论文 PDF（一键解析文本）自动改写成：

- **Twitter/X Thread**：紧凑、高密度摘要，面向科研 & 工程圈 🧵  
- **小红书风格总结**：中文、结构清晰、友好又不失专业 📕  
- **LinkedIn 技术贴**：职业化、偏工程落地的长文分享 💼  

你只需要一份 `paper.pdf`，剩下的交给 `papercaster`。

---

## 项目亮点 🚀

- **一键多平台**：一次解析，自动生成三种完全不同的文案风格。
- **技术准确性优先**：Prompt 里有明确“不得编造”约束，缺信息会标记为“未在文中说明”。
- **启发式章节解析**：粗分出 `Abstract / Introduction / Method / Results / Conclusion` 等，提高 LLM 输出质量。
- **纯文本 PDF 解析**：使用 `pypdf`，稳定可靠，不依赖 OCR。
- **CLI 工具友好**：`papercaster paper.pdf --all` 即可跑。

---

## 安装指南 🛠️

### 1. 克隆或下载项目

```bash
cd Paper2Post
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv .venv
.venv\Scripts\activate   # PowerShell / CMD
```

### 3. 安装依赖 & 项目本体

```bash
pip install -r requirements.txt
pip install -e .
```

> 如果安装后提示 `papercaster` 不在 PATH，可以：
>
> - 直接用模块方式运行：`py -m Paper2Post.cli paper.pdf --all`  
> - 或把 Python 的 `Scripts` 目录加入 PATH（例如 `C:\Users\<you>\AppData\Local\Python\...\Scripts`）

---

## LLM 配置：环境变量 🌐

项目依赖一个 **OpenAI 兼容的 Chat Completions 接口**：

- **必填**
  - `OPENAI_API_KEY`
- **可选（有默认）**
  - `OPENAI_BASE_URL`：默认 `https://api.openai.com/v1`
  - `OPENAI_MODEL`：默认 `gpt-4o-mini`

在 PowerShell 中示例：

```powershell
$env:OPENAI_API_KEY = "你的_API_Key"
$env:OPENAI_MODEL = "gpt-4o-mini"
papercaster paper.pdf --all
```

如果你使用自建网关或第三方兼容服务，只需要把 `OPENAI_BASE_URL` 改掉即可。

---

## CLI 使用方法 💻

### 1. 生成所有平台内容

```bash
papercaster paper.pdf --all
```

- 不加 `--outdir` 时：直接在终端打印三种平台的结果。
- 加 `--outdir` 时：会在目标目录下生成 3 个 Markdown 文件。

```bash
papercaster paper.pdf --all --outdir outputs
```

会生成大致如下文件：

- `outputs/twitter_thread.md`
- `outputs/xiaohongshu.md`
- `outputs/linkedin.md`

### 2. 只生成单个平台

```bash
papercaster paper.pdf --twitter
papercaster paper.pdf --xiaohongshu
papercaster paper.pdf --linkedin
```

### 3. 限制解析页数（加速 & 控制 Token）

```bash
papercaster long_paper.pdf --all --max-pages 8
```

---

## 项目结构与核心模块 🧩

```text
Paper2Post/
├── Paper2Post/
│   ├── pdf_loader.py        # PDF 文本抽取
│   ├── section_parser.py    # 章节解析（启发式）
│   ├── generators/
│   │   ├── twitter.py       # Twitter/X Thread 生成
│   │   ├── xiaohongshu.py   # 小红书风格总结
│   │   └── linkedin.py      # LinkedIn 技术贴
│   ├── prompt.py            # LLM 调用 & Prompt 组合
│   └── cli.py               # CLI 入口（papercaster）
├── README.md
├── requirements.txt
├── setup.py
└── pyproject.toml
```

下面对代码做一点“读源码导览”，方便你二次开发 👇

---

## 1️⃣ PDF 文本抽取：`pdf_loader.py` 📚

核心函数：`load_pdf_text`  
职责：把 PDF 按页抽成干净的文本（仅 text，不 OCR）。

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List

from pypdf import PdfReader


@dataclass(frozen=True)
class PDFDocument:
    path: Path
    pages: List[str]

    @property
    def text(self) -> str:
        return "\n\n".join([p.strip() for p in self.pages if p and p.strip()]).strip()


def load_pdf_text(pdf_path: str | Path, *, max_pages: int | None = None) -> PDFDocument:
    path = Path(pdf_path).expanduser().resolve()
    reader = PdfReader(str(path))

    pages: List[str] = []
    limit = min(len(reader.pages), max_pages) if max_pages else len(reader.pages)
    for i in range(limit):
        page = reader.pages[i]
        txt = page.extract_text() or ""
        pages.append(_normalize_pdf_text(txt))

    return PDFDocument(path=path, pages=pages)
```

**设计要点：**

- 使用 `@dataclass` 把 PDF 抽象成 `PDFDocument`，带 `pages` 和聚合的 `text` 属性。
- `max_pages` 用于**大论文截断**，防止 prompt 过长和 token 爆炸。
- `_normalize_pdf_text` 里做了常见 PDF 垃圾清理：
  - 换行统一
  - 合并带 `-` 的人工断行（`trans-\nformer` → `transformer`）
  - 折叠过多空行

如果你后面想支持 **不同清洗策略**（比如保留公式附近的上下文），改这里即可。

---

## 2️⃣ 章节解析：`section_parser.py` 🧠

目标：从原始文本中尽量识别出：

- `title`
- `abstract`
- `introduction`
- `method(s)/approach`
- `experiments/results`
- `discussion/limitations`
- `conclusion`

核心接口：`parse_sections(text: str) -> ParsedPaper`

```python
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ParsedPaper:
    title: str
    sections: Dict[str, str]
    raw_text: str

    def get(self, name: str, default: str = "") -> str:
        return self.sections.get(name, default)
```

**主要逻辑：**

- `_guess_title`：从开头几十行里，过滤掉 `arXiv` / `doi` / `Abstract` 等非标题，猜论文标题。
- `_find_headings`：用正则匹配形如：
  - `Abstract`
  - `1 Introduction`
  - `2.1 Method`
  - `Conclusion`
- `_canonicalize`：把各种表述统一为规范键，比如：
  - `methods` / `methodology` / `approach` → `method`
  - `conclusions` → `conclusion`
  - `related work` → `related work`

得到的 `ParsedPaper` 会被后续 prompt 组装使用。

---

## 3️⃣ LLM & Prompt 设计：`prompt.py` 🧬

### 3.1 LLM 客户端：OpenAI 兼容

```python
import httpx
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient:
    def __init__(self, *, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o-mini", timeout_s: float = 120.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def chat(self, messages: List[ChatMessage], *, temperature: float = 0.4) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
```

**特点：**

- 只依赖 `httpx`，实现一个最小的 Chat Completions 客户端。
- 支持自定义 `base_url` 和 `model`，方便切换到别的兼容服务。

### 3.2 上下文构建 & 准确性护栏

```python
def build_paper_context(*, title: str, sections: Dict[str, str], raw_text: str, max_chars: int = 18000) -> str:
    preferred = ["abstract", "introduction", "method", "results", "discussion", "limitations", "conclusion"]
    parts: List[str] = []
    if title:
        parts.append(f"Title: {title}")
    for k in preferred:
        if k in sections and sections[k].strip():
            parts.append(f"\n## {k.title()}\n{sections[k].strip()}")

    if len(parts) <= 1:
        parts.append("\n## Paper Text (truncated)\n" + raw_text.strip())

    ctx = "\n".join(parts).strip()
    if len(ctx) > max_chars:
        ctx = ctx[:max_chars].rstrip() + "\n\n[TRUNCATED]"
    return ctx
```

`system_guardrails()` 中明确要求：

- 保持技术准确性，不编造结果/数据集/指标。
- 信息缺失时必须标注“未在文本中说明”。

后面三种平台生成器会在此基础上叠加各自风格的 prompt。

---

## 4️⃣ 三大平台生成器：`generators/` 🧵📕💼

### 4.1 Twitter/X：`generators/twitter.py`

**风格定位**：  
短句、偏技术，不搞鸡汤，不刷无意义 emoji，也不会乱打标签。

**核心设计点：**

- 要求输出 **10–14 条 tweet**，每条 ≤ 280 字符。
- 强制编号格式：`1/12`, `2/12`, ...
- Prompt 结构里明确要求：
  - 问题 → 方法 → 结果 → 意义 → 局限 → 适用人群。
  - 缺少信息必须写明 `Not specified in the provided text`。

### 4.2 小红书：`generators/xiaohongshu.py`

**风格定位**：

- 中文、口语化，结构清晰，适合科研/工程圈“种草式”分享。
- 有完整的：
  - 吸引但不标题党的标题
  - TL;DR
  - 分节小标题
  - 复现/落地清单
  - “适合谁/不适合谁”

并且明确禁止：

- 夸张网络梗
- emoji（如果你喜欢也可以以后放宽）

### 4.3 LinkedIn：`generators/linkedin.py`

**风格定位**：

- 专业、工程视角，面向“做系统的人”。
- 400–900 词，短段落 + bullets。
- 内容包括：
  - 问题背景
  - 方法概述（高层机制）
  - 证据/结果（缺失则说明）
  - 在真实系统里的潜在用法
  - 风险 & 局限
  - 最后附带 2 个给从业者的问题，方便引导讨论。

---

## 5️⃣ CLI 入口：`cli.py` 🧰

命令行的核心流程：

```python
def main(argv: list[str] | None = None) -> None:
    # 1. 解析命令行参数（pdf 路径、输出选项）
    # 2. 校验至少选择一个输出平台
    # 3. 读取环境变量，构造 LLMClient
    # 4. 调用 load_pdf_text → parse_sections → build_paper_context
    # 5. 分别调用各平台 generator
    # 6. 输出到终端或写入文件
```

你可以很容易扩展：

- 新增 `--wechat`、`--medium` 等参数。
- 在 `generators/` 下再加一个生成器模块并在 `cli.py` 里接上。

---

## 适用场景 & 局限性 🧪

- **适用：**
  - 快速把自己刚读/刚写的论文转换成多平台可发的内容。
  - 帮导师/老板/合作者准备项目宣传素材。
  - 运营团队想要技术向内容但又不想从 PDF 抄来抄去。

- **当前局限：**
  - 只做 **文本解析**，不处理图表、公式截图等（需要 OCR 可自行扩展）。
  - 章节解析是启发式的，对格式很乱的 PDF 可能效果一般。
  - 依赖外部 LLM 接口，需要配置 API Key。

---

## 下一步可以做什么？🧭

- 增加一个 **“复现脚本提示”** 生成器，专门输出 pseudo-code / 训练脚本骨架。
|- 针对 arXiv / conference 模板做更强的结构识别。
- 加一个简单的 **Web UI**（Streamlit / FastAPI + 前端）方便非技术同事使用。

欢迎你在此基础上魔改，贴合你自己的工作流。  
如果你有新的平台需求，也可以在 `generators/` 下加一个模块，然后在 `cli.py` 里接入新的 CLI 参数即可。🚀

---

## 🤝 贡献与支持 (Contribution)

**Paper2Post** 是一个开源项目，我们需要您的帮助让它变得更好！

*   **给个 Star** ⭐：如果您觉得这个项目对您有帮助，请点击右上角的 Star，这是对我最大的鼓励！
*   **提交 Issue** 🐛：发现 Bug 或有新功能建议？欢迎提交 Issue。
*   **提交 PR** 🧑‍💻：欢迎贡献代码，无论是修复 Bug 还是增加新特性。

---

## 👤 作者 (Author)

**Haoze Zheng**

*   🎓 **School**: Xinjiang University (XJU)
*   📧 **Email**: zhenghaoze@stu.xju.edu.cn
*   🐱 **GitHub**: [mire403](https://github.com/mire403)

---

<div align="center">
  <sub>Made by Haoze Zheng. 2026 Paper2Post.</sub>
</div>
