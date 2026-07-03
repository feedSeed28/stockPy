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
  headScripts: [
    `(function(){var w=console.warn;console.warn=function(){if(typeof arguments[0]==='string'&&arguments[0].indexOf('findDOMNode')>-1)return;w.apply(console,arguments)}})()`,
  ],
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
    {
      name: "趋势",
      path: "/slope",
      component: "./Slope",
    },
    {
      name: "行情",
      path: "/market",
      component: "./Market",
    },
    {
      name: "龙虎榜",
      path: "/lhb",
      component: "./LHB",
    },
    {
      name: "涨停板",
      path: "/limit-up",
      routes: [
        { path: "/limit-up", redirect: "/limit-up/main" },
        { name: "主板", path: "/limit-up/main", component: "./LimitUp" },
        { name: "创业板", path: "/limit-up/chinext", component: "./LimitUp" },
        { name: "科创板", path: "/limit-up/star", component: "./LimitUp" },
      ],
    },
  ],
  mfsu: {
    exclude: ["echarts", "echarts-for-react"],
  },
  npmClient: "pnpm",
  proxy: {
    "/api": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
  },
});
