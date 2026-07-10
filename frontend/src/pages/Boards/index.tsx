/** Industry / concept boards page — 直连模式优先东方财富 */

import { PageContainer, ProTable } from "@ant-design/pro-components";
import { Tag, Drawer, List, Typography, Alert } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@umijs/max";
import { fetchBoards, fetchBoardMembers } from "@/services/stock";
import { useDirectSource } from "@/utils/dataSource";
import {
  fetchBoardListEM,
  fetchBoardMembersEM,
  type EMBoardInfo,
  type EMStockBrief,
} from "@/services/eastmoney";
import type { BoardInfo, BoardMember } from "@/services/typings";
import type { ProColumns } from "@ant-design/pro-components";

export default function BoardsPage() {
  const navigate = useNavigate();
  const direct = useDirectSource();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [members, setMembers] = useState<BoardMember[]>([]);
  const [boardName, setBoardName] = useState("");
  const [membersLoading, setMembersLoading] = useState(false);
  const [allBoards, setAllBoards] = useState<BoardInfo[]>([]);
  const [boardsLoaded, setBoardsLoaded] = useState(false);

  // 加载全量板块（直连模式一次拉全，后端模式分页）
  useEffect(() => {
    setBoardsLoaded(false);
    if (direct) {
      Promise.all([
        fetchBoardListEM("industry"),
        fetchBoardListEM("concept"),
      ]).then(([ind, con]) => {
        const all: BoardInfo[] = [
          ...ind.map((b) => ({ id: b.code, board_code: b.code, board_name: b.name, board_type: "industry" as const, source: "em" as const })),
          ...con.map((b) => ({ id: b.code, board_code: b.code, board_name: b.name, board_type: "concept" as const, source: "em" as const })),
        ];
        setAllBoards(all);
        setBoardsLoaded(true);
      });
      return;
    }
    // 后端模式
    (async () => {
      let all: BoardInfo[] = [];
      let page = 1;
      const pageSize = 200;
      while (true) {
        const res = await fetchBoards({ page, page_size: pageSize });
        all = [...all, ...res.items];
        if (all.length >= res.total) break;
        page++;
      }
      setAllBoards(all);
    })();
  }, [direct]);

  const codeEnum = useMemo(() => {
    const map: Record<string, { text: string }> = {};
    allBoards.forEach((b) => {
      if (!map[b.board_code]) map[b.board_code] = { text: b.board_code };
    });
    return map;
  }, [allBoards]);

  const nameEnum = useMemo(() => {
    const map: Record<string, { text: string }> = {};
    allBoards.forEach((b) => {
      if (!map[b.board_name]) map[b.board_name] = { text: b.board_name };
    });
    return map;
  }, [allBoards]);

  const columns: ProColumns<BoardInfo>[] = [
    {
      title: "板块代码",
      dataIndex: "board_code",
      key: "board_code",
      width: 120,
      valueType: "select",
      valueEnum: codeEnum,
      fieldProps: { showSearch: true, allowClear: true },
    },
    {
      title: "板块名称",
      dataIndex: "board_name",
      key: "board_name",
      width: 200,
      valueType: "select",
      valueEnum: nameEnum,
      fieldProps: { showSearch: true, allowClear: true },
    },
    {
      title: "类型",
      dataIndex: "board_type",
      key: "board_type",
      width: 100,
      valueType: "select",
      valueEnum: {
        industry: { text: "行业" },
        concept: { text: "概念" },
      },
      render: (_, row) => (
        <Tag color={row.board_type === "industry" ? "blue" : "orange"}>
          {row.board_type === "industry" ? "行业" : "概念"}
        </Tag>
      ),
    },
    {
      title: "数据源",
      dataIndex: "source",
      key: "source",
      width: 80,
      valueType: "select",
      valueEnum: {
        em: { text: "东方财富" },
        ths: { text: "同花顺" },
      },
    },
  ];

  const loadMembers = async (boardCode: string, name: string) => {
    setBoardName(name);
    setDrawerOpen(true);
    setMembersLoading(true);
    try {
      if (direct) {
        // 直连模式：东方财富板块成分股
        const emMembers = await fetchBoardMembersEM(boardCode);
        setMembers(emMembers.map((m: EMStockBrief) => ({
          stock_code: m.code,
          stock_name: m.name,
        })));
      } else {
        const res = await fetchBoardMembers(boardCode);
        setMembers(res.items);
      }
    } finally {
      setMembersLoading(false);
    }
  };

  return (
    <PageContainer>
      {direct && (
        <Alert
          type="info"
          message="直连模式 — 板块数据来自东方财富 API（用户IP），点击板块查看成分股"
          style={{ marginBottom: 16 }}
          showIcon
          closable
        />
      )}

      <ProTable<BoardInfo>
        columns={columns}
        rowKey="id"
        loading={direct && !boardsLoaded}
        request={async (params: Record<string, any>) => {
          const { current, pageSize, board_type, board_code, board_name } = params;

          let items: BoardInfo[];
          let total: number;

          if (direct) {
            // ── 直连模式：复用已加载的全量板块，不重复请求API ──
            let list = allBoards;
            if (board_type) {
              list = list.filter((b) => b.board_type === board_type);
            }
            items = list;
          } else {
            // ── 后端模式 ──
            const res = await fetchBoards({
              page: current,
              page_size: pageSize,
              board_type,
            });
            items = res.items;
          }

          // 前端筛选
          if (board_code) {
            items = items.filter((b) => b.board_code === board_code);
          }
          if (board_name) {
            items = items.filter((b) => b.board_name === board_name);
          }
          total = items.length;

          // 前端分页
          const start = ((current || 1) - 1) * (pageSize || 30);
          const paged = items.slice(start, start + (pageSize || 30));

          return { data: paged, total, success: true };
        }}
        search={{ labelWidth: "auto", defaultCollapsed: false }}
        onRow={(record) => ({
          onClick: () => loadMembers(record.board_code, record.board_name),
          style: { cursor: "pointer" },
        })}
        pagination={{ defaultPageSize: 30 }}
      />

      <Drawer
        title={`${boardName} — 成分股`}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={400}
        loading={membersLoading}
      >
        <List
          dataSource={members}
          renderItem={(item) => (
            <List.Item
              style={{ cursor: "pointer" }}
              onClick={() => {
                setDrawerOpen(false);
                navigate(`/stocks/${item.stock_code}`);
              }}
            >
              <Typography.Text copyable={{ text: item.stock_code }}>
                {item.stock_code}
              </Typography.Text>
              <Typography.Text style={{ marginLeft: 12 }}>
                {item.stock_name || "-"}
              </Typography.Text>
            </List.Item>
          )}
        />
      </Drawer>
    </PageContainer>
  );
}
