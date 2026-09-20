# CLIFF 1.1 Token 基准

- 语料：16 个翻译单元，分布在 4 个组中，包含家庭信息、规范、依赖、术语表、逐条 type/emotion/status/max-width/context/reference 和 ICU 载荷。
- 分词器：tiktoken cl100k_base。
- CLIFF token 数 = CLIFF 1.1 标准主文件 + 单独的 `variant: glossary` 依赖术语表文件。术语表在语义上是 CLIFF 语料的一部分，按 CLIFF 的实际单工作流成本计入；其他每种格式都在其原生语法中内联同样的三条术语。
- 可复现性：连续两次运行 `python tools/token_benchmark.py` 得到完全一致的 token 数（本报告由第二次运行生成）。

| 格式 | Tokens | 字符数 | 字节数 | vs CLIFF |
| --- | ---: | ---: | ---: | ---: |
| CLIFF 1.1 | 1138 | 3571 | 3821 | +0.0% |
| XLIFF 2.1 | 2095 | 7462 | 7712 | +84.1% |
| JSON | 1594 | 5670 | 5920 | +40.1% |
| CSV | 3095 | 10550 | 11040 | +172.0% |
| gettext PO | 1368 | 4656 | 4906 | +20.2% |
| Fluent | 1716 | 5726 | 5976 | +50.8% |
| YAML | 1288 | 4344 | 4594 | +13.2% |
| TOML | 1345 | 4271 | 4521 | +18.2% |

CLIFF 1.1 使用 **1138** token（主文件 + 术语表）。其他 7 种格式平均为 **1785.9** token。CLIFF 相对该平均值节省 **36.3%**。

**结果：PASS**（门槛为相对其他 7 种格式平均值至少节省 30%）。

已写入 `tests/benchmark/fixtures/` 供公平性人工审计：

- `tests/benchmark/fixtures/cliff-main.cliff`
- `tests/benchmark/fixtures/cliff-glossary.cliff`
- `tests/benchmark/fixtures/xliff.xlf`
- `tests/benchmark/fixtures/data.json`
- `tests/benchmark/fixtures/data.csv`
- `tests/benchmark/fixtures/data.po`
- `tests/benchmark/fixtures/data.ftl`
- `tests/benchmark/fixtures/data.yaml`
- `tests/benchmark/fixtures/data.toml`
