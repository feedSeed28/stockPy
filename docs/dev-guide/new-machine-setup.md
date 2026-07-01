# New Machine Quick Setup

适用于换电脑、重装系统、或多台电脑同步开发。

## 前置条件

- Python 3.12+
- MySQL 8（Docker 或原生）
- Git

---

## 方案 A：数据库文件拷贝（最快，推荐）

从旧电脑导出 → 新电脑导入，不需要重新下载数据。

### 旧电脑导出

```bash
cd D:\project\stock_py\backend

# 导出全部数据（不含建表语句，约 2GB）
mysqldump -h localhost -u admin -pZggDLAXkkHXFwQVM --no-create-info --single-transaction stock_data > stock_data_dump.sql
```

拷贝 `stock_data_dump.sql` 到新电脑。

### 新电脑恢复

```bash
# 1. 克隆项目 + 装依赖 + 建表
git clone <repo-url> stock_py && cd stock_py
pip install -r backend/requirements.txt
cd backend
cp .env.example .env
alembic upgrade head

# 2. 导入数据（约 20 分钟）
mysql -h localhost -u admin -pZggDLAXkkHXFwQVM stock_data < stock_data_dump.sql
```

### 优缺点

| 优点 | 缺点 |
|------|------|
| 不消耗 AKShare API 配额 | 需要传输大文件（~2GB） |
| 速度快（~20 min vs ~2h） | 是快照，不含导出后新增的数据 |
| 100% 完整 | 两台电脑 MySQL 版本需接近 |

---

## 方案 B：重新同步（无需传文件）

从 AKShare 重新拉取所有数据。零文件传输，但耗时长。

### 步骤

```bash
# 1. 克隆项目 + 装依赖
git clone <repo-url> stock_py && cd stock_py
cd backend
pip install -r requirements.txt
cp .env.example .env

# 2. 启动 MySQL 并建表
#    有 Docker: docker-compose up -d mysql
#    原生 MySQL 手动创建库和用户（见下方）
alembic upgrade head

# 3. 同步日K线（最核心数据，约 2.5 小时）
set PYTHONUTF8=1
python scripts\sync_sina.py
```

### 同步命令速查

| 命令 | 耗时 | 说明 |
|------|------|------|
| `python scripts\sync_sina.py` | ~2.5h | 全部A股日K线（核心），支持断点续传 |
| `python scripts\sync_full.py` | ~3h+ | 全部数据（日/周/月K线+财报+板块），但东方财富源可能限流 |
| `python scripts\sync_stocks.py` | <1min | 仅更新股票列表 |
| `python scripts\sync_slow.py` | ~3h | 日K线单线程慢速版，抗限流但更慢 |

> **注意**：`scripts\sync_sina.py` 使用新浪数据源（稳定），`sync_full.py` 使用东方财富（容易限流）。
> 实际经验：新浪源稳定运行至 100% 无中断；东方财富源运行几分钟后 IP 被封。
>
> 所有脚本支持**断点续传**：中断后重跑会自动跳过已同步的股票。

### 启动 MySQL（原生安装）

```sql
CREATE DATABASE stock_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'ZggDLAXkkHXFwQVM';
GRANT ALL PRIVILEGES ON stock_data.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
```

---

## 验证

```bash
curl http://localhost:8000/api/v1/health
# → {"code":200,"message":"ok","data":null}

curl http://localhost:8000/api/v1/stocks?page_size=3
# → 返回股票列表

curl http://localhost:8000/api/v1/stocks/000001/daily?page_size=3
# → 返回平安银行日K线
```

---

## 查看同步进度

```bash
cd backend
set PYTHONUTF8=1
python -c "import pymysql; c=pymysql.connect(host='localhost',port=3306,user='admin',password='ZggDLAXkkHXFwQVM',database='stock_data'); r=c.cursor(); r.execute('SELECT COUNT(DISTINCT stock_code) FROM stock_daily_quote'); print(f'{r.fetchone()[0]}/5528 stocks'); c.close()"
```

---

## 方案对比

| | 方案 A（拷贝DB） | 方案 B（重同步） |
|---|---|---|
| 传输文件 | ~2GB .sql | 无 |
| 旧电脑操作 | 导出 5-10 min | 无 |
| 新电脑耗时 | 导入 ~20 min | 同步 ~2.5h |
| AKShare 依赖 | 不需要 | 需要网络 |
| 数据新鲜度 | 快照时间点 | 实时最新 |
| 断点续传 | N/A | ✅ 自动跳过已完成 |
| 适用场景 | 两台电脑都在手边 | 只有新电脑 |

**建议**：主电脑同步完成后导出一次 SQL 备份，其他电脑直接用方案 A 导入。
