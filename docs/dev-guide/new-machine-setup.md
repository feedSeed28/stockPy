# New Machine Quick Setup

适用于换电脑、重装系统、或多台电脑同步开发。

## 前置条件

- Python 3.12+
- MySQL 8（Docker 或原生）
- Git

## 三步启动

```bash
# 1. 克隆项目
git clone <repo-url> stock_py && cd stock_py

# 2. 安装依赖
pip install -r backend/requirements.txt

# 3. 一键安装（依赖 + 配置文件 + 建表）
make setup
# 按提示启动 MySQL 后再继续
```

## 启动 MySQL

**有 Docker：**
```bash
docker-compose up -d mysql
```

**原生 MySQL 8（手动创建库）：**
```sql
CREATE DATABASE stock_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'ZggDLAXkkHXFwQVM';
GRANT ALL PRIVILEGES ON stock_data.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
```

## 建表

```bash
cd backend
alembic upgrade head
```

## 同步数据（一次性，~46 分钟）

```bash
# 完整历史数据同步
PYTHONUTF8=1 python scripts/sync_full.py
```

同步期间可以新开一个终端启动后端：
```bash
cd backend
PYTHONUTF8=1 uvicorn app.main:app --reload --port 8000
```

## 验证

```bash
curl http://localhost:8000/api/v1/health
# → {"code":200,"message":"ok","data":null}

curl http://localhost:8000/api/v1/stocks?page_size=3
# → 返回股票列表

curl http://localhost:8000/api/v1/stocks/000001/daily?page_size=3
# → 返回平安银行日K线
```

## 后续日常

- 启动后端：`make dev-backend`（或 `make dev-backend PYTHON=python`）
- 调度器每天 16:00 自动增量同步
- 查看同步状态：`make sync-status`

## Windows 注意

Makefile 默认 `python3`，Windows 上需指定：
```bash
make dev-backend PYTHON=python
make sync-status PYTHON=python
```

## 同步进度查询

```bash
cd backend && PYTHONUTF8=1 python -c "
import asyncio
from app.core.database import async_session
from sqlalchemy import select
from app.models.sync_status import SyncStatus

async def main():
    async with async_session() as db:
        r = await db.execute(select(SyncStatus))
        for s in r.scalars().all():
            print(f'{s.table_name:30s} {s.status:8s}  {s.row_count:>10,} rows  last: {s.last_data_date}')

asyncio.run(main())
"
```
