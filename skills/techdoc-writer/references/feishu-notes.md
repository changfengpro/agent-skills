# 飞书落地实操经验（配合 lark-doc skill 使用）

写飞书前必读 lark-doc skill 本体（认证、XML 协议、+fetch/+update 细节以它为准）。本文是 techdoc-writer 场景下的踩坑经验补充。

## 1. 大改版的安全操作顺序

对已有文档做整体重构时，**先加后删、资源块只搬不删**：

```
① fetch --detail with-ids 全量拿 block 清单
② 识别资源块（whiteboard / figure+source 附件 / sheet / bitable）
   —— 这些删了就没了（附件 token 不可重建），必须保留
③ append 新结构到文档末尾
④ block_move_after 把资源块搬进新结构的对应位置
⑤ block_delete 批量删除旧 block（逗号分隔；删除清单在 ① 时就保存到文件）
⑥ fetch --scope outline 验证最终结构
```

不要用 overwrite —— 它会清空文档，画板、附件、评论全部丢失。

## 2. block 清单提取的坑

- 正则提取 id 会把**表格单元格里的 p** 也抓进来；删除时只需要顶层 block。
  用 XML 解析取 fragment 的**直接子元素**：
  ```python
  import xml.etree.ElementTree as ET
  root = ET.fromstring('<root>' + content + '</root>')
  for ch in root:            # 仅直接子元素
      bid = ch.get('id')
      # ul/ol 容器无 id，取其 li 子元素的 id
  ```
- 文档末尾常有一个编辑器自动生成的空 `<p>`（id 风格与 API 创建的不同），留着无害，别误删。

## 3. XML 转义与代码块

- 只转义文本内容，不转义标签本身：`&` → `&amp;`、`<` → `&lt;`、`>` → `&gt;`。
- 代码（dts 的 `<&gpio4 ...>`、C 的 `->`、diff 的上下文行）转义量大，**用程序生成**：
  `html.escape(code, quote=False)`，手写必漏。
- `<pre><code>` 里可以用真实换行，CLI 会自动转成 `<br/>`。
- diff 用 `lang="Diff"`；shell/日志用 `lang="Bash"`。
- 注释文字里不要出现裸的 `};` 之类片段——不影响解析，但会干扰后续用脚本做括号配平检查。

## 4. 局部修订

- 改一段 → `block_replace`（一次一个 block）；批量同文本 → `str_replace`。
- 插入代码块到既有章节 → 先 keyword fetch 拿锚点 id，再 `block_insert_after`。
  多个插入互不影响锚点 id，可顺序执行。
- 改文档标题（含 wiki 节点名）→ 对 title 文本 `str_replace` 即可。

## 5. 权限与授权

- 读文档需要 `docx:document:readonly`，写需要 `docx:document:write_only`
  （注意不是 `docx:document`——scope 名不对等于没授权）。
- 授权用 `auth login --scope ... --no-wait --json` 拿 verification_url，
  生成二维码发给用户，**结束本轮等用户确认**后再 `--device-code` 续上。
  device code 约 10 分钟过期，过期就重新发起，旧码作废。

## 6. 验证

- 结构：`fetch --scope outline --max-depth 2` 对照目录。
- 代码块：全文 fetch 后统计 `<pre ... caption>`，确认每个解决方案都有 diff、无旧版残留。
- 资源块：确认 whiteboard / figure 仍在且位置正确（outline 看不到资源块，需全文 fetch 或 keyword 定位）。
