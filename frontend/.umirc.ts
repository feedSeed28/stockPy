import { defineConfig } from "@umijs/max";

export default defineConfig({
  antd: {},
  access: {},
  model: {},
  initialState: {},
  request: {},
  layout: {
    title: "Stock Quant",
  },
  routes: [
    {
      path: "/",
      redirect: "/stocks",
    },
    {
      name: "股票列表",
      path: "/stocks",
      component: "./Stocks",
    },
    {
      name: "股票详情",
      path: "/stocks/:code",
      component: "./Stocks/Detail",
      hideInMenu: true,
    },
    {
      name: "板块",
      path: "/boards",
      component: "./Boards",
    },
    {
      name: "选股",
      path: "/screener",
      component: "./Screener",
    },
    {
      name: "回测",
      path: "/backtest",
      component: "./Backtest",
    },
  ],
  npmClient: "pnpm",
  proxy: {
    "/api": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
  },
});
