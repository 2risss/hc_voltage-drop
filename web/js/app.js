(function () {
  "use strict";

  var HISTORY_KEY = "hc_voltage_drop_history_v1";
  var HISTORY_MAX = 10;
  var cfg = null;
  var mode = "single_phase";
  var fieldsEl = document.getElementById("formFields");
  var resultBox = document.getElementById("resultBox");
  var errorBox = document.getElementById("errorBox");
  var historyBox = document.getElementById("historyBox");

  function $(id) {
    return document.getElementById(id);
  }

  function num(v) {
    var n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  }

  function fmtNum(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return v.toFixed(2);
  }

  function badgeClass(color) {
    if (color === "green") return "badge green";
    if (color === "yellow") return "badge yellow";
    if (color === "orange") return "badge orange";
    if (color === "red") return "badge red";
    return "badge";
  }

  function fieldHtml(spec, extraClass) {
    var id = spec.id;
    var unit = spec.unit ? '<span class="unit">' + spec.unit + "</span>" : "";
    var hint = spec.remark ? '<div class="hint">' + spec.remark + "</div>" : "";
    var control;
    if (spec.type === "select") {
      var opts = spec.options.map(function (opt) {
        var selected = String(opt) === String(spec.default) ? " selected" : "";
        return "<option value=\"" + opt + "\"" + selected + ">" + opt + "</option>";
      }).join("");
      control = "<select id=\"f_" + id + "\">" + opts + "</select>";
    } else {
      var min = spec.min != null ? " min=\"" + spec.min + "\"" : "";
      var max = spec.max != null ? " max=\"" + spec.max + "\"" : "";
      control = "<input id=\"f_" + id + "\" type=\"number\" inputmode=\"decimal\" step=\"1\" value=\"" + spec.default + "\"" + min + max + ">";
    }
    return '<div class="field ' + (extraClass || "") + '" data-id="' + id + '"><label><span>' + spec.label + "</span>" + unit + "</label>" + control + hint + "</div>";
  }

  function allSpecs() {
    return cfg.inputs.common
      .concat(cfg.inputs.single_phase)
      .concat(cfg.inputs.three_phase)
      .concat(cfg.inputs.lengths)
      .concat(cfg.inputs.bury_temps);
  }

  function renderForm() {
    var html = "";
    cfg.inputs.common.forEach(function (spec) {
      html += fieldHtml(spec);
    });
    if (mode === "single_phase") {
      cfg.inputs.single_phase.forEach(function (spec) {
        html += fieldHtml(spec);
      });
    } else {
      cfg.inputs.three_phase.forEach(function (spec) {
        html += fieldHtml(spec);
      });
    }
    html += "<h2 style=\"margin-top:16px\">敷设方式及长度</h2>";
    cfg.inputs.lengths.forEach(function (spec) {
      html += fieldHtml(spec);
    });
    cfg.inputs.bury_temps.forEach(function (spec) {
      html += fieldHtml(spec);
    });
    fieldsEl.innerHTML = html;
    fieldsEl.querySelectorAll("input, select").forEach(function (el) {
      el.addEventListener("input", liveCalc);
      el.addEventListener("change", liveCalc);
    });
    liveCalc();
  }

  function readInputs() {
    var inputs = {};
    allSpecs().forEach(function (spec) {
      var el = $("f_" + spec.id);
      var fallback = spec.default;
      if (!el) {
        inputs[spec.id] = typeof fallback === "number" ? fallback : fallback;
        return;
      }
      if (spec.type === "select") {
        var raw = el.value;
        inputs[spec.id] = typeof spec.options[0] === "number" ? num(raw) : raw;
      } else {
        inputs[spec.id] = num(el.value);
      }
    });
    return inputs;
  }

  function validateInputs(inputs) {
    var messages = [];
    function checkRange(spec, value) {
      if (spec.min != null && value < spec.min) messages.push(spec.label + "应不小于 " + spec.min);
      if (spec.max != null && value > spec.max) messages.push(spec.label + "应不大于 " + spec.max);
    }
    if (mode === "single_phase") {
      cfg.inputs.single_phase.forEach(function (spec) {
        checkRange(spec, inputs[spec.id]);
      });
    } else {
      cfg.inputs.three_phase.forEach(function (spec) {
        checkRange(spec, inputs[spec.id]);
      });
    }
    cfg.inputs.lengths.forEach(function (spec) {
      checkRange(spec, inputs[spec.id]);
    });
    if (inputs.len_direct_bury !== 0 && (inputs.temp_direct_bury === "" || inputs.temp_direct_bury == null)) {
      messages.push("直埋地长度不为 0 时需要填写埋地温度");
    }
    if (inputs.len_pipe_bury !== 0 && (inputs.temp_pipe_bury === "" || inputs.temp_pipe_bury == null)) {
      messages.push("穿管埋地长度不为 0 时需要填写埋地温度");
    }
    return messages;
  }

  function row(label, value, unit) {
    return '<div class="result-row"><span>' + label + "</span><b>" + value + (unit ? " " + unit : "") + "</b></div>";
  }

  function renderResult(result) {
    errorBox.hidden = true;
    var vMeta = result.voltage_class_meta || {};
    var aMeta = result.ampacity_class_meta || {};
    var pMeta = result.power_class_meta || {};
    var html = "";
    if (mode === "single_phase") {
      html += '<div class="kpi">';
      html += '<div class="item"><span>压降 Δu</span><b>' + fmtNum(result.dU) + " V</b></div>";
      html += '<div class="item"><span>压降百分比</span><b>' + fmtNum(result.dU_pct) + "%</b></div>";
      html += '<div class="item wide"><span>末端电压</span><b>' + fmtNum(result.u_end) + " V</b>";
      html += '<span class="' + badgeClass(vMeta.color) + '">' + (result.voltage_class || "") + "</span></div>";
      html += "</div>";
    } else {
      html += '<div class="kpi">';
      html += '<div class="item"><span>压降 Δu</span><b>' + fmtNum(result.dU) + " V</b></div>";
      html += '<div class="item"><span>计算电流</span><b>' + fmtNum(result.I_calc) + " A</b></div>";
      html += '<div class="item"><span>Δu% AB</span><b>' + fmtNum(result.dU_pct_ab) + "%</b></div>";
      html += '<div class="item"><span>Δu% BC</span><b>' + fmtNum(result.dU_pct_bc) + "%</b></div>";
      html += '<div class="item"><span>Δu% CA</span><b>' + fmtNum(result.dU_pct_ca) + "%</b></div>";
      html += '<div class="item wide"><span>末端电压 AB / BC / CA</span><b>' + fmtNum(result.u_end_ab) + " / " + fmtNum(result.u_end_bc) + " / " + fmtNum(result.u_end_ca) + " V</b>";
      html += '<span class="' + badgeClass(vMeta.color) + '">' + (result.voltage_class || "") + "</span></div>";
      html += "</div>";
    }
    html += row("直流电阻 Rθ", fmtNum(result.R_dc), "Ω");
    html += row("交流电阻 Rj", fmtNum(result.R_ac), "Ω");
    html += row("电缆总长度", fmtNum(result.L), "m");
    html += row("电缆载流量 IC", fmtNum(result.I_c), "A");
    html += '<div class="result-row"><span>载流量验证</span><span class="' + badgeClass(aMeta.color) + '">' + (result.ampacity_class || "") + "</span></div>";
    html += row("热损失功率", fmtNum(result.p_loss_kw), "kW");
    html += row("热损失百分数", fmtNum(result.p_loss_pct), "%");
    html += '<div class="result-row"><span>功率损失</span><span class="' + badgeClass(pMeta.color) + '">' + (result.power_class || "") + "</span></div>";
    html += row("电源点容量", fmtNum(result.s_kva), "kVA");
    resultBox.innerHTML = html;
  }

  function showError(msg) {
    errorBox.hidden = false;
    errorBox.textContent = msg;
    resultBox.innerHTML = "";
  }

  function liveCalc() {
    if (!cfg) return null;
    var inputs = readInputs();
    var msgs = validateInputs(inputs);
    if (msgs.length) {
      showError(msgs.join("；"));
      return null;
    }
    try {
      var result = window.VoltageDropEngine.calculate(cfg, mode, inputs);
      renderResult(result);
      return { inputs: inputs, result: result };
    } catch (e) {
      showError(e.message || "计算失败");
      return null;
    }
  }

  function loadHistory() {
    try {
      var raw = localStorage.getItem(HISTORY_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory(list) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, HISTORY_MAX)));
  }

  function renderHistory() {
    var list = loadHistory();
    if (!list.length) {
      historyBox.innerHTML = '<p class="hint">还没有保存的记录。</p>';
      return;
    }
    historyBox.innerHTML = list.map(function (item, idx) {
      var title = item.mode === "three_phase" ? "三相" : "单相";
      var extra = item.mode === "three_phase"
        ? "末端 " + fmtNum(item.u_end_ab) + "/" + fmtNum(item.u_end_bc) + "/" + fmtNum(item.u_end_ca) + " V"
        : "末端 " + fmtNum(item.u_end) + " V";
      return '<div class="history-item" data-idx="' + idx + '">'
        + '<p class="time">' + item.time + " · " + title + " · 公式 " + item.formulaVersion + "</p>"
        + "<p>" + item.section_mm2 + " mm² · " + item.limit_a + " A · 总长 " + fmtNum(item.L) + " m · 压降 " + fmtNum(item.dU) + " V · " + extra + "</p>"
        + '<p class="hint">' + (item.voltage_class || "") + " · " + (item.ampacity_class || "") + " · " + (item.power_class || "") + "</p>"
        + "</div>";
    }).join("");
  }

  function snapshot(payload) {
    var r = payload.result;
    var i = payload.inputs;
    return {
      time: new Date().toLocaleString("zh-CN", { hour12: false }),
      formulaVersion: cfg.version,
      mode: mode,
      section_mm2: i.section_mm2,
      limit_a: i.limit_a,
      L: r.L,
      dU: r.dU,
      u_end: r.u_end,
      u_end_ab: r.u_end_ab,
      u_end_bc: r.u_end_bc,
      u_end_ca: r.u_end_ca,
      voltage_class: r.voltage_class,
      ampacity_class: r.ampacity_class,
      power_class: r.power_class
    };
  }

  function setMode(next) {
    mode = next;
    $("modeSingle").classList.toggle("active", mode === "single_phase");
    $("modeThree").classList.toggle("active", mode === "three_phase");
    renderForm();
  }

  $("modeSingle").addEventListener("click", function () { setMode("single_phase"); });
  $("modeThree").addEventListener("click", function () { setMode("three_phase"); });
  $("btnCalc").addEventListener("click", function () {
    var payload = liveCalc();
    if (!payload) return;
    var list = loadHistory();
    list.unshift(snapshot(payload));
    saveHistory(list);
    renderHistory();
  });
  $("btnReset").addEventListener("click", function () {
    renderForm();
  });
  $("btnClear").addEventListener("click", function () {
    if (!window.confirm("清空这台手机上保存的最近计算记录？不会影响当前填写的参数。")) return;
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
  });

  fetch("config/formula.json", { cache: "no-store" })
    .then(function (resp) {
      if (!resp.ok) throw new Error("无法加载公式配置");
      return resp.json();
    })
    .then(function (data) {
      cfg = data;
      $("formulaVersion").textContent = "公式版本 " + cfg.version + " · 来源 " + cfg.source.workbookVersion + " · 记录只留在本机";
      renderForm();
      renderHistory();
    })
    .catch(function (err) {
      $("formulaVersion").textContent = "公式配置加载失败";
      showError(err.message || "公式配置加载失败。请用本地网页服务打开，不要直接双击文件。");
    });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js");
  }
})();
