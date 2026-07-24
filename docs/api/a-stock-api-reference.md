# A 股数据接口参考文档

本项目实际使用的数据源和可用接口汇总。

---

## 一、数据源总览

| 数据源 | 服务器可用 | 浏览器可用(CORS) | 最适合场景 |
|--------|-----------|-----------------|-----------|
| 东方财富 push2 | ⚠️ 部分受限 | ✅ 完全可用 | 实时行情、个股快照 |
| 东方财富 push2his | ❌ TLS阻断 | ✅ 完全可用 | 历史K线(服务器IP被封) |
| 东方财富 datacenter | ✅ 可用 | ✅ 可用 | 财务数据、业绩报表 |
| 东方财富 datacenter-web | ✅ 可用 | ✅ 可用 | 业绩报表、利润表 |
| 新浪 Sina | ⚠️ 批量被封 | ❌ 无CORS | 服务器单条K线查询 |
| 同花顺 | ✅ 可用 | — | 板块数据 |

---

## 二、东方财富 API（主力数据源）

### 2.1 实时行情

**端点**：`https://push2.eastmoney.com/api/qt/stock/get`

| 参数 | 说明 | 示例 |
|------|------|------|
| `secid` | 交易所.代码（1=上证, 0=深证, 0=北证） | `1.600519` |
| `fields` | 返回字段，逗号分隔 | `f43,f44,f45,f46` |
| `fltt` | 过滤类型 | `2` |
| `invt` | 投资类型 | `2` |

**常用 fields**：

| 字段 | 含义 | 字段 | 含义 |
|------|------|------|------|
| f43 | 最新价 | f44 | 最高价 |
| f45 | 最低价 | f46 | 开盘价 |
| f47 | 成交量(手) | f48 | 成交额 |
| f57 | 股票代码 | f58 | 股票名称 |
| f60 | 昨收价 | f116 | 总市值 |
| f117 | 流通市值 | f162 | 市盈率(动) |
| f167 | 市净率 | f168 | 换手率 |
| f169 | 涨跌额 | f170 | 涨跌幅 |
| f171 | 振幅 | | |

**请求示例**：
```
GET https://push2.eastmoney.com/api/qt/stock/get?fltt=2&invt=2&secid=1.600519&fields=f43,f57,f58,f170
```

---

### 2.2 历史 K 线

**端点**：`https://push2his.eastmoney.com/api/qt/stock/kline/get`

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `secid` | 交易所.代码 | `1.600519` / `0.000001` |
| `klt` | K线周期 | 101=日, 102=周, 103=月, 1/5/15/30/60=分钟 |
| `fqt` | 复权 | 0=不复权, 1=前复权, 2=后复权 |
| `beg` | 起始日期 | `20240101` |
| `end` | 截止日期 | `20991231` |
| `lmt` | 返回条数 | 最大 1000000 |
| `fields2` | K线数据字段 | `f51,f52,f53,f54,f55,f56,f57` |

**fields2 字段映射**：

| 字段 | 含义 | 字段 | 含义 |
|------|------|------|------|
| f51 | 日期 | f52 | 开盘 |
| f53 | 收盘 | f54 | 最高 |
| f55 | 最低 | f56 | 成交量 |
| f57 | 成交额 | f58 | 振幅 |
| f59 | 涨跌幅 | f60 | 涨跌额 |
| f61 | 换手率 | | |

**请求示例**：
```
GET https://push2his.eastmoney.com/api/qt/stock/kline/get
  ?fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61
  &klt=101&fqt=1&beg=20240101&end=20260724&lmt=500
  &secid=1.600519
```

---

### 2.3 全市场行情列表

**端点**：`https://push2.eastmoney.com/api/qt/clist/get`

| 参数 | 说明 |
|------|------|
| `pn` | 页码 |
| `pz` | 每页条数 |
| `fs` | 市场过滤: `m:0+t:6,m:0+t:80` (深市主板+创业板) |
| `fields` | 返回字段(f3=涨跌幅, f12=代码, f14=名称等) |

**市场代码(fs参数)**：

| fs 值 | 市场 |
|-------|------|
| `m:1+t:2` | 上海主板 |
| `m:1+t:23` | 科创板 |
| `m:0+t:6` | 深圳主板 |
| `m:0+t:80` | 创业板 |
| `m:0+t:81` | 北交所 |

**请求示例**：
```
GET https://push2.eastmoney.com/api/qt/clist/get
  ?pn=1&pz=50&po=1&np=1&fltt=2&invt=2
  &fs=m:1+t:2,m:1+t:23,m:0+t:6,m:0+t:80
  &fields=f2,f3,f12,f14,f15,f16,f17,f18
```

---

### 2.4 资金流向

**每日资金流**：`https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get`

| 参数 | 说明 |
|------|------|
| `secid` | 交易所.代码 |
| `fields2` | `f51,f52,f53,f54,f55,f56` |

| 字段 | 含义 |
|------|------|
| f51 | 日期 |
| f52 | 主力净流入 |
| f53 | 小单净流入 |
| f54 | 中单净流入 |
| f55 | 大单净流入 |
| f56 | 超大单净流入 |

---

### 2.5 财务数据

**datacenter-web 端点**：`https://datacenter-web.eastmoney.com/api/data/v1/get`

| 参数 | 说明 |
|------|------|
| `reportName` | 报表名称(决定数据类型) |
| `columns` | 返回字段，`ALL` 获取全部 |
| `filter` | 过滤条件 `(字段="值")` |
| `pageSize` | 每页条数 |
| `sortColumns` | 排序字段 |
| `sortTypes` | `-1`=降序, `1`=升序 |

**常用 reportName**：

| reportName | 说明 |
|------------|------|
| `RPT_DMSK_FN_INCOME` | 利润表 |
| `RPT_DMSK_FN_BALANCE` | 资产负债表 |
| `RPT_DMSK_FN_CASHFLOW` | 现金流量表 |
| `RPT_F10_FINANCE_MAINFINADATA` | 主要财务指标(ROE/EPS/毛利率等) |

**filter 写法**：
```
(SECURITY_CODE="600519")                     # 指定股票
(DATE_TYPE_CODE="001")                       # 年报(去掉=所有报告期)
(REPORT_DATE>='2024-01-01')                  # 日期范围
```

**请求示例**：
```
GET https://datacenter-web.eastmoney.com/api/data/v1/get
  ?reportName=RPT_DMSK_FN_INCOME
  &columns=ALL
  &filter=(SECURITY_CODE="600519")
  &pageSize=50&pageNumber=1
  &sortColumns=REPORT_DATE&sortTypes=-1
```

**财务指标返回字段**（主要）：

| 字段 | 含义 | 字段 | 含义 |
|------|------|------|------|
| EPSJB | 基本每股收益 | EPSXS | 稀释每股收益 |
| ROEJQ | ROE(加权) | ZZCJLL | ROA |
| XSMLL | 销售毛利率 | XSJLL | 销售净利率 |
| TOTALOPERATEREVETZ | 营收增速 | PARENTNETPROFITTZ | 利润增速 |
| LD | 流动比率 | SD | 速动比率 |
| ZCFZL | 资产负债率 | BPS | 每股净资产 |
| MGJYXJJE | 每股经营现金流 | | |

---

### 2.6 板块数据

**行业板块**：`https://push2.eastmoney.com/api/qt/clist/get`

```python
# 行业板块列表
fs=m:90+t:2    # 概念板块 fs=m:90+t:3
# 板块成分股
fs=b:BK0001+t:2   # BK0001换成具体板块代码
```

**板块成分股字段**：`f2,f3,f12,f14,f15,f16,f17,f18,f20`

---

## 三、新浪财经 API

### 3.1 实时行情

**端点**：`http://hq.sinajs.cn/list=<codes>`

**请求头必须带**：`Referer: https://finance.sina.com.cn`

```bash
# 单只
curl -H "Referer: https://finance.sina.com.cn" \
  "http://hq.sinajs.cn/list=sh600519"

# 批量（逗号分隔）
curl -H "Referer: https://finance.sina.com.cn" \
  "http://hq.sinajs.cn/list=sh600519,sz000001"
```

**返回格式**（逗号分隔 VAR 字符串）：
```
var hq_str_sh600519="贵州茅台,1500.00,1495.00,1498.00,..."
```

字段顺序：名称 → 今开 → 昨收 → 现价 → 最高 → 最低 → 竞买价 → 竞卖价 → 成交股数 → 成交金额 → 买1-5(量+价) → 卖1-5(量+价) → 日期 → 时间

### 3.2 历史 K 线

**端点**：`http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData`

| 参数 | 说明 |
|------|------|
| `symbol` | `sh600519` / `sz000001` |
| `scale` | 240=日, 60=60分钟, 30=30分钟, 15=15分钟, 5=5分钟 |
| `ma` | 均线(5/10/20) |
| `datalen` | 返回条数(1-3000) |

**返回**：JSON 数组，每元素含 `day, open, high, low, close, volume`

> ⚠️ Sina K 线不支持复权调整，返回不复权数据。本项目服务器批量同步时被 Sina 封过IP。

---

## 四、AKShare 封装的接口

本项目通过 AKShare 调用上述 API。核心函数对照：

| AKShare 函数 | 底层数据源 | 对应上方接口 |
|-------------|-----------|-------------|
| `ak.stock_zh_a_hist()` | 东方财富 push2his | 2.2 历史K线 |
| `ak.stock_zh_a_daily()` | 新浪 | 3.2 新浪K线 |
| `ak.stock_zh_a_spot_em()` | 东方财富 clist | 2.3 全市场行情 |
| `ak.stock_financial_analysis_indicator_em()` | 东方财富 datacenter | 2.5 财务指标 |
| `ak.stock_yjbb_em()` | 东方财富 datacenter-web | 2.5 业绩报表 |
| `ak.stock_board_industry_name_em()` | 东方财富 | 2.6 板块 |
| `ak.stock_lhb_detail_daily_sina()` | 新浪 | 龙虎榜 |

---

## 五、其他数据源

### 5.1 Tushare（替代方案）

需要注册获取 Token，积分制（注册送礼120积分，够日用）。

```python
import tushare as ts
ts.set_token('your_token')
pro = ts.pro_api()

# 日线行情
df = pro.daily(trade_date='20260724')
# 全市场，单次最多4500条

# 股票列表
df = pro.stock_basic(exchange='', list_status='L')
```

- 免费用户：60次/分钟，批量建议 1s 间隔
- 地址：https://tushare.pro

### 5.2 BaoStock（替代方案）

无需注册，但仅支持不复权日线，且 2022 年后停止更新。
- `bs.query_history_k_data_plus()` — 历史 K 线
- `bs.query_stock_basic()` — 股票列表

---

## 六、关键注意事项

1. **东方财富 secid**：上证 `1.xxxxxx`，深证 `0.xxxxxx`，北证 `0.8xxxxx`（本项目中北交所被排除）
2. **字段名不固定**：不同 `reportName` 下字段名可能不同，建议先用 `columns=ALL` 查完整字段列表
3. **IP 限流**：东方财富和新浪均按 IP 限流，批量请求必须控制频率（建议 1-2 并发 + 1.5s 延迟）
4. **非交易时段**：晚间和周末访问某些东财接口可能需要 Cookie（`nid` 字段）
5. **CORS 说明**：东方财富接口均支持浏览器 CORS，新浪不支持（必须通过服务器代理）
6. **复权数据**：东方财富 K 线支持前复权/后复权，新浪不支持复权
