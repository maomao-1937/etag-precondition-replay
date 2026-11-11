# etag-precondition-replay

Replay why an origin would continue a saved request or stop at HTTP 304 or 412. Give it the request method, the current selected representation and the two ETag conditions. It runs locally and prints the decisive condition without printing the tags.

## Quick start

Use Python 3.11 or later. Clone the repository or unpack its source archive. There are no dependencies or environment variables to configure.

```sh
git clone https://github.com/maomao-1937/etag-precondition-replay.git
cd etag-precondition-replay
python etag_precondition_replay.py examples/weak-write.json
```

```json
{"status":"short_circuit","http_status":412,"precondition":"if_match"}
```

The fixture has a weak current ETag and a matching opaque value in `If-Match`. Strong comparison fails even when the two opaque values agree. Compare the fixtures below.

| Command suffix | Exit | Decision |
|---|---:|---|
| `examples/weak-write.json` | 1 | `If-Match` stops the write with 412 |
| `examples/weak-read.json` | 1 | `If-None-Match` stops GET with 304 |
| `examples/create-absent.json` | 0 | `If-None-Match: *` permits the request to continue |
| `examples/invalid-mixed-list.json` | 2 | Wildcard mixed with entity tags is an invalid fixture |

## Fixture and output

Supply exactly the keys shown below in a strict UTF-8 JSON object up to 256 KiB. A JSON BOM or duplicate key is invalid. `exists` denotes whether there is a current selected representation. Set `etag` to `null` if it has no tag or the representation is absent. Use `null` for an absent condition and a string for a captured header value. The method is a case-sensitive ASCII HTTP token up to 64 characters. Each header value may be up to 8,192 characters.

```json
{
  "method": "PATCH",
  "exists": true,
  "etag": "W/\"rev7\"",
  "if_match": "\"rev7\"",
  "if_none_match": null
}
```

`If-Match` uses strong comparison and is evaluated first. `If-None-Match` uses weak comparison. A matching `If-None-Match` produces 304 for `GET` or `HEAD` and 412 otherwise. A whole-value `*` checks existence independently of `etag`. The lists allow up to 128 comma-delimited positions, including empty positions, and commas within quoted tags stay inside the tag. Use U+0080 through U+00FF to represent corresponding HTTP obs-text octets. Field names are fixed in the JSON output.

| Exit | Output |
|---:|---|
| 0 | `{"status":"continue","http_status":null,"precondition":null}` |
| 1 | `status` is `short_circuit`, `http_status` is 304 or 412, and `precondition` is `if_match` or `if_none_match` |
| 2 | `{"status":"invalid"}` for an invalid or unreadable fixture. An unavailable stdout also returns 2. |

The replay starts after normal origin checks permit evaluating preconditions. It covers ETag comparisons and precedence. Date conditions, range processing, cache-specific behavior and already-applied writes are outside its scope. A `continue` decision leaves the final HTTP status to the application. Use saved regular files on a trusted local filesystem. The CLI rejects common URL, UNC and Windows device spellings, and follows ordinary OS link resolution.

The comparison rules are in [RFC 9110 §8.8.3.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3.2) and [§13.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.2.2). The weak-write fixture is original and illustrates the rule behind [KOReader issue #15707](https://github.com/koreader/koreader/issues/15707).

## 中文

从保存的请求条件和当前表示重放源站的 ETag 判断。输出继续处理、304 或 412，并指出触发的条件字段。输出省略原始标签、请求方法和文件路径。

安装 Python 3.11 或更高版本，克隆仓库或解压源码后运行 `python etag_precondition_replay.py examples/weak-write.json`。无需安装第三方依赖或配置环境变量。示例退出码为 1，JSON 报告 `if_match` 触发 412。可对照上表运行读取、创建和无效输入示例。

输入为最多 256 KiB 的严格 UTF-8 JSON 对象，字段必须与上方样本一致。`exists` 表示当前选定表示是否存在。没有当前标签或表示时，`etag` 填 `null`。缺席的条件字段也填 `null`，已有条件填保存的头值。方法名区分大小写，最多 64 个 ASCII token 字符。每个头值最多 8,192 个字符。标签列表最多 128 个逗号分隔位置，包含空位置。引号内的逗号属于标签。

先判断 `If-Match` 的强匹配，再判断 `If-None-Match` 的弱匹配。整个头值为 `*` 时只看表示是否存在。退出码 0 表示继续，1 表示返回 304 或 412，2 表示输入无效、读取失败或无法输出。该工具从源站常规请求检查已允许评估条件的位置开始。日期条件、Range、缓存角色和写操作已成功的例外超出范围。请使用可信本地文件系统中的普通文件。

运行 `python -I -m unittest discover -s tests -v` 和 `python -I examples/run_examples.py` 可验证测试与示例。本地实测环境为 Windows、Python 3.11.15。代码和原始样本使用 [MIT 许可证](LICENSE)。
