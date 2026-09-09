# 用途：把网页、样式、计算引擎和 formula.json 打成单个 HTML，便于微信直接打开
# 输入：index.html、css/app.css、js/engine.js、js/app.js、config/formula.json
# 输出：压降验证测算.html（不覆盖别人发来的「电缆压降计算工具.html」）

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "压降验证测算.html"


def main() -> None:
    css = (ROOT / "css" / "app.css").read_text(encoding="utf-8")
    engine = (ROOT / "js" / "engine.js").read_text(encoding="utf-8")
    app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
    formula = json.loads((ROOT / "config" / "formula.json").read_text(encoding="utf-8"))
    formula_js = json.dumps(formula, ensure_ascii=False, separators=(",", ":"))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#171a1c">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="压降测算">
  <title>压降验证测算</title>
  <style>
{css}
  </style>
</head>
<body>
  <div class="app">
    <header class="top">
      <h1>压降验证测算</h1>
      <p id="formulaVersion">正在加载公式配置…</p>
    </header>

    <section class="card">
      <h2>电源类型</h2>
      <div class="seg" role="tablist">
        <button type="button" id="modeSingle" class="active">单相</button>
        <button type="button" id="modeThree">三相</button>
      </div>
      <p class="install-tip">本文件可在微信中直接打开。数据只保存在这台手机里，不会上传。</p>
    </section>

    <section class="card" id="formCard">
      <h2>基本信息</h2>
      <div id="formFields"></div>
    </section>

    <section class="card" id="resultCard">
      <h2>验证结果</h2>
      <div id="errorBox" class="error" hidden></div>
      <div id="resultBox"></div>
      <div class="actions">
        <button type="button" class="primary" id="btnCalc">计算并保存</button>
        <button type="button" class="ghost" id="btnReset">恢复默认</button>
      </div>
      <p class="okline" id="calcHint">改参数后结果会实时更新；点「计算并保存」才会写入最近 10 条记录。</p>
    </section>

    <section class="card">
      <h2>最近记录</h2>
      <div id="historyBox"></div>
      <button type="button" class="danger" id="btnClear">一键清空历史</button>
    </section>
  </div>
  <script>
window.EMBEDDED_FORMULA = {formula_js};
  </script>
  <script>
{engine}
  </script>
  <script>
{app}
  </script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print("wrote", OUT, "chars", len(html))


if __name__ == "__main__":
    main()
