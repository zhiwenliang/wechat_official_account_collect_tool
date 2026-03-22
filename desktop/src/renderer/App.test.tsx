import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the desktop shell heading", () => {
    const markup = renderToStaticMarkup(React.createElement(App));

    expect(markup).toContain("微信公众号文章采集工具");
  });
});
