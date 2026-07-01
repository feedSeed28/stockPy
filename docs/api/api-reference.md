# API Reference

Base URL: `http://localhost:8000/api/v1`

Response format: `{ code: int, message: string, data: T | null }`

---

## Stocks

### `GET /stocks`
A股股票列表，分页 + 筛选。

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| exchange | string | - | SH / SZ / BJ |
| board_type | string | - | 主板 / 科创板 / 创业板 / 北交所 |
| is_active | bool | true | 是否仍上市 |
| keyword | string | - | 代码/名称模糊搜索 |
| page | int | 1 | 页码 |
| page_size | int | 50 (max 200) | 每页数量 |

### `GET /stocks/{code}`
单只股票基本信息。

### `GET /stocks/{code}/daily`
日K线数据。

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| adjust_type | string | qfq | qfq / hfq / none |
| start_date | date | - | 开始日期 |
| end_date | date | - | 结束日期 |
| page | int | 1 | 页码 |
| page_size | int | 200 (max 500) | 每页数量 |

### `GET /stocks/{code}/weekly`
周K线，参数同上。

### `GET /stocks/{code}/monthly`
月K线，参数同上。

### `GET /stocks/{code}/kline-range`
某只股票K线的日期范围。

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| period | string | daily | daily / weekly / monthly |
| adjust_type | string | qfq | 复权类型 |

### `GET /stocks/{code}/performance`
季度业绩报表。分页参数 `page`, `page_size`。

### `GET /stocks/{code}/financials`
详细财务指标（EPS、ROE、毛利率、增长率、偿债能力等）。分页参数 `page`, `page_size`。

### `GET /stocks/{code}/forecast`
最新一份分析师盈利预测。

### `GET /stocks/{code}/fund-flow`
每日资金流向（主力/大户/中户/小户净流入）。

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| start_date | date | - | 开始日期 |
| end_date | date | - | 结束日期 |
| page | int | 1 | 页码 |
| page_size | int | 50 (max 200) | 每页数量 |

---

## Boards

### `GET /boards`
行业/概念板块列表。

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| board_type | string | - | industry / concept |
| page | int | 1 | 页码 |
| page_size | int | 50 (max 200) | 每页数量 |

### `GET /boards/{board_id}/members`
板块成分股。分页参数 `page`, `page_size`。

---

## Quant

### `GET /quant/strategies`
可用回测策略列表及参数说明。

### `POST /quant/stocks/{code}/indicators`
计算技术指标。

```json
{
  "indicators": ["ma", "macd", "rsi", "boll"],
  "params": { "ma": {"period": 10} }
}
```

可用指标: `ma`, `ema`, `macd`, `rsi`, `kdj`, `boll`, `atr`, `obv`, `volume_ma`

### `POST /quant/screener`
多条件选股筛选。

```json
{
  "conditions": [
    {"field": "roe", "op": "gt", "value": 15},
    {"field": "ma_cross", "op": "golden", "params": {"fast": 5, "slow": 20}}
  ],
  "sort_by": "code",
  "limit": 50
}
```

### `POST /quant/backtest`
策略回测。

```json
{
  "stock_code": "000001",
  "strategy": "ma_cross",
  "params": {"fast": 5, "slow": 20},
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000
}
```

策略: `ma_cross` (MA金叉), `macd` (MACD金叉), `rsi` (超买超卖)

---

## System

### `GET /health`
健康检查 → `{"code":200,"message":"ok","data":null}`

### `GET /docs`
Swagger UI（交互式 API 文档）
