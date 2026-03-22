const assert = require("node:assert/strict");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const { App } = require("./App.tsx");

const markup = renderToStaticMarkup(React.createElement(App));

assert.match(markup, /微信公众号文章采集工具/);
