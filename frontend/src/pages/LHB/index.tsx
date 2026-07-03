/** 龙虎榜 — daily list, institution detail, stock stats */

import { PageContainer } from "@ant-design/pro-components";
import { DatePicker, Select, Space, Table, Tabs, message, Tag } from "antd";
import { useNavigate } from "@umijs/max";
import { useEffect, useState } from "react";
import axios from "axios";
import dayjs from "dayjs";

export default function LHBPage() {
  const navigate = useNavigate();
  const [date, setDate] = useState(dayjs());
  const [reason, setReason] = useState<string | undefined>();
  const [reasons, setReasons] = useState<string[]>([]);
  const [dailyData, setDailyData] = useState<any[]>([]);
  const [institutionData, setInstitutionData] = useState<any[]>([]);
  const [statsData, setStatsData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadDaily = async () => {
    setLoading(true);
    try {
      const params: any = { date: date.format("YYYYMMDD") };
      if (reason) params.reason = reason;
      const { data } = await axios.get("/api/v1/lhb/daily", { params });
      if (data.code === 200) {
        setDailyData(data.data.items || []);
        setReasons(data.data.reasons || []);
      }
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  const loadInstitution = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get("/api/v1/lhb/institution");
      if (data.code === 200) setInstitutionData(data.data.items || []);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  const loadStats = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get("/api/v1/lhb/stock-stats", { params: { period: "5" } });
      if (data.code === 200) setStatsData(data.data.items || []);
    } catch { message.error("加载失败"); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadDaily(); }, [date, reason]);

  const dailyColumns = [
    { title: "代码", dataIndex: "code", key: "code", width: 100, copyable: true },
    { title: "名称", dataIndex: "name", key: "name", width: 100 },
    { title: "收盘价", dataIndex: "close", key: "close", width: 80 },
    { title: "对应值", dataIndex: "change_val", key: "change_val", width: 80,
      render: (v: number) => <span style={{ color: v > 0 ? "red" : "green" }}>{v}%</span> },
    { title: "成交额(万)", dataIndex: "amount", key: "amount", width: 120,
      render: (v: number) => (v ? (v / 10000).toFixed(0) : "-") },
    { title: "上榜原因", dataIndex: "reason", key: "reason", ellipsis: true },
  ];

  const instColumns = [
    { title: "代码", dataIndex: "code", key: "code", width: 100, copyable: true },
    { title: "名称", dataIndex: "name", key: "name", width: 100 },
    { title: "日期", dataIndex: "trade_date", key: "trade_date", width: 110 },
    { title: "机构买入(万)", dataIndex: "institution_buy", key: "institution_buy", width: 130,
      render: (v: number) => (v ? (v / 10000).toFixed(0) : "0") },
    { title: "机构卖出(万)", dataIndex: "institution_sell", key: "institution_sell", width: 130,
      render: (v: number) => (v ? (v / 10000).toFixed(0) : "0") },
    { title: "净买入(万)", key: "net", width: 120,
      render: (_: any, r: any) => {
        const net = (r.institution_buy || 0) - (r.institution_sell || 0);
        return <span style={{ color: net > 0 ? "red" : "green" }}>{(net / 10000).toFixed(0)}</span>;
      }},
    { title: "上榜原因", dataIndex: "reason", key: "reason", ellipsis: true },
  ];

  const statsColumns = [
    { title: "代码", dataIndex: "code", key: "code", width: 100, copyable: true },
    { title: "名称", dataIndex: "name", key: "name", width: 100 },
    { title: "上榜次数", dataIndex: "appear_count", key: "appear_count", width: 80,
      render: (v: number) => <Tag color={v > 3 ? "red" : "blue"}>{v}</Tag> },
    { title: "净买入(万)", dataIndex: "net_amount", key: "net_amount", width: 120,
      render: (v: number) => (v ? <span style={{ color: v > 0 ? "red" : "green" }}>{(v / 10000).toFixed(0)}</span> : "-") },
    { title: "累积购买额(万)", dataIndex: "total_buy", key: "total_buy", width: 140,
      render: (v: number) => (v ? (v / 10000).toFixed(0) : "-") },
    { title: "累积卖出额(万)", dataIndex: "total_sell", key: "total_sell", width: 140,
      render: (v: number) => (v ? (v / 10000).toFixed(0) : "-") },
  ];

  return (
    <PageContainer title="龙虎榜">
      <Tabs
        defaultActiveKey="daily"
        onChange={(key) => {
          if (key === "institution") loadInstitution();
          if (key === "stats") loadStats();
          if (key === "daily") loadDaily();
        }}
        items={[
          {
            key: "daily",
            label: "每日明细",
            children: (
              <Space direction="vertical" style={{ width: "100%" }}>
                <Space>
                  <DatePicker value={date} onChange={(d) => setDate(d || dayjs())} allowClear={false} />
                  <Select
                    placeholder="上榜原因（全部）"
                    allowClear
                    style={{ width: 300 }}
                    value={reason}
                    onChange={setReason}
                    options={reasons.map((r) => ({ label: r, value: r }))}
                  />
                </Space>
                <Table
                  dataSource={dailyData}
                  columns={dailyColumns}
                  rowKey="code"
                  loading={loading}
                  pagination={false}
                  scroll={{ y: 500 }}
                  onRow={(r) => ({ onClick: () => navigate(`/stocks/${r.code}`), style: { cursor: "pointer" } })}
                />
              </Space>
            ),
          },
          {
            key: "institution",
            label: "机构买卖",
            children: (
              <Table
                dataSource={institutionData}
                columns={instColumns}
                rowKey="code"
                loading={loading}
                pagination={{ pageSize: 30 }}
                scroll={{ y: 500 }}
                onRow={(r) => ({ onClick: () => navigate(`/stocks/${r.code}`), style: { cursor: "pointer" } })}
              />
            ),
          },
          {
            key: "stats",
            label: "个股统计(5日)",
            children: (
              <Table
                dataSource={statsData}
                columns={statsColumns}
                rowKey="code"
                loading={loading}
                pagination={{ pageSize: 30 }}
                scroll={{ y: 500 }}
                onRow={(r) => ({ onClick: () => navigate(`/stocks/${r.code}`), style: { cursor: "pointer" } })}
              />
            ),
          },
        ]}
      />
    </PageContainer>
  );
}
