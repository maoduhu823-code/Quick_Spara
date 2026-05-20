# QS_runtime_services — 路径与汇总

试用授权 / 版本检查 / 用户资料 / 使用记录 / 评价反馈五个子系统共用一套路径配置（[path_config.py](path_config.py)），并由 [data_feedback_aggregator.py](data_feedback_aggregator.py) 把分散的小 JSON 合并成 summary Excel。

本文档目标：让发布方一眼看清「应用读哪里、写哪里、谁负责汇总」。

---

## 一、两种运行模式

启动时按 hostname + 命令行旗标决定模式：

```python
DEV_HOSTNAMES = {"DAVIDWORLD", "W00810255", "W00810255-NFWP"}  # 比对时统一 .upper()
# is_local_mode() = True 当且仅当：
#   socket.gethostname().upper() in DEV_HOSTNAMES, 或者
#   Quick_Sparam_B.py 带 --dev 旗标启动（force_local_mode(True)）
```

| 模式 | 谁会进入 | 路径策略 |
|---|---|---|
| **本机开发模式** | 白名单内的开发机；或 `--dev` 启动 | 全部路径落在程序基准目录旁的 `./Public/` |
| **分发模式** | 同事机、产线机 | 读 + 写两套共享路径；共享盘不可达时落到本机 `./Public/` 兜底 |

> 「程序基准目录」：源码运行 = 仓库根；PyInstaller 冻结 = exe 所在目录。

新增本机白名单 hostname：编辑 [path_config.py](path_config.py) 顶部 `DEV_HOSTNAMES` 集合，**用全大写形式**（运行时会把当前 hostname 转大写后比对）。

---

## 二、本机开发模式

读 + 写都在同一目录，零网络：

| 用途 | 路径 |
|---|---|
| 版本检查 | `./Public/version.json` |
| 试用授权 | `./Public/license.json` |
| 资料问卷 | `./Public/usage_profile.json` |
| inbox（必落地） | `./Public/data_feedback/inbox/` |
| usage summary | `./Public/data_feedback/Quick_Sparam_usage_summary.xlsx` |
| user_data summary | `./Public/data_feedback/Quick_Sparam_user_data_summary.xlsx` |
| feedback summary | `./Public/data_feedback/Quick_Sparam_feedback_summary.xlsx` |

> 仓库根 `Public/` 目录在 `.gitignore` 内（如不在请加上），避免把本机产生的数据提交回去。

---

## 三、分发模式

按平台分支，每个平台都有「读路径」+「写路径」+「本机兜底」三层。

### 3.1 Windows

| 类别 | 路径 |
|---|---|
| **读** version.json / license.json | `\\10.114.193.143\Public\` |
| **写** usage_profile.json / inbox/ / *.xlsx | `\\10.114.193.143\data_feedback\` |
| **本机兜底**（共享盘不可达时） | `.\Public\data_feedback\` |

### 3.2 Linux

| 类别 | 路径 |
|---|---|
| **读** version.json / license.json | `/data/hs_5023_public/Quick_Sparam/Public/` |
| **写** usage_profile.json / inbox/ / *.xlsx | `/data/hs_5023_public/Quick_Sparam/data_feedback/` |
| **本机兜底** | `./Public/data_feedback/` |

### 3.3 共享盘不可达时（A 报错 + B 兜底）

- inbox JSON 落到本机 `./Public/data_feedback/inbox/`，**不丢数据**。
- 不写本机 summary Excel（避免管理员与用户机各出一份）。
- 反馈 UI 的「提交成功」弹窗追加一行：
  > 无法自动发送文件，请联系管理员添加共享路径权限。
- 应用照常启动，不阻塞。

### 3.4 usage_profile.json 双写策略

```
启动：
  读本机 ./Public/usage_profile.json
  ├─ 本机为空           → 弹问卷 UI → 写本机 + 推共享 → 推送失败时弹一次性警告
  ├─ 本机完整、共享缺失 → 静默推送 → 推送失败时弹一次性警告
  └─ 本机完整、共享存在 → 无操作
```

**本机永远是唯一权威**，共享盘只是给管理员侧的同步副本。机 A 写过资料后到机 B 启动，机 B 仍然会弹问卷（不复用共享盘上的别人 profile）。

---

## 四、运行汇总脚本

入口：[data_feedback_aggregator.py](data_feedback_aggregator.py)。建议在仓库根或 Python 安装目录下跑，确保能找到 `QS_runtime_services` 包。

### 4.1 模式说明

| `--target` | 扫描的 inbox | 写入的 summary |
|---|---|---|
| `local` | 本机 `./Public/data_feedback/inbox/` | 本机 summary（仅本机模式才有；分发模式下兜底数据需要管理员手动复制到共享盘后再汇总） |
| `developer`（管理员侧） | Windows `\\10.114.193.143\data_feedback\inbox\` / Linux `/data/.../data_feedback/inbox/` | 共享盘 summary |
| `all`（默认） | 两者都扫 | 两者都写 |

### 4.2 命令

```bash
# 一次性汇总本机 inbox（用户机器上排错或开发机用）
python -m QS_runtime_services.data_feedback_aggregator --target local --once

# 一次性汇总共享盘 inbox（管理员手动跑一次）
python -m QS_runtime_services.data_feedback_aggregator --target developer --once

# 守护模式，每 600 秒扫一次共享盘（管理员侧建议挂成定时任务）
python -m QS_runtime_services.data_feedback_aggregator --target developer --interval-seconds 600

# 两边都扫一次
python -m QS_runtime_services.data_feedback_aggregator --once
```

### 4.3 行为约定

- summary Excel 写成功后，才会删除已合并的 inbox JSON——**写失败不丢数据**。
- 同一 `record_id` 已在 summary 中就跳过，**重复跑安全**。
- 附件目录 `attachments/{record_id}/` 不会被 aggregator 删除（保留原始证据）；如需清理，单独跑清理脚本或人工处理。
- 共享盘加锁：aggregator 用 inbox 目录下的 `.lock` 文件防多进程同时跑；如果 lock 残留导致跑不起来，删掉 `<inbox>/.lock` 即可。

---

## 五、修改路径时的注意事项

所有路径定义集中在 [path_config.py](path_config.py)。修改步骤：

1. 改完后跑 `python -m pytest tests/ -q` 验证；
2. 用以下脚本人眼核对一遍解析结果：

   ```bash
   python -c "from QS_runtime_services.path_config import \
              license_sources, version_sources, profile_paths, \
              inbox_dirs_primary, inbox_dirs_fallback; \
              print('license:', license_sources()); \
              print('version:', version_sources()); \
              print('profile:', profile_paths()); \
              print('inbox primary:', inbox_dirs_primary()); \
              print('inbox fallback:', inbox_dirs_fallback())"
   ```

3. 同步本文档对应表格（保持单一信息源）。

切忌在应用代码里直接拼路径——绕过 path_config 会让发布方无法在出问题时只动一处修复。
