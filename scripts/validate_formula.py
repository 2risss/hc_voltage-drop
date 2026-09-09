# 用途：按 config/formula.json 本地验算，对照原表算例
# 输入：config/formula.json
# 输出：output/formula_validation_20260909.html

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = ROOT / "config" / "formula.json"
OUT_PATH = ROOT / "output" / "formula_validation_20260909.html"


def lookup_air(cfg: dict, section: float, ambient: float, mode: str) -> float:
    table = cfg["tables"]["air_ampacity"]["rows"]
    key = str(int(ambient)) if float(ambient).is_integer() else str(ambient)
    for row in table:
        if row["section_mm2"] == section and key in row:
            return float(row[key])
    overflow = cfg["tables"]["air_ampacity_overflow"][mode]
    expr = overflow.get(str(int(section)), "0")
    return float(eval(expr, {"__builtins__": {}}, {"ambient_c": ambient}))


def lookup_bury(cfg: dict, section: float, temp: float) -> float:
    table = cfg["tables"]["bury_ampacity"]["rows"]
    key = str(int(temp)) if float(temp).is_integer() else str(temp)
    for row in table:
        if row["section_mm2"] == section and key in row:
            return float(row[key])
    return float(cfg["tables"]["bury_ampacity"].get("missingMeans", 0))


def eval_expr(expr: str, env: dict):
    return eval(expr, {"__builtins__": {}}, env)


def classify(cfg: dict, using: str, env: dict) -> str:
    for rule in cfg["thresholds"][using]:
        if bool(eval_expr(rule["when"], env)):
            return rule["label"]
    return ""


def run_ampacity(cfg: dict, env: dict, mode: str) -> None:
    if env["is_buried"]:
        env["I_c_raw"] = lookup_bury(cfg, env["section_mm2"], env["bury_temp_c"])
        env["I_c"] = env["I_c_raw"]
        return
    env["I_c_raw"] = lookup_air(cfg, env["section_mm2"], env["ambient_c"], mode)
    ic = env["I_c_raw"]
    if ic != 0:
        if env["len_solid_tray"] != 0:
            ic = ic * cfg["constants"]["air_derate_tray"]
        if env["len_conduit"] != 0 or env["len_ceiling"] != 0 or env["len_brick"] != 0:
            ic = ic / cfg["constants"]["air_derate_tray"] * cfg["constants"]["air_derate_conduit"]
    env["I_c"] = ic


def run_steps(cfg: dict, step_ids: list[str], env: dict, mode: str) -> None:
    steps = []
    for group in step_ids:
        steps.extend(cfg["steps"][group])
    for step in steps:
        op = step["op"]
        sid = step["id"]
        if op == "expr":
            env[sid] = eval_expr(step["expr"], env)
        elif op == "assert":
            if not bool(eval_expr(step["expr"], env)):
                raise ValueError(step.get("message", "assert failed"))
        elif op == "ampacity_lookup":
            run_ampacity(cfg, env, mode)
        elif op == "air_derate":
            continue
        elif op == "classify":
            env[sid] = classify(cfg, step["using"], env)
        else:
            raise ValueError(f"unknown op {op}")


def calculate(cfg: dict, mode: str, inputs: dict) -> dict:
    env = {}
    env.update(cfg["constants"])
    env.update(inputs)
    run_steps(cfg, ["shared_length", "resistance", "ampacity", mode], env, mode)
    return env


def close_enough(got, expect) -> bool:
    if isinstance(expect, str):
        return got == expect
    if got is None:
        return False
    got_f = float(got)
    exp_f = float(expect)
    abs_err = abs(got_f - exp_f)
    rel_err = abs_err / max(abs(exp_f), 1e-12)
    # 压降等项可对到 1e-12；电源容量原表用 VBA Single（约 7 位有效数字），允许到 1e-6。
    return abs_err <= 1e-6 or rel_err < 1e-6


def fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.12g}"
    return str(v)


def main() -> None:
    cfg = json.loads(FORMULA_PATH.read_text(encoding="utf-8"))
    rows = []
    all_ok = True
    for fixture in cfg["fixtures"]:
        result = calculate(cfg, fixture["mode"], fixture["inputs"])
        for key, expect in fixture["expect"].items():
            got = result.get(key)
            ok = close_enough(got, expect)
            all_ok = all_ok and ok
            rows.append(
                {
                    "fixture": fixture["id"],
                    "mode": fixture["mode"],
                    "key": key,
                    "expect": expect,
                    "got": got,
                    "ok": ok,
                }
            )

    status = "全部通过" if all_ok else "存在差异"
    html_rows = []
    for r in rows:
        mark = "通过" if r["ok"] else "不一致"
        if r["ok"] and not isinstance(r["expect"], str):
            abs_err = abs(float(r["got"]) - float(r["expect"]))
            if abs_err > 1e-12:
                mark = "通过（原表单精度差）"
        color = "#1f7a4d" if r["ok"] else "#b42318"
        html_rows.append(
            f"<tr><td>{r['fixture']}</td><td>{r['mode']}</td><td>{r['key']}</td>"
            f"<td>{fmt(r['expect'])}</td><td>{fmt(r['got'])}</td>"
            f"<td style='color:{color}'>{mark}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>公式验算结果</title>
  <style>
    body {{ font-family: "Microsoft YaHei", "微软雅黑", Calibri, sans-serif; background:#f6f7f8; color:#1f2328; margin:0; }}
    .wrap {{ max-width: 960px; margin: 0 auto; padding: 24px 16px 64px; }}
    table {{ width:100%; border-collapse: collapse; background:#fff; font-size:14px; }}
    th, td {{ border:1px solid #e6e8eb; padding:8px 10px; text-align:left; }}
    th {{ background:#f3f4f6; }}
    .kpi {{ font-size:28px; margin: 8px 0 20px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>压降验证测算 — 公式 JSON 验算</h1>
    <p>公式版本 {cfg["version"]}，对照原表 V1.1 两组当前算例。</p>
    <div class="kpi">{status}</div>
    <table>
      <thead><tr><th>算例</th><th>模式</th><th>项目</th><th>原表</th><th>JSON计算结果</th><th>核对</th></tr></thead>
      <tbody>
        {"".join(html_rows)}
      </tbody>
    </table>
    <p>文件：config/formula.json。本步未写网页，也未推送到 GitHub。</p>
  </div>
</body>
</html>
"""
    OUT_PATH.write_text(html, encoding="utf-8")
    print(status)
    print("rows", len(rows), "ok", sum(1 for r in rows if r["ok"]))
    if not all_ok:
        for r in rows:
            if not r["ok"]:
                print("DIFF", r)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
