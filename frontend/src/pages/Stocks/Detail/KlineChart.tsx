/** ECharts candlestick chart + volume bar for daily/weekly/monthly K-line. */

import { useEffect, useState } from "react";
import { DatePicker, Radio, Space, Spin, message } from "antd";
import ReactECharts from "echarts-for-react";
import dayjs from "dayjs";
import { fetchKline, fetchKlineRange } from "@/services/stock";
import type { KlineBar } from "@/services/typings";

const { RangePicker } = DatePicker;

type Period = "daily" | "weekly" | "monthly";

interface Props {
  code: string;
}

export default function KlineChart({ code }: Props) {
  const [period, setPeriod] = useState<Period>("daily");
  const [data, setData] = useState<KlineBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<[string, string] | null>(null);

  useEffect(() => {
    if (!code) return;
    setLoading(true);

    fetchKlineRange(code, period)
      .then((range) => {
        if (range.max_date) {
          // Default: last 120 trading days
          const end = dayjs(range.max_date);
          const start = end.subtract(180, "day");
          setDateRange([start.format("YYYY-MM-DD"), end.format("YYYY-MM-DD")]);
        }
      })
      .catch(() => {});

    fetchKline(code, { period, page_size: 500 })
      .then((res) => setData(res.items.reverse())) // oldest first for chart
      .catch(() => message.error("Failed to load K-line"))
      .finally(() => setLoading(false));
  }, [code, period]);

  const filtered = dateRange
    ? data.filter(
        (d) => d.trade_date >= dateRange[0] && d.trade_date <= dateRange[1]
      )
    : data;

  const option = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
    },
    axisPointer: {
      link: [{ xAxisIndex: "all" }],
    },
    grid: [
      { left: "8%", right: "2%", top: "2%", height: "60%" },
      { left: "8%", right: "2%", top: "72%", height: "20%" },
    ],
    xAxis: [
      {
        type: "category",
        data: filtered.map((d) => d.trade_date),
        gridIndex: 0,
        axisLabel: { show: false },
      },
      {
        type: "category",
        data: filtered.map((d) => d.trade_date),
        gridIndex: 1,
        axisLabel: { rotate: 30, fontSize: 10 },
      },
    ],
    yAxis: [
      {
        type: "value",
        gridIndex: 0,
        scale: true,
        splitArea: { show: true },
      },
      {
        type: "value",
        gridIndex: 1,
        scale: true,
      },
    ],
    series: [
      {
        name: "K线",
        type: "candlestick",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: filtered.map((d) => [d.open, d.close, d.low, d.high]),
        itemStyle: {
          color: "#ef232a",
          color0: "#14b143",
          borderColor: "#ef232a",
          borderColor0: "#14b143",
        },
      },
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: filtered.map((d) => {
          const isUp = d.close >= d.open;
          return {
            value: d.volume,
            itemStyle: { color: isUp ? "#ef232a" : "#14b143" },
          };
        }),
      },
    ],
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Radio.Group
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          optionType="button"
          buttonStyle="solid"
        >
          <Radio.Button value="daily">日K</Radio.Button>
          <Radio.Button value="weekly">周K</Radio.Button>
          <Radio.Button value="monthly">月K</Radio.Button>
        </Radio.Group>
        <RangePicker
          value={
            dateRange
              ? [dayjs(dateRange[0]), dayjs(dateRange[1])]
              : undefined
          }
          onChange={(dates) => {
            if (dates && dates[0] && dates[1]) {
              setDateRange([
                dates[0].format("YYYY-MM-DD"),
                dates[1].format("YYYY-MM-DD"),
              ]);
            } else {
              setDateRange(null);
            }
          }}
        />
      </Space>
      <Spin spinning={loading}>
        <ReactECharts
          option={option}
          style={{ height: 550 }}
          notMerge
          lazyUpdate
        />
      </Spin>
    </div>
  );
}
