export function App() {
  return (
    <main className="shell">
      <section className="shell__hero" aria-label="桌面工作区">
        <p className="shell__eyebrow">Electron Desktop Workspace</p>
        <h1>微信公众号文章采集工具</h1>
        <p className="shell__description">
          这是桌面端的导航壳层，后续阶段会把采集、抓取和索引能力接到这里。
        </p>
      </section>

      <nav className="shell__nav" aria-label="主导航">
        <a href="#collect">采集</a>
        <a href="#scrape">抓取</a>
        <a href="#index">索引</a>
        <a href="#settings">设置</a>
      </nav>
    </main>
  );
}
