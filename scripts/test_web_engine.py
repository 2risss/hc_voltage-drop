# 用途：用 Python 复现 web/js/engine.js 的表达式解析，核对 formula.json 算例
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "web" / "config" / "formula.json").read_text(encoding="utf-8"))


class Parser:
    def __init__(self, src: str, env: dict):
        self.tokens = tokenize(src)
        self.i = 0
        self.env = env

    def peek(self):
        return self.tokens[self.i]

    def eat(self, kind=None, value=None):
        cur = self.peek()
        if kind and cur[0] != kind:
            raise ValueError("表达式格式不对")
        if value is not None and cur[1] != value and cur[0] != value:
            raise ValueError("表达式格式不对")
        self.i += 1
        return cur

    def parse(self):
        v = self.parse_ternary()
        if self.peek()[0] != "end":
            raise ValueError("表达式未读完")
        return v

    def parse_ternary(self):
        left = self.parse_or()
        if self.peek()[0] == "if":
            self.eat("if")
            cond = self.parse_or()
            self.eat("else")
            right = self.parse_ternary()
            return left if cond else right
        return left

    def parse_or(self):
        v = self.parse_and()
        while self.peek()[0] == "or":
            self.eat("or")
            r = self.parse_and()
            v = v or r
        return v

    def parse_and(self):
        v = self.parse_not()
        while self.peek()[0] == "and":
            self.eat("and")
            r = self.parse_not()
            v = v and r
        return v

    def parse_not(self):
        if self.peek()[0] == "not":
            self.eat("not")
            return not self.parse_not()
        return self.parse_compare()

    def parse_compare(self):
        v = self.parse_add()
        while self.peek()[0] == "op" and self.peek()[1] in {"<", ">", "<=", ">=", "==", "!="}:
            op = self.eat("op")[1]
            r = self.parse_add()
            v = {
                "<": v < r,
                ">": v > r,
                "<=": v <= r,
                ">=": v >= r,
                "==": v == r,
                "!=": v != r,
            }[op]
        return v

    def parse_add(self):
        v = self.parse_mul()
        while self.peek()[0] == "op" and self.peek()[1] in {"+", "-"}:
            op = self.eat("op")[1]
            r = self.parse_mul()
            v = v + r if op == "+" else v - r
        return v

    def parse_mul(self):
        v = self.parse_unary()
        while self.peek()[0] == "op" and self.peek()[1] in {"*", "/", "%"}:
            op = self.eat("op")[1]
            r = self.parse_unary()
            v = v * r if op == "*" else v / r if op == "/" else v % r
        return v

    def parse_unary(self):
        if self.peek()[0] == "op" and self.peek()[1] in {"+", "-"}:
            op = self.eat("op")[1]
            v = self.parse_unary()
            return -v if op == "-" else v
        return self.parse_primary()

    def parse_primary(self):
        cur = self.peek()
        if cur[0] == "num":
            self.eat("num")
            return cur[1]
        if cur[0] == "id":
            self.eat("id")
            if self.peek()[0] == "op" and self.peek()[1] == "(":
                self.eat("op", "(")
                args = []
                if not (self.peek()[0] == "op" and self.peek()[1] == ")"):
                    args.append(self.parse_ternary())
                    while self.peek()[0] == "op" and self.peek()[1] == ",":
                        self.eat("op", ",")
                        args.append(self.parse_ternary())
                self.eat("op", ")")
                if cur[1] == "max":
                    return max(args)
                if cur[1] == "min":
                    return min(args)
                raise ValueError(cur[1])
            return self.env[cur[1]]
        if cur[0] == "op" and cur[1] == "(":
            self.eat("op", "(")
            v = self.parse_ternary()
            self.eat("op", ")")
            return v
        raise ValueError("表达式格式不对")


def tokenize(s: str):
    tokens = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in " \t\n":
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < len(s) and s[i + 1].isdigit()):
            j = i
            while j < len(s) and (s[j].isdigit() or s[j] == "."):
                j += 1
            tokens.append(("num", float(s[i:j])))
            i = j
            continue
        if ch.isalpha() or ch == "_":
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] == "_"):
                j += 1
            ident = s[i:j]
            if ident in {"if", "else", "and", "or", "not"}:
                tokens.append((ident, ident))
            else:
                tokens.append(("id", ident))
            i = j
            continue
        two = s[i : i + 2]
        if two in {"<=", ">=", "!=", "=="}:
            tokens.append(("op", two))
            i += 2
            continue
        if ch in "+-*/%()<>,":
            tokens.append(("op", ch))
            i += 1
            continue
        raise ValueError(ch)
    tokens.append(("end", None))
    return tokens


def eval_expr(expr: str, env: dict):
    return Parser(expr, env).parse()


def lookup_air(cfg, section, ambient, mode):
    key = str(int(ambient) if float(ambient).is_integer() else ambient)
    for row in cfg["tables"]["air_ampacity"]["rows"]:
        if row["section_mm2"] == section and key in row:
            return row[key]
    expr = cfg["tables"]["air_ampacity_overflow"][mode].get(str(int(section)), "0")
    return eval_expr(expr, {"ambient_c": ambient})


def lookup_bury(cfg, section, temp):
    key = str(int(temp) if float(temp).is_integer() else temp)
    for row in cfg["tables"]["bury_ampacity"]["rows"]:
        if row["section_mm2"] == section and key in row:
            return row[key]
    return cfg["tables"]["bury_ampacity"].get("missingMeans", 0)


def run_ampacity(cfg, env, mode):
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


def calculate(cfg, mode, inputs):
    env = {}
    env.update(cfg["constants"])
    env.update(inputs)
    groups = ["shared_length", "resistance", "ampacity", mode]
    for group in groups:
        for step in cfg["steps"][group]:
            op = step["op"]
            if op == "expr":
                env[step["id"]] = eval_expr(step["expr"], env)
            elif op == "assert":
                if not eval_expr(step["expr"], env):
                    raise ValueError(step.get("message"))
            elif op == "ampacity_lookup":
                run_ampacity(cfg, env, mode)
            elif op == "air_derate":
                continue
            elif op == "classify":
                label = ""
                for rule in cfg["thresholds"][step["using"]]:
                    if eval_expr(rule["when"], env):
                        label = rule["label"]
                        break
                env[step["id"]] = label
    return env


def close_enough(got, expect) -> bool:
    if isinstance(expect, str):
        return got == expect
    abs_err = abs(float(got) - float(expect))
    rel_err = abs_err / max(abs(float(expect)), 1e-12)
    return abs_err <= 1e-6 or rel_err < 1e-6


def main() -> None:
    ok = fail = 0
    for fixture in CFG["fixtures"]:
        result = calculate(CFG, fixture["mode"], fixture["inputs"])
        for key, expect in fixture["expect"].items():
            if close_enough(result.get(key), expect):
                ok += 1
            else:
                fail += 1
                print("DIFF", fixture["id"], key, expect, result.get(key))
    print("ok", ok, "fail", fail)
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
