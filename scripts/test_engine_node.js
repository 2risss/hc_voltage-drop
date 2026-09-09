// 用途：用 Node 核对 web/js/engine.js 与 formula.json 算例
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const engineSrc = fs.readFileSync(path.join(root, "web", "js", "engine.js"), "utf8");
const cfg = JSON.parse(fs.readFileSync(path.join(root, "web", "config", "formula.json"), "utf8"));
const sandbox = { window: {}, console };
vm.runInNewContext(engineSrc, sandbox);
const engine = sandbox.window.VoltageDropEngine;

function closeEnough(got, expect) {
  if (typeof expect === "string") return got === expect;
  const absErr = Math.abs(got - expect);
  const relErr = absErr / Math.max(Math.abs(expect), 1e-12);
  return absErr <= 1e-6 || relErr < 1e-6;
}

let ok = 0;
let fail = 0;
for (const fixture of cfg.fixtures) {
  const result = engine.calculate(cfg, fixture.mode, fixture.inputs);
  for (const [key, expect] of Object.entries(fixture.expect)) {
    if (closeEnough(result[key], expect)) {
      ok += 1;
    } else {
      fail += 1;
      console.log("DIFF", fixture.id, key, "expect", expect, "got", result[key]);
    }
  }
}
console.log("ok", ok, "fail", fail);
if (fail) process.exit(1);
