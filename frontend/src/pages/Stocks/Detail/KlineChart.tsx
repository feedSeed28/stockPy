/** ECharts candlestick chart — 直连模式优先东方财富K线API */

import { useEffect, useState } from "react";
import { DatePicker, Radio, Space, Spin, Tag, Empty, message } from "antd";
import { getStockDataProvider } from "@/services/dataProvider";
import type { KlineBar } from "@/services/typings";
import dayjs from "dayjs";
import ReactECharts from "echarts-for-react";

const { RangePicker } = DatePicker;
type Period = "daily" | "weekly" | "monthly";

interface Props { code: string; }

export default function KlineChart({ code }: Props) {
  const [period, setPeriod] = useState<Period>("daily");
  const [data, setData] = useState<KlineBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);
  const [source, setSource] = useState<"db" | "live">("db");

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    setDateRange(null);
    const provider = getStockDataProvider();

    if (provider.mode === "direct") {
      provider.getKline(code, { period, page_size: 500 })
        .then((res) => {
          setData(res.items);
          if (res.items.length > 0) {
            const first = res.items[0].trade_date;
            const last = res.items[res.items.length - 1].trade_date;
            setDateRange([first, last]);
          }
          setSource("live");
        })
        .catch(() => message.error("K线加载失败"))
        .finally(() => setLoading(false));
      return;
    }

    // ── 后端模式 ──
    provider.getKlineRange(code, period).then((range) => {
      if (range.max_date) {
        const end = dayjs(range.max_date);
        const start = end.subtract(180, "day");
        setDateRange([start.format("YYYY-MM-DD"), end.format("YYYY-MM-DD")]);
        provider.getKline(code, {
          period,
          start_date: start.format("YYYY-MM-DD"),
          end_date: end.format("YYYY-MM-DD"),
          page_size: 500,
        }).then((res) => {
          setData(res.items);
          setSource("db");
        }).catch(() => message.error("K线加载失败"))
          .finally(() => setLoading(false));
      } else {
        provider.getKline(code, { period, page_size: 500 }).then((res) => {
          setData(res.items);
          setSource("db");
        }).catch(() => message.error("K线加载失败"))
          .finally(() => setLoading(false));
      }
    }).catch(() => {
      provider.getKline(code, { period, page_size: 500 }).then((res) => {
        setData(res.items);
        setSource("db");
      }).catch(() => message.error("K线加载失败"))
        .finally(() => setLoading(false));
    });
  }, [code, period]);

  if (!loading && data.length === 0) {
    return <Empty description="暂无K线数据" />;
  }

  const filtered = dateRange
    ? data.filter((d) => d.trade_date >= dateRange[0] && d.trade_date <= dateRange[1])
    : data;

  const dates = filtered.map((d) => d.trade_date);
  const ohlc = filtered.map((d) => [d.open, d.close, d.low, d.high]);
  const vols = filtered.map((d) => ({
    value: d.volume,
    itemStyle: { color: d.close >= d.open ? "#ef232a" : "#14b143" },
  }));

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Radio.Group value={period} onChange={(e) => setPeriod(e.target.value)} optionType="button" buttonStyle="solid">
          <Radio value="daily">日K</Radio>
          <Radio value="weekly">周K</Radio>
          <Radio value="monthly">月K</Radio>
        </Radio.Group>
        <RangePicker
          value={dateRange ? [dayjs(dateRange[0]), dayjs(dateRange[1])] : null}
          onChange={(dates) => {
            if (dates?.[0] && dates?.[1]) {
              setDateRange([dates[0].format("YYYY-MM-DD"), dates[1].format("YYYY-MM-DD")]);
            } else {
              setDateRange(null);
            }
          }}
        />
        {source === "live" && <Tag color="orange">🔥 直连</Tag>}
      </Space>

      <Spin spinning={loading}>
        {filtered.length > 0 && (
          <ReactECharts
            style={{ height: 550 }}
            option={{
              grid: [
                { left: "8%", right: "2%", top: "2%", height: "55%" },
                { left: "8%", right: "2%", top: "68%", height: "22%" },
              ],
              xAxis: [
                { type: "category", data: dates, gridIndex: 0, axisLabel: { show: false } },
                { type: "category", data: dates, gridIndex: 1, axisLabel: { rotate: 30, fontSize: 10 } },
              ],
              yAxis: [
                { type: "value", gridIndex: 0, scale: true },
                { type: "value", gridIndex: 1, scale: true },
              ],
              series: [
                {
                  type: "candlestick", xAxisIndex: 0, yAxisIndex: 0, data: ohlc,
                  itemStyle: { color: "#ef232a", color0: "#14b143", borderColor: "#ef232a", borderColor0: "#14b143" },
                },
                { type: "bar", xAxisIndex: 1, yAxisIndex: 1, data: vols },
              ],
            }}
            notMerge
            lazyUpdate
          />
        )}
      </Spin>
    </div>
  );
}
