# PDF2MD-Cleaner

> 将嵌入式 / 单片机 / 运动控制器的 PDF 编程手册转为干净的 Markdown，自动去除页眉页脚、厂商名、页码等冗余，保留并修复寄存器表格。

## 为什么需要

MCU 厂商的编程手册（Reference Manual / Datasheet / User Manual）通常几百页起步，转成 Markdown 后每页都夹杂着 "STMicroelectronics"、"Page 45/200"、"-46-"、版权声明等重复内容，表格格式也经常断裂。本工具解决这些问题。

## 效果一览

**清理前**（PyMuPDF4LLM 原始输出片段）：

```markdown
# STM32F103 Reference Manual

STMicroelectronics

RM0008

| Bit | Name | Type | Reset | Description |
| | | | | |
| 31:16 | RESERVED | - | - | Reserved |

Address: 0x40010804

© 2024 STMicroelectronics

Proprietary

-46-

STMicroelectronics
```

**清理后**：

```markdown
# STM32F103 Reference Manual

| Bit | Name | Type | Reset | Description |
|---|---|---|---|---|
| 31:16 | RESERVED | - | - | Reserved |

Address: `0x40010804`
```

冗余内容删除，表头分隔符修复，十六进制地址自动加 inline code。

## 快速开始

### 安装

```powershell
# 方式一：脚本安装（推荐）
powershell -ExecutionPolicy Bypass -File scripts/install_deps.ps1 -Lightweight   # 最小安装，无需 GPU
powershell -ExecutionPolicy Bypass -File scripts/install_deps.ps1 -Docling       # + Docling，表格更强
powershell -ExecutionPolicy Bypass -File scripts/install_deps.ps1 -All           # 全部安装

# 方式二：手动
pip install pymupdf4llm          # 必装，轻量，无需 GPU
pip install docling              # 可选，更好的表格识别（仍不需要 GPU）
```

### 一行转换

```powershell
# 最简单：PyMuPDF4LLM 转换 + 自动清理
python scripts/pdf2md_multi.py manual.pdf -b pymupdf4llm -o ./output

# 多后端对比 + LLM 自动选最优
python scripts/pdf2md_multi.py manual.pdf -b all -o ./output --evaluate --api-key YOUR_KEY
```

### 批量转换

```powershell
python scripts/batch_convert.py ./pdfs/ -o ./output -b pymupdf4llm
```

### 只清理已有的 Markdown

```powershell
python scripts/md_cleaner.py input.md -o cleaned.md --aggressive --report
```

## 四个转换后端

| 后端 | GPU | 特点 | 什么时候用 |
|------|:---:|------|-----------|
| **PyMuPDF4LLM** | 否 | 轻量极速，开箱即用 | 日常使用，快速预览 |
| **Docling** | 否 | IBM 出品，TableFormer 表格识别强 | 寄存器表格多的手册 |
| **Marker** | 推荐 | 深度学习高精度，21k★ | 扫描件、需要极高精度 |
| **MinerU** | 推荐 | 最强复杂布局，30k★ | 最复杂的文档、学术论文 |

日常用 PyMuPDF4LLM 或 Docling 就够了。Marker 和 MinerU 需要 GPU 和模型下载，适合特殊需求。

## 自动清理了什么

### 删除的冗余内容

| 类型 | 示例 |
|------|------|
| 厂商名 | STMicroelectronics、NXP、TI、Microchip、Renesas、Espressif、GigaDevice、WCH 等 30+ |
| 页码 | `45`、`Page 45 of 200`、`-46-`、`45/200` |
| 文档编号 | RM0008、DS12345、AN1234、UM1234 |
| 版权声明 | © 2024 STMicroelectronics、Copyright © ... |
| 版本戳 | Rev. 16 |
| 保密标记 | Proprietary、Confidential、Preliminary |
| 厂商 URL | st.com、nxp.com、ti.com 等链接行 |
| 目录章节 | （`--aggressive` 模式） |
| 修订历史 | （`--aggressive` 模式） |

清理器还会**自适应检测**：如果某一行在文档中重复出现 3 次以上，自动判定为页眉/页脚并删除。

### 表格修复

- 自动插入缺失的表头分隔符 `|---|---|`
- 删除空表格行 `| | | |`
- 删除表格内的空行
- 修正表格行前导空格

### 寄存器格式化

| 处理项 | 效果 |
|--------|------|
| 十六进制地址 | `0x40010800` → `` `0x40010800` `` |
| 寄存器名 | GPIOx_CRH → `GPIOx_CRH` |
| Unicode 符号 | ×→x、±→+/-、≤→<=、≥→>=、→→-> |
| Bit-field | bit[3:0] → bits 3-0 |
| 访问类型 | r/w → R/W（统一大写） |

## LLM 评估（可选）

启用 `--evaluate` 后，工具会把各后端的输出提交给大模型，从 5 个维度打分（各 0-10，满分 50），自动选最优：

| 维度 | 评估内容 |
|------|----------|
| 表格质量 | 寄存器表格是否完整、格式正确 |
| 结构保持 | 标题层级、章节结构是否保留 |
| 清洁度 | 冗余信息是否清除干净 |
| 寄存器数据 | 地址、位域、复位值是否保留 |
| 可读性 | 整体 Markdown 是否清晰可读 |

评估结果保存在 `output/evaluation_report.json`。

默认使用 `deepseek-ai/deepseek-v4-flash`（通过 NVIDIA API），需要 API Key。

## 命令参数

### pdf2md_multi.py

```
python scripts/pdf2md_multi.py <input.pdf> [选项]

  -b, --backend     all | pymupdf4llm | docling | marker | mineru
                    默认: pymupdf4llm
  -o, --output-dir  输出目录，默认 ./output
  -c, --clean       后处理清理（默认开启）
  --no-clean        关闭清理
  -e, --evaluate    启用 LLM 评估
  --api-key         NVIDIA API Key（或设置环境变量 NVIDIA_API_KEY）
  --model           评估模型，默认 deepseek-ai/deepseek-v4-flash
```

### md_cleaner.py

```
python scripts/md_cleaner.py <input.md> [选项]

  -o, --output      输出文件路径
  --aggressive      激进模式（删除目录、修订历史）
  --report          输出清理报告
```

### batch_convert.py

```
python scripts/batch_convert.py <input_dir> [选项]

  -o, --output-dir  输出目录，默认 ./output
  -b, --backend     转换后端，默认 pymupdf4llm
  --deep-clean      深度清理模式
```

## 项目结构

```
pdf2md-cleaner/
├── README.md                    ← 本文件
├── SKILL.md                     ← OpenClaw Skill 定义
├── requirements.txt             ← Python 依赖
├── pipeline_evaluation.json     ← LLM 对工具链设计的评估报告
├── test_sample.md               ← 测试样本（模拟 STM32 手册）
├── test_sample_cleaned.md       ← 清理后输出
└── scripts/
    ├── pdf2md_multi.py           主转换脚本（多后端 + 清理 + LLM 评估）
    ├── md_cleaner.py             独立 Markdown 清理器
    ├── llm_evaluate.py           独立 LLM 评估器
    ├── batch_convert.py          批量转换
    ├── install_deps.ps1          PowerShell 依赖安装
    └── llm_eval_pipeline.ps1     LLM 评估 PowerShell 脚本
```

## 已验证的手册类型

- ✅ STM32 参考手册（RM0008 等）
- ✅ GD32 用户手册
- ✅ ESP32 技术参考手册
- ✅ NXP LPC 系列用户手册
- ✅ 运动控制器编程手册（TMC、ASDA 等）

## 环境要求

- **Python** 3.10+
- **OS**：Windows / macOS / Linux
- **GPU**：仅 Marker 和 MinerU 需要（PyMuPDF4LLM 和 Docling 纯 CPU 运行）
- **LLM 评估**：NVIDIA API Key（[免费申请](https://build.nvidia.com/)）

## 常见问题

**Q: 转换很慢怎么办？**

先用 PyMuPDF4LLM 快速预览：`python scripts/pdf2md_multi.py input.pdf -b pymupdf4llm`。如果表格质量不够，再换 Docling。

**Q: 表格还是不完整？**

试试 Docling 后端，它的 TableFormer 模型对表格识别最好：`-b docling`。

**Q: 不想用 LLM 评估？**

不用加 `--evaluate` 参数即可。工具默认只做转换 + 清理，不需要任何 API Key。

**Q: 清理太激进了，删了不该删的？**

去掉 `--aggressive` 参数（仅保留默认清理），或用 `--no-clean` 完全关闭清理。

## License

MIT
