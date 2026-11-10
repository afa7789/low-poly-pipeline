#!/usr/bin/env python3
"""Human vs judge report (IA_gen_paper/05-avaliacao-humana-vs-juiz.md).

    python3 tools/blender/eval_report.py --computer eval/computer-<ts>.json [--human eval/human-<ts>.json | /api/eval/export JSON]
                                         [--md ../IA_gen_paper/05-avaliacao-humana-vs-juiz.md] [--no-md]

Per question (q1 WC3 likeness, q2 concept fidelity, q3 usable in the alpha): mean human (per-unit mean over
raters), mean judge, Spearman / Kendall tau-b between human and judge, human and judge against the automatic
numbers (IoU front/left/rts, parts share), and the means by rig group (biped vs non-biped). Prints the tables
and replaces the block between EVAL-REPORT markers of the markdown file. Without --human the judge columns
are filled and the human ones stay "—". No deps (scipy only for p-values when installed).
"""
import argparse
import json
import math
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[2]
MD = ROOT.parent / "IA_gen_paper" / "05-avaliacao-humana-vs-juiz.md"
QS = ("q1", "q2", "q3")
QNAME = {"q1": "Q1 parece WC3", "q2": "Q2 fiel ao concept", "q3": "Q3 usaria na alfa"}
AUTO = (("iou_front", "IoU front"), ("iou_left", "IoU left"), ("iou_rts", "IoU rts"), ("parts", "parts k/n"))
BEGIN, END = "<!-- EVAL-REPORT:begin -->", "<!-- EVAL-REPORT:end -->"


def ranks(xs):
    """Average ranks (ties share the mean rank)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


def kendall(xs, ys):
    """Kendall tau-b."""
    n = len(xs)
    if n < 3:
        return None
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = xs[i] - xs[j], ys[i] - ys[j]
            if a == 0 and b == 0:
                continue
            if a == 0:
                tx += 1
            elif b == 0:
                ty += 1
            elif (a > 0) == (b > 0):
                c += 1
            else:
                d += 1
    den = math.sqrt((c + d + tx) * (c + d + ty))
    return (c - d) / den if den else None


def spearman_p(xs, ys):
    try:
        from scipy.stats import spearmanr
        return float(spearmanr(xs, ys).pvalue)
    except Exception:
        return None


def load_human(path):
    """{unit id: {q: mean over raters}} plus the number of raters (sessions), from a session file or an export."""
    if path is None:
        return {}, 0
    data = json.loads(pathlib.Path(path).read_text())
    rows = data.get("answers", [])
    sessions = {r.get("session", data.get("session", "?")) for r in rows}
    per = {}
    for r in rows:
        if all(isinstance(r.get(q), int) for q in QS):
            per.setdefault(r["id"], []).append(r)
    return {uid: {q: statistics.fmean(a[q] for a in lst) for q in QS} for uid, lst in per.items()}, len(sessions)


def load_judge(path):
    data = json.loads(pathlib.Path(path).read_text())
    out = {}
    for r in data["results"]:
        if all(isinstance(r.get(q), int) for q in QS):
            out[r["id"]] = r
    return data, out


def fmt(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def corr_cell(xs, ys):
    if len(xs) < 3:
        return "—"
    rho, tau, p = spearman(xs, ys), kendall(xs, ys), spearman_p(xs, ys)
    s = f"ρ {rho:.2f}" if rho is not None else "ρ —"
    s += f" / τ {tau:.2f}" if tau is not None else " / τ —"
    if p is not None:
        s += f" (p {p:.2f})"
    return s


def pairs(ids, a, b, qa, qb):
    """Aligned value lists for ids present in both maps and with both values."""
    xs, ys = [], []
    for uid in ids:
        x, y = a.get(uid, {}).get(qa), b.get(uid, {}).get(qb)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            xs.append(float(x))
            ys.append(float(y))
    return xs, ys


def mean_cell(scores, members, q, nd=2):
    """Mean of scores[u][q] over the members that have one, or '—'."""
    vals = [scores[u][q] for u in members if u in scores]
    return f"{statistics.fmean(vals):.{nd}f}" if vals else "—"


def question_table(ids, human, judge, auto):
    lines = ["| pergunta | média humano | média juiz | humano↔juiz | humano↔IoU front | humano↔IoU left | humano↔parts "
             "| juiz↔IoU front | juiz↔IoU left | juiz↔parts |", "|---|---|---|---|---|---|---|---|---|---|"]
    for q in QS:
        hx, jy = pairs(ids, human, judge, q, q)
        hm = f"{statistics.fmean(hx):.2f} (n {len(hx)})" if hx else "—"
        jm = f"{statistics.fmean(judge[u][q] for u in ids):.2f} (n {len(ids)})"
        cells = [QNAME[q], hm, jm, corr_cell(hx, jy)]
        cells += [corr_cell(*pairs(ids, human, auto, q, key)) for key in ("iou_front", "iou_left", "parts")]
        cells += [corr_cell(*pairs(ids, judge, auto, q, key)) for key in ("iou_front", "iou_left", "parts")]
        lines.append("| " + " | ".join(cells) + " |")
    rts_j = ", ".join(f"{q} {corr_cell(*pairs(ids, judge, auto, q, 'iou_rts'))}" for q in QS)
    rts_h = ", ".join(f"{q} {corr_cell(*pairs(ids, human, auto, q, 'iou_rts'))}" for q in QS)
    lines += ["", f"IoU rts (n menor: unidades sem painel rts): juiz {rts_j}; humano {rts_h}."]
    return lines


def group_table(ids, human, judge, auto):
    lines = ["| grupo | n | humano Q1 | humano Q2 | humano Q3 | juiz Q1 | juiz Q2 | juiz Q3 | IoU front | parts |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    groups = {"bípedes": [u for u in ids if judge[u].get("group") == "biped"],
              "não-bípedes": [u for u in ids if judge[u].get("group") != "biped"]}
    for name, members in groups.items():
        if not members:
            continue
        cells = [mean_cell(human, members, q) for q in QS] + [mean_cell(judge, members, q) for q in QS]
        cells += [mean_cell(auto, members, "iou_front"), mean_cell(auto, members, "parts")]
        lines.append(f"| {name} | {len(members)} | " + " | ".join(cells) + " |")
    return lines


def rig_table(ids, human, judge):
    lines = ["Por rig (juiz Q1/Q2/Q3, humano Q1/Q2/Q3 quando há):", "",
             "| rig | n | juiz Q1 | juiz Q2 | juiz Q3 | humano Q1 | humano Q2 | humano Q3 |", "|---|---|---|---|---|---|---|---|"]
    by_rig = {}
    for u in ids:
        by_rig.setdefault(judge[u].get("rig", "?"), []).append(u)
    for rig, members in sorted(by_rig.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        cells = [mean_cell(judge, members, q, 1) for q in QS] + [mean_cell(human, members, q, 1) for q in QS]
        lines.append(f"| {rig} | {len(members)} | " + " | ".join(cells) + " |")
    return lines


def unit_table(ids, human, judge, auto):
    lines = ["Por unidade (juiz; humano quando há):", "",
             "| id | nome | rig | juiz Q1 | Q2 | Q3 | humano Q1 | Q2 | Q3 | IoU front | parts | porquê (juiz) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for u in ids:
        r, a = judge[u], auto[u]
        h = [mean_cell(human, [u], q, 1) for q in QS]
        why = (r.get("why") or "").replace("|", "/").replace("\n", " ")
        lines.append(f"| {u} | {r.get('name', '')} | {r.get('rig', '')} | {r['q1']} | {r['q2']} | {r['q3']} | "
                     + " | ".join(h) + f" | {fmt(a.get('iou_front'))} | {fmt(a.get('parts'))} | {why} |")
    return lines


def build(human, n_raters, judge):
    ids = sorted(judge)
    auto = {uid: {k: v for k, v in (judge[uid].get("auto") or {}).items() if v is not None} for uid in ids}
    lines = [f"Unidades com nota do juiz: {len(ids)}; avaliadores humanos (sessões): {n_raters}; "
             f"unidades com nota humana: {len([u for u in ids if u in human])}.", ""]
    lines += question_table(ids, human, judge, auto) + [""]
    lines += group_table(ids, human, judge, auto) + [""]
    lines += rig_table(ids, human, judge) + [""]
    lines += unit_table(ids, human, judge, auto)
    return "\n".join(lines)


def write_md(path, block):
    text = path.read_text()
    if BEGIN not in text or END not in text:
        raise SystemExit(f"{path}: markers {BEGIN} / {END} missing")
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    path.write_text(f"{head}{BEGIN}\n{block}\n{END}{tail}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--computer", required=True)
    ap.add_argument("--human", default=None)
    ap.add_argument("--md", default=str(MD))
    ap.add_argument("--no-md", action="store_true")
    args = ap.parse_args()
    human, n_raters = load_human(args.human)
    _, judge = load_judge(args.computer)
    block = build(human, n_raters, judge)
    print(block)
    if not args.no_md:
        write_md(pathlib.Path(args.md), block)
        print(f"\nwrote {args.md}")


if __name__ == "__main__":
    main()
