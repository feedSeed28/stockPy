/** 今年 K 线统计：涨跌停次数 + 大涨大跌天数 */

import { Card, Col, Row, Spin, Statistic } from "antd";
import { ArrowUpOutlined, ArrowDownOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { getStockDataProvider } from "@/services/dataProvider";

interface Props {
  code: string;
}

interface Stats {
  limitUp: number;
  limitDown: number;
  up5pct: number;
  down5pct: number;
  totalDays: number;
}

/** 根据代码判断涨跌停阈值 */
function getLimitPct(code: string): number {
  // 科创板 + 创业板 → 20%
  if (code.startsWith("688")) return 20;
  if (code.startsWith("300") || code.startsWith("301")) return 20;
  // 主板 → 10%
  return 10;
}

function computeStats(
  changes: number[],
  limitPct: number,
): Stats {
  let limitUp = 0;
  let limitDown = 0;
  let up5pct = 0;
  let down5pct = 0;

  for (const pct of changes) {
    if (pct >= limitPct - 0.2) limitUp++;
    if (pct <= -(limitPct - 0.2)) limitDown++;
    if (pct >= 5) up5pct++;
    if (pct <= -5) down5pct++;
  }

  return { limitUp, limitDown, up5pct, down5pct, totalDays: changes.length };
}

export default function YearStats({ code }: Props) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    setError(null);

    const provider = getStockDataProvider();
    const thisYear = new Date().getFullYear().toString();

    provider
      .getKline(code, {
        period: "daily",
        start_date: `${thisYear}-01-01`,
        end_date: `${thisYear}-12-31`,
        page_size: 300,
      })
      .then((res) => {
        if (!res.items.length) {
          setError("暂无数据");
          return;
        }
        const changes = res.items
          .filter((b) => b.change_pct != null)
          .map((b) => b.change_pct!);
        const limitPct = getLimitPct(code);
        setStats(computeStats(changes, limitPct));
      })
      .catch(() => setError("加载失败"))
      .finally(() => setLoading(false));
  }, [code]);

  if (loading) return <Spin size="small" />;
  if (error) return <span style={{ color: "#999" }}>{error}</span>;
  if (!stats) return null;

  return (
    <Row gutter={16} style={{ marginBottom: 16 }}>
      <Col span={6}>
        <Card size="small" style={{ background: "#fff7e6" }}>
          <Statistic
            title="今年涨停"
            value={stats.limitUp}
            prefix={<ArrowUpOutlined />}
            valueStyle={{
              color: stats.limitUp > 0 ? "#cf1322" : "#999",
              fontSize: 20,
            }}
            suffix={`/ ${stats.totalDays}天`}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small" style={{ background: "#e6fffb" }}>
          <Statistic
            title="今年跌停"
            value={stats.limitDown}
            prefix={<ArrowDownOutlined />}
            valueStyle={{
              color: stats.limitDown > 0 ? "#3f8600" : "#999",
              fontSize: 20,
            }}
            suffix={`/ ${stats.totalDays}天`}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small" style={{ background: "#fff2f0" }}>
          <Statistic
            title="涨幅 ≥5%"
            value={stats.up5pct}
            valueStyle={{
              color: stats.up5pct > 0 ? "#cf1322" : "#999",
              fontSize: 20,
            }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small" style={{ background: "#f6ffed" }}>
          <Statistic
            title="跌幅 ≥5%"
            value={stats.down5pct}
            valueStyle={{
              color: stats.down5pct > 0 ? "#3f8600" : "#999",
              fontSize: 20,
            }}
          />
        </Card>
      </Col>
    </Row>
  );
}
