# 开发期调试脚本

这里的脚本是开发 Web Studio 与 OWL/Neo4j 链路时用来临时排查问题的工具，
不属于安装包内容，也不参与 CI。它们的共同前提：

- 仓库根目录作为工作目录（`task_history.db`、`.litellm_cache/` 都按相对路径读取）；
- 已安装本项目的开发依赖，并且 `ontogpt` 可导入；
- 涉及 Neo4j 的脚本需要可用的图数据库实例，连接参数通过
  `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`、`NEO4J_DATABASE` 环境变量提供。

## 分类

| 前缀 | 用途 |
| --- | --- |
| `check_*` | 检查任务历史库或 OWL 图中的节点、关系、属性是否齐全 |
| `inspect_*` | 打印某次抽取结果、搜索命中或三元组细节 |
| `verify_*` | 校验去重、合并属性、链接解析的结果 |
| `debug_*` | 定位查询与链接生成过程中的异常 |
| `find_*` | 在结果中检索特定 LC 系统或等价类 |
| `test_*` | 手工验证 API、IRI 解析、RDF 到 Neo4j 的边生成 |
| `batch_upgrade_db.py` / `upgrade_task_in_db.py` | 历史库 schema 或结果字段的一次性升级 |
| `analyze_data_quality.py` | 抽取结果的字段完整度统计 |
| `resolve_links.py` | 批量重写结果中的实体链接 |
| `sample_lub_system.py` | 打印一份样例系统的抽取结构 |

这些脚本会直接读取或改写本地 `task_history.db`，运行前建议先备份该文件。
