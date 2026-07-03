/** Backtest page — configure strategy, run backtest, view results. */

import { PageContainer } from "@ant-design/pro-components";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  message,
} from "antd";
import ReactECharts from "echarts-for-react";
import { useState } from "react";
import { runBacktest, fetchStrategies } from "@/services/stock";

const STRATEGY_OPTIONS = [
  { label: "MA均线金叉", value: "ma_cross" },
  { label: "MACD金叉", value: "macd" },
  { label: "RSI超买超卖", value: "rsi" },
];

export default function BacktestPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleRun = async () => {
    const values = form.getFieldsValue();
    setLoading(true);
    try {
      const res = await runBacktest({
        stock_code: values.stock_code || "000001",
        strategy: values.strategy || "ma_cross",
        params: values.fast ? { fast: values.fast, slow: values.slow } : undefined,
        initial_capital: values.initial_capital || 100000,
      });
      setResult(res);
      message.success("Backtest complete");
    } catch {
      message.error("Backtest failed");
    } finally {
      setLoading(false);
    }
  };

  const equityOption = result
    ? {
        tooltip: { trigger: "axis" },
        grid: { left: "8%", right: "4%", top: "4%", bottom: "8%" },
        xAxis: {
          type: "category",
          data: result.equity_curve?.map((e: any) => e.date) || [],
        },
        yAxis: { type: "value" },
        series: [
          {
            name: "权益",
            type: "line",
            data: result.equity_curve?.map((e: any) => e.equity) || [],
            smooth: true,
            areaStyle: { opacity: 0.1 },
          },
        ],
      }
    : {};

  const tradeColumns = [
    { title: "买入日期", dataIndex: "buy_date", key: "buy_date", width: 110 },
    { title: "买入价", dataIndex: "buy_price", key: "buy_price", width: 80 },
    { title: "卖出日期", dataIndex: "sell_date", key: "sell_date", width: 110 },
    { title: "卖出价", dataIndex: "sell_price", key: "sell_price", width: 80 },
    {
      title: "盈亏",
      dataIndex: "pnl_pct",
      key: "pnl_pct",
      width: 90,
      render: (v: number) => (
        <span style={{ color: v > 0 ? "red" : "green" }}>
          {v?.toFixed(2)}%
        </span>
      ),
    },
  ];

  return (
    <PageContainer>
      <Row gutter={16}>
        <Col span={8}>
          <Card title="策略配置">
            <Form form={form} layout="vertical" initialValues={{
              stock_code: "000001", strategy: "ma_cross", fast: 5, slow: 20, initial_capital: 100000
            }}>
              <Form.Item label="股票代码" name="stock_code">
                <Input placeholder="000001" />
              </Form.Item>
              <Form.Item label="策略" name="strategy">
                <Select options={STRATEGY_OPTIONS} />
              </Form.Item>
              <Form.Item label="快线周期" name="fast">
                <InputNumber min={2} max={60} />
              </Form.Item>
              <Form.Item label="慢线周期" name="slow">
                <InputNumber min={5} max={120} />
              </Form.Item>
              <Form.Item label="初始资金" name="initial_capital">
                <InputNumber min={1000} step={10000} style={{ width: "100%" }} />
              </Form.Item>
              <Button
                type="primary"
                onClick={handleRun}
                loading={loading}
                block
              >
                ▶ 运行回测
              </Button>
            </Form>
          </Card>
        </Col>

        <Col span={16}>
          <Spin spinning={loading}>
            {result ? (
              <>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={6}>
                    <Card>
                      <Statistic title="总收益" value={result.total_return_pct} suffix="%" precision={2}
                        valueStyle={{ color: result.total_return_pct > 0 ? "#cf1322" : "#3f8600" }} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic title="年化收益" value={result.annual_return_pct} suffix="%" precision={2} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic title="最大回撤" value={result.max_drawdown_pct} suffix="%" precision={2}
                        valueStyle={{ color: "#cf1322" }} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic title="夏普比率" value={result.sharpe_ratio} precision={2} />
                    </Card>
                  </Col>
                </Row>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={8}>
                    <Card><Statistic title="胜率" value={result.win_rate_pct} suffix="%" precision={1} /></Card>
                  </Col>
                  <Col span={8}>
                    <Card><Statistic title="交易次数" value={result.trade_count} /></Card>
                  </Col>
                  <Col span={8}>
                    <Card><Statistic title="最终权益" value={result.final_equity} precision={2} /></Card>
                  </Col>
                </Row>
                <Card title="权益曲线" style={{ marginBottom: 16 }}>
                  <ReactECharts option={equityOption} style={{ height: 300 }} />
                </Card>
                <Card title="交易记录">
                  <Table dataSource={result.trades} columns={tradeColumns} rowKey="buy_date"
                    pagination={{ pageSize: 10 }} size="small" />
                </Card>
              </>
            ) : (
              <Card>
                配置策略参数后点击"运行回测"
              </Card>
            )}
          </Spin>
        </Col>
      </Row>
    </PageContainer>
  );
}
