---
name: pdf2md-cleaner
description: |
  PDF转Markdown工具链，专为嵌入式/单片机/运动控制器编程手册优化。
  支持多后端转换（PyMuPDF4LLM、Docling、Marker、MinerU），自动清理页眉页脚/公司名/手册名等冗余信息，
  修复表格格式，格式化寄存器地址和寄存器名，使用大模型评估选出最佳输出。
  触发词：PDF转markdown、转换PDF、手册转换、datasheet转换、寄存器手册、PDF提取表格、
  pdf2md、clean pdf、嵌入式手册转换、MCU手册、编程手册转markdown。
metadata:
  openclaw:
    emoji: "📄"
---

# PDF to Markdown Cleaner — 嵌入式手册专用

## 用途

将嵌入式/MCU/运动控制器等PDF编程手册转换为干净的Markdown格式，自动去除冗余页眉页脚，保留寄存器表格。

## 工作流

```
PDF输入 → 多后端并行转换 → 自动清理 → LLM评估选优 → 最终Markdown输出
```

## 工具链结构

```
pdf2md-cleaner/
├── SKILL.md                      ← 本文件
├── requirements.txt
├── scripts/
│   ├── pdf2md_multi.py           ← 主转换脚本（多后端+清理+评估）
│   ├── md_cleaner.py             ← 独立Markdown清理器
│   ├── llm_evaluate.py           ← 独立LLM评估器
│   ├── batch_convert.py          ← 批量转换
│   └── install_deps.ps1          ← 依赖安装
└── pipeline_evaluation.json      ← LLM评估报告
```

## 四大后端对比

| 后端 | 特点 | GPU | Stars | 适用场景 |
|------|------|-----|-------|----------|
| **PyMuPDF4LLM** | 轻量极速，无需GPU | 否 | 高 | 快速转换，简单手册 |
| **Docling (IBM)** | TableFormer表格识别，布局理解强 | 否 | 29k+ | 复杂表格，寄存器映射 |
| **Marker** | 深度学习高精度，多语言 | 推荐 | 21k+ | 高精度需求，扫描件 |
| **MinerU** | 最强复杂布局，公式/表格 | 推荐 | 30k+ | 最复杂文档，学术论文 |

LLM评估推荐排序：PyMuPDF4LLM > Docling > Marker > MinerU（综合速度与质量）

## 清理规则

### 自动去除的冗余信息
- **厂商名**：STMicroelectronics、NXP、TI、Microchip、Renesas、Espressif、GigaDevice、WCH等30+
- **页码**：独立数字、Page X of Y、-N-、N/M格式
- **文档编号**：RMxxxx、DSxxxx、ANxxxx、UMxxxx、PMxxxx、TNxxxx
- **手册标题**（作为页眉重复出现的）
- **版权声明**：© 2024 xxx、Copyright © xxx
- **版本戳**：Rev. X.X
- **保密标记**：Proprietary、Confidential、Preliminary
- **厂商URL**：st.com、nxp.com、ti.com等
- **目录章节**（aggressive模式）
- **修订历史**（aggressive模式）

### 表格修复
- 自动插入缺失的表头分隔符 `|---|---|`
- 删除表格内空行
- 删除空表格行 `| | | |`
- 修正表格行前导空格

### 寄存器增强
- **十六进制地址**自动加inline code：`0x40010800`
- **寄存器名**自动加inline code：`GPIOx_CRH`、`USART_SR`、`TIMx_PSC`
- **Unicode数学符号**规范化：×→x、±→+/-、≤→<=、≥→>=
- **Bit-field标记**标准化：bit[3:0] → bits 3-0
- **访问类型**统一大写：R/W、RC_W1、RO、WO

## 使用方法

### 1. 安装依赖

```powershell
# 轻量安装（仅PyMuPDF4LLM，无需GPU）
powershell -ExecutionPolicy Bypass -File scripts/install_deps.ps1 -Lightweight

# 安装Docling（推荐，CPU友好）
powershell -ExecutionPolicy Bypass -File scripts/install_deps.ps1 -Docling

# 全部安装
powershell -ExecutionPolicy Bypass -File scripts/install_deps.ps1 -All
```

或手动安装：
```powershell
pip install pymupdf4llm          # 轻量，必装
pip install docling              # 推荐补充
# pip install marker-pdf         # 需GPU
# pip install -U "magic-pdf[full]" --extra-index-url https://wheels.myhloli.com  # 需GPU+模型
```

### 2. 单文件转换

```powershell
# 最简：用PyMuPDF4LLM转换+清理
python scripts/pdf2md_multi.py input.pdf -b pymupdf4llm -o ./output --clean

# 多后端对比+LLM评估选优
python scripts/pdf2md_multi.py input.pdf -b all -o ./output --clean --evaluate --api-key YOUR_KEY

# 仅Docling（推荐的CPU-only高质量后端）
python scripts/pdf2md_multi.py input.pdf -b docling -o ./output --clean
```

### 3. 批量转换

```powershell
python scripts/batch_convert.py ./pdfs/ -o ./output -b pymupdf4llm --deep-clean
```

### 4. 独立清理已有Markdown

```powershell
python scripts/md_cleaner.py input.md -o output_cleaned.md --aggressive --report
```

### 5. 独立LLM评估

```powershell
python scripts/llm_evaluate.py --files backend1.md backend2.md --api-key YOUR_KEY --model deepseek-ai/deepseek-v4-flash
```

## LLM评估维度

| 维度 | 满分 | 评估内容 |
|------|------|----------|
| 表格质量 | 10 | 寄存器表格是否完整、格式正确 |
| 结构保持 | 10 | 标题层级、章节结构是否保留 |
| 清洁度 | 10 | 页眉页脚/公司名/页码是否清除 |
| 寄存器数据 | 10 | 十六进制地址、位域、复位值是否保留 |
| 可读性 | 10 | 整体Markdown是否清晰可读 |
| **总分** | **50** | |

## 参数说明

### pdf2md_multi.py 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `input` | (必填) | PDF文件路径 |
| `-b/--backend` | pymupdf4llm | 转换后端：all/pymupdf4llm/docling/marker/mineru |
| `-o/--output-dir` | ./output | 输出目录 |
| `--clean/-c` | 开启 | 后处理清理 |
| `--no-clean` | - | 关闭清理 |
| `--evaluate/-e` | 关闭 | LLM评估选优 |
| `--api-key` | 环境变量 | NVIDIA API密钥 |
| `--model` | deepseek-ai/deepseek-v4-flash | 评估用模型 |

## 注意事项

1. **PyMuPDF4LLM**无需GPU，开箱即用，适合大多数手册
2. **Docling**也支持CPU运行，表格识别质量更高
3. **Marker和MinerU**需要GPU和模型下载，适合极高精度需求
4. LLM评估需要NVIDIA API Key（免费额度可用）
5. 大文件（>100页）建议先用PyMuPDF4LLM快速预览
6. 清理规则已针对STM32/GD32/ESP32/NXP等主流MCU手册优化
7. 输出文件命名规则：`{pdf名}_{后端名}_cleaned.md`

## 已验证手册类型

- STM32参考手册（RM0008等）
- GD32用户手册
- ESP32技术参考手册
- NXP LPC系列用户手册
- 运动控制器编程手册（TMC、ASDA等）
