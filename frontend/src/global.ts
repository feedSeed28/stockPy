// Suppress antd findDOMNode deprecation (React 18 compat warning, harmless)
const _warn = console.warn;
console.warn = function (...args: any[]) {
  if (typeof args[0] === "string" && args[0].includes("findDOMNode")) return;
  _warn.apply(console, args);
};
