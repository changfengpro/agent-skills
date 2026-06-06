# 内容范式：故障五段式、git diff 切分、术语表、速查表

## 1. 故障五段式（文档的核心价值所在）

每个问题/故障按固定五段组织。这个结构的价值：读者拿着自己的日志，能沿着 现象→解析→根因 的路径自己定位，而不是只抄解决方案。

```
x.y.1 故障现象     —— 日志/命令输出【原文】，放代码块。不要清洗、不要改写，
                     读者将来是拿自己的日志与此比对的。
x.y.2 逐条解析     —— 对日志中每条关键报错：加粗报错关键词，说明【谁】在调用
                     【谁】、期望得到什么、为什么失败（例如返回 -ENOIOCTLCMD
                     的机制）。一条报错一段。
x.y.3 根因分析     —— 机制层面的解释。最好能给出数值推导（例如
                     688+1920=2608 > 1920 → 判定越界），让结论可检验。
x.y.4 解决方案     —— 改了什么 + 为什么这样改 + 真实 git diff（见下节）。
x.y.5 验证结果     —— 命令 + 实测输出原文 + 判定标准（精确数字：
                     "46,656,000 字节 = 1920×1080×1.5×15 帧"）。
```

简单问题可以合并段落（如现象与解析合写），但"根因"和"验证"不可省。

## 2. 解决方案配真实 git diff

**原则**：文档里的代码必须可复核——直接从 commit 提取，不凭记忆重写。

按 hunk 切分到对应小节的方法（一个 commit 往往覆盖文档的多个小节）：

```python
import subprocess
from html import escape

def gitshow(commit, path):
    return subprocess.run(['git','show',commit,'--',path],
                          capture_output=True, text=True).stdout

def split_hunks(diff):
    """拆出 (---/+++ 头, [每个 @@ hunk 的文本])"""
    hdr, hunks, cur = [], [], None
    for ln in diff.split('\n'):
        if ln.startswith(('--- ','+++ ')): hdr.append(ln)
        elif ln.startswith('@@'):
            if cur: hunks.append('\n'.join(cur))
            cur = [ln]
        elif cur is not None: cur.append(ln)
    if cur: hunks.append('\n'.join(cur))
    return hdr, hunks

# 按关键词把 hunk 分到各小节，例如：
# 'VBLANK_MIN' in h        → vblank 小节
# 'of_property_read' in h  → probe 小节
# 其余                      → ioctl 小节
```

呈现方式：
- **飞书**：`<pre lang="Diff" caption="git diff <commit> — <主题>（节选）">`，Diff 高亮自动给 +/- 行着色。
- **Markdown**：```` ```diff ```` 围栏。
- caption/引导句标注来源 commit 短哈希，保证可追溯。
- 保留 `--- / +++ / @@` 头与上下文行，与 `git show` 输出一致。
- 与 diff 等价的"最终代码 + 行尾注释"形式仅在用户明确不要 diff 时使用。

## 3. 术语表（附录）

三列：术语 | 全称 | 说明。规则：

- 正文出现过的**每个缩写**都要进表（CIF、ISP、3A、AE、D-PHY、V4L2…）。
- 全称写英文原文，必要时附中文（如 "AE（Auto Exposure）/ AWB（Auto White Balance）"）。
- 没有缩写的概念（如 "online 模式"）全称列写 "—"，靠说明列讲清。
- 说明列写它在本文档语境下的含义，不是泛义词典解释。

## 4. 故障速查总表

放在故障诊断章首，四列：故障现象 | 根本原因 | 解决方案 | 详见。

- 一行一个问题，覆盖正文出现过的全部问题（包括"预防项"——还没踩到但机制上必然踩的坑，标注"预防项"）。
- "详见"列填真实小节号，写完后逐个核对存在性。

## 5. 图表

- 整体架构/信号链路/流程优先用图（飞书用画板，Markdown 用 mermaid 或 ASCII）。
- 图编号 `图 <章>-<序>`，编号行放图的紧邻位置。
- 表格前要有一句引导（"……差异如下："），不要裸表。
