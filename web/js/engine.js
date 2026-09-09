/* 用途：按 formula.json 的步骤计算，不把公式写死在页面里 */

(function (root) {
  "use strict";

  function tokenize(src) {
    var tokens = [];
    var i = 0;
    var s = src;
    while (i < s.length) {
      var ch = s[i];
      if (ch === " " || ch === "\t" || ch === "\n") {
        i += 1;
        continue;
      }
      if ((ch >= "0" && ch <= "9") || (ch === "." && i + 1 < s.length && s[i + 1] >= "0" && s[i + 1] <= "9")) {
        var num = "";
        while (i < s.length && ((s[i] >= "0" && s[i] <= "9") || s[i] === ".")) {
          num += s[i];
          i += 1;
        }
        tokens.push({ t: "num", v: parseFloat(num) });
        continue;
      }
      if ((ch >= "a" && ch <= "z") || (ch >= "A" && ch <= "Z") || ch === "_") {
        var id = "";
        while (i < s.length && ((s[i] >= "a" && s[i] <= "z") || (s[i] >= "A" && s[i] <= "Z") || (s[i] >= "0" && s[i] <= "9") || s[i] === "_")) {
          id += s[i];
          i += 1;
        }
        if (id === "if" || id === "else" || id === "and" || id === "or" || id === "not") {
          tokens.push({ t: id });
        } else {
          tokens.push({ t: "id", v: id });
        }
        continue;
      }
      var two = s.slice(i, i + 2);
      if (two === "<=" || two === ">=" || two === "!=" || two === "==") {
        tokens.push({ t: "op", v: two });
        i += 2;
        continue;
      }
      if ("+-*/%()<>,".indexOf(ch) !== -1) {
        tokens.push({ t: "op", v: ch });
        i += 1;
        continue;
      }
      throw new Error("无法识别的符号: " + ch);
    }
    tokens.push({ t: "end" });
    return tokens;
  }

  function Parser(tokens, env) {
    this.tokens = tokens;
    this.i = 0;
    this.env = env;
  }

  Parser.prototype.peek = function () {
    return this.tokens[this.i];
  };

  Parser.prototype.eat = function (kind, value) {
    var cur = this.peek();
    if (kind && cur.t !== kind) {
      throw new Error("表达式格式不对");
    }
    if (value && (cur.v !== value && cur.t !== value)) {
      throw new Error("表达式格式不对");
    }
    this.i += 1;
    return cur;
  };

  Parser.prototype.parse = function () {
    var v = this.parseTernary();
    if (this.peek().t !== "end") {
      throw new Error("表达式未读完");
    }
    return v;
  };

  Parser.prototype.parseTernary = function () {
    var left = this.parseOr();
    if (this.peek().t === "if") {
      this.eat("if");
      var cond = this.parseOr();
      if (this.peek().t !== "else") {
        throw new Error("缺少 else");
      }
      this.eat("else");
      var right = this.parseTernary();
      return cond ? left : right;
    }
    return left;
  };

  Parser.prototype.parseOr = function () {
    var v = this.parseAnd();
    while (this.peek().t === "or") {
      this.eat("or");
      var r = this.parseAnd();
      v = v || r;
    }
    return v;
  };

  Parser.prototype.parseAnd = function () {
    var v = this.parseNot();
    while (this.peek().t === "and") {
      this.eat("and");
      var r = this.parseNot();
      v = v && r;
    }
    return v;
  };

  Parser.prototype.parseNot = function () {
    if (this.peek().t === "not") {
      this.eat("not");
      return !this.parseNot();
    }
    return this.parseCompare();
  };

  Parser.prototype.parseCompare = function () {
    var v = this.parseAdd();
    while (this.peek().t === "op" && ["<", ">", "<=", ">=", "==", "!="].indexOf(this.peek().v) !== -1) {
      var op = this.eat("op").v;
      var r = this.parseAdd();
      if (op === "<") v = v < r;
      else if (op === ">") v = v > r;
      else if (op === "<=") v = v <= r;
      else if (op === ">=") v = v >= r;
      else if (op === "==") v = v === r;
      else v = v !== r;
    }
    return v;
  };

  Parser.prototype.parseAdd = function () {
    var v = this.parseMul();
    while (this.peek().t === "op" && (this.peek().v === "+" || this.peek().v === "-")) {
      var op = this.eat("op").v;
      var r = this.parseMul();
      v = op === "+" ? v + r : v - r;
    }
    return v;
  };

  Parser.prototype.parseMul = function () {
    var v = this.parseUnary();
    while (this.peek().t === "op" && (this.peek().v === "*" || this.peek().v === "/" || this.peek().v === "%")) {
      var op = this.eat("op").v;
      var r = this.parseUnary();
      if (op === "*") v = v * r;
      else if (op === "/") v = v / r;
      else v = v % r;
    }
    return v;
  };

  Parser.prototype.parseUnary = function () {
    if (this.peek().t === "op" && (this.peek().v === "+" || this.peek().v === "-")) {
      var op = this.eat("op").v;
      var v = this.parseUnary();
      return op === "-" ? -v : v;
    }
    return this.parsePrimary();
  };

  Parser.prototype.parsePrimary = function () {
    var cur = this.peek();
    if (cur.t === "num") {
      this.eat("num");
      return cur.v;
    }
    if (cur.t === "id") {
      this.eat("id");
      if (this.peek().t === "op" && this.peek().v === "(") {
        this.eat("op", "(");
        var args = [];
        if (!(this.peek().t === "op" && this.peek().v === ")")) {
          args.push(this.parseTernary());
          while (this.peek().t === "op" && this.peek().v === ",") {
            this.eat("op", ",");
            args.push(this.parseTernary());
          }
        }
        this.eat("op", ")");
        return callFn(cur.v, args);
      }
      if (!(cur.v in this.env)) {
        throw new Error("缺少参数: " + cur.v);
      }
      return this.env[cur.v];
    }
    if (cur.t === "op" && cur.v === "(") {
      this.eat("op", "(");
      var v = this.parseTernary();
      this.eat("op", ")");
      return v;
    }
    throw new Error("表达式格式不对");
  };

  function callFn(name, args) {
    if (name === "max") {
      return Math.max.apply(null, args);
    }
    if (name === "min") {
      return Math.min.apply(null, args);
    }
    throw new Error("不支持的函数: " + name);
  }

  function evalExpr(expr, env) {
    var parser = new Parser(tokenize(expr), env);
    return parser.parse();
  }

  function lookupAir(cfg, section, ambient, mode) {
    var rows = cfg.tables.air_ampacity.rows;
    var key = String(ambient);
    var i;
    for (i = 0; i < rows.length; i += 1) {
      if (rows[i].section_mm2 === section && key in rows[i]) {
        return rows[i][key];
      }
    }
    var overflow = cfg.tables.air_ampacity_overflow[mode];
    var overflowExpr = overflow[String(section)] || "0";
    return evalExpr(overflowExpr, { ambient_c: ambient });
  }

  function lookupBury(cfg, section, temp) {
    var rows = cfg.tables.bury_ampacity.rows;
    var key = String(temp);
    var i;
    for (i = 0; i < rows.length; i += 1) {
      if (rows[i].section_mm2 === section && key in rows[i]) {
        return rows[i][key];
      }
    }
    return cfg.tables.bury_ampacity.missingMeans || 0;
  }

  function runAmpacity(cfg, env, mode) {
    if (env.is_buried) {
      env.I_c_raw = lookupBury(cfg, env.section_mm2, env.bury_temp_c);
      env.I_c = env.I_c_raw;
      return;
    }
    env.I_c_raw = lookupAir(cfg, env.section_mm2, env.ambient_c, mode);
    var ic = env.I_c_raw;
    if (ic !== 0) {
      if (env.len_solid_tray !== 0) {
        ic = ic * cfg.constants.air_derate_tray;
      }
      if (env.len_conduit !== 0 || env.len_ceiling !== 0 || env.len_brick !== 0) {
        ic = ic / cfg.constants.air_derate_tray * cfg.constants.air_derate_conduit;
      }
    }
    env.I_c = ic;
  }

  function classify(cfg, using, env) {
    var rules = cfg.thresholds[using];
    var i;
    for (i = 0; i < rules.length; i += 1) {
      if (evalExpr(rules[i].when, env)) {
        return { label: rules[i].label, color: rules[i].color, id: rules[i].id };
      }
    }
    return { label: "", color: "", id: "" };
  }

  function runSteps(cfg, groups, env, mode) {
    var g;
    var i;
    var step;
    for (g = 0; g < groups.length; g += 1) {
      var steps = cfg.steps[groups[g]];
      for (i = 0; i < steps.length; i += 1) {
        step = steps[i];
        if (step.op === "expr") {
          env[step.id] = evalExpr(step.expr, env);
        } else if (step.op === "assert") {
          if (!evalExpr(step.expr, env)) {
            var err = new Error(step.message || "输入不满足计算条件");
            err.code = "assert";
            throw err;
          }
        } else if (step.op === "ampacity_lookup") {
          runAmpacity(cfg, env, mode);
        } else if (step.op === "air_derate") {
          continue;
        } else if (step.op === "classify") {
          var cls = classify(cfg, step.using, env);
          env[step.id] = cls.label;
          env[step.id + "_meta"] = cls;
        } else {
          throw new Error("未知步骤: " + step.op);
        }
      }
    }
  }

  function calculate(cfg, mode, inputs) {
    var env = {};
    var key;
    for (key in cfg.constants) {
      if (Object.prototype.hasOwnProperty.call(cfg.constants, key)) {
        env[key] = cfg.constants[key];
      }
    }
    for (key in inputs) {
      if (Object.prototype.hasOwnProperty.call(inputs, key)) {
        env[key] = inputs[key];
      }
    }
    runSteps(cfg, ["shared_length", "resistance", "ampacity", mode], env, mode);
    return env;
  }

  root.VoltageDropEngine = {
    evalExpr: evalExpr,
    calculate: calculate
  };
})(window);
