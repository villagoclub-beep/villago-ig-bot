#!/usr/bin/env python3
"""
VillaGO 中东市场 - 每日外联跟进清单生成器

做什么:
  读取 middle_east/crm.csv, 按 stage + 日期算出今天该做什么:
    - 还没首触的服务商 (not_contacted) -> 挑几个生成 WA Day1 消息草稿
    - 首触后满3天没变 stage 的 -> 生成 Day3 追问草稿
    - Day3后满4天没变 stage 的 (即首触后第7天) -> 生成 Day7 最后跟进草稿
  把结果写到 middle_east/todo_today.md, 如果有 GITHUB_TOKEN 就同步开/更新一个
  GitHub Issue,方便每天早上直接在仓库里看到当天要发的话术,复制粘贴到 WhatsApp。

不做什么(刻意):
  不会自动发送 WhatsApp/邮件 —— 这里没有接入发送渠道,而且冷启动外联需要真人判断语气、
  按对方公司做小改动,自动群发正是话术模板里明确写了"严禁"的做法。
  这个脚本只负责"提醒 + 生成草稿",发送这一步永远是人来做。

用法:
  python3 tools/me_followup_reminder.py                # 生成清单,写文件
  python3 tools/me_followup_reminder.py --limit 3       # 每天最多推3个新首触目标
  python3 tools/me_followup_reminder.py --no-issue       # 只写本地文件,不碰 GitHub Issue

注意:
  CRM 数据放在 middle_east/crm.csv (repo根目录,受git追踪),不是 outputs/ 目录 ——
  outputs/ 整个被 .gitignore 忽略,GitHub Actions checkout 时拿不到,放那里自动化会直接报错。
"""

import argparse
import csv
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

CRM_PATH = Path(__file__).parent.parent / "middle_east" / "crm.csv"
TODO_PATH = Path(__file__).parent.parent / "middle_east" / "todo_today.md"

DAY3_GAP = 3   # Day1 -> Day3 追问间隔(天)
DAY7_GAP = 4   # Day3 -> Day7 间隔(天), 即首触后第7天

TEMPLATES = {
    "day1": {
        "ar": "مرحباً [الاسم] 👋\nمعك [اسمك] من VillaGO في بوكيت، تايلاند. لدينا مجموعة مختارة من الفلل الخاصة بمسبح خاص (٦-١٠ غرف) في بوكيت، مناسبة للعائلات الكبيرة. هل تتعاملون حالياً مع عملاء يسافرون إلى بوكيت؟",
        "en": "Hi [Name] 👋\nThis is [Your name] from VillaGO in Phuket. We manage a curated portfolio of private-pool villas (6-10 bedrooms), well suited for large GCC family groups. Do you currently place clients in Phuket?",
    },
    "day3": {
        "ar": "تحية طيبة مجدداً 🙏\nهذا فيديو قصير لأحد أكبر فللنا (٨ غرف، مسبح خاص بسور كامل، وطاهٍ خاص) وهو مطلوب كثيراً من عملاء الخليج. أقدر أرسل لكم قائمة الأسعار الخاصة بالوكلاء إذا يهمكم.",
        "en": "Following up 🙏 Here's a short video of one of our larger villas (8BR, fully walled private pool, dedicated chef) — very popular with GCC family groups. Happy to send our trade rate sheet if useful.",
    },
    "day7": {
        "ar": "أعتذر عن التكرار 🙏 إذا التوقيت غير مناسب الآن فلا مشكلة أبداً، الباب مفتوح دائماً. وإذا يهمكم لاحقاً، جاهز لإرسال ملف الشراكة والعمولة في أي وقت.",
        "en": "Sorry to follow up once more 🙏 If the timing isn't right, no worries — the door stays open. Whenever useful, happy to send our partnership file and commission structure.",
    },
}

DONE_STAGES = {"replied", "partner", "paused_no_response", "wa_day7_sent"}


def load_rows():
    with open(CRM_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save_rows(rows, fieldnames):
    with open(CRM_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_date(s):
    if not s:
        return None
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def fill(tpl, company):
    return tpl.replace("[الاسم]", company).replace("[Name]", company)


def build_todo(rows, new_limit, today):
    not_contacted = [r for r in rows if r["stage"] == "not_contacted"]
    not_contacted.sort(key=lambda r: int(r["priority"] or 9))

    due_day3, due_day7 = [], []
    for r in rows:
        last = parse_date(r.get("last_contact_date", ""))
        if not last:
            continue
        days_since = (today - last).days
        if r["stage"] == "wa_day1_sent" and days_since >= DAY3_GAP:
            due_day3.append(r)
        elif r["stage"] == "wa_day3_sent" and days_since >= DAY7_GAP:
            due_day7.append(r)

    lines = [f"# VillaGO 中东市场 · 今日跟进清单 ({today.isoformat()})", ""]
    lines.append(
        "> 发送方式: 一对一 WhatsApp,把 [公司名] 替换成实际称呼,发完后回到 "
        "`middle_east/crm.csv` 把该行 stage/last_contact_date 更新,下一次到期会自动算出来。"
    )
    lines.append("")

    def section(title, items, tpl_key):
        lines.append(f"## {title} ({len(items)})")
        if not items:
            lines.append("- (无)")
            lines.append("")
            return
        for r in items:
            lines.append(f"### {r['company']} — {r['country']}/{r['city']}  [id: {r['id']}]")
            lines.append(f"- 网站: {r['website'] or '无'} | 电话: {r['phone'] or '无'} | Email: {r['email'] or '无'}")
            if r.get("notes"):
                lines.append(f"- 备注: {r['notes']}")
            ar = fill(TEMPLATES[tpl_key]["ar"], r["company"])
            en = fill(TEMPLATES[tpl_key]["en"], r["company"])
            lines.append(f"- **阿语草稿**: {ar}")
            lines.append(f"- **英语草稿**: {en}")
            lines.append("")

    section(f"🆕 待首触 WA Day1 (今日建议推 {new_limit} 个)", not_contacted[:new_limit], "day1")
    section("⏰ Day3 追问到期", due_day3, "day3")
    section("⏰ Day7 最后跟进到期", due_day7, "day7")

    remaining = len(not_contacted) - min(new_limit, len(not_contacted))
    lines.append(f"---\n还有 {remaining} 家未首触的服务商在库里,明天/后续会按优先级继续推送。")
    return "\n".join(lines)


# ── GitHub Issue sync (reuses same auth pattern as tools/daily_post.py) ──
GH_REPO = os.environ.get("GITHUB_REPOSITORY", "villagoclub-beep/villago-ig-bot")
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
ISSUE_TITLE = "中东市场每日跟进清单"


def gh_request(method, url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def sync_github_issue(body):
    query = f'repo:{GH_REPO} type:issue in:title state:open "{ISSUE_TITLE}"'
    search_url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(query)
    result = gh_request("GET", search_url)
    items = result.get("items", [])
    if items:
        num = items[0]["number"]
        gh_request("PATCH", f"https://api.github.com/repos/{GH_REPO}/issues/{num}", {"body": body})
        print(f"  updated issue #{num}")
    else:
        created = gh_request(
            "POST", f"https://api.github.com/repos/{GH_REPO}/issues",
            {"title": ISSUE_TITLE, "body": body, "labels": ["middle-east", "outreach"]},
        )
        print(f"  created issue #{created['number']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5, help="每天最多推送几个新的首触目标")
    ap.add_argument("--no-issue", action="store_true", help="只写本地文件,不同步GitHub Issue")
    args = ap.parse_args()

    today = date.today()
    rows = load_rows()
    todo_md = build_todo(rows, args.limit, today)

    TODO_PATH.parent.mkdir(parents=True, exist_ok=True)
    TODO_PATH.write_text(todo_md, encoding="utf-8")
    print(f"✅ 已写入 {TODO_PATH}")

    if not args.no_issue and GH_TOKEN:
        print("📮 同步 GitHub Issue...")
        sync_github_issue(todo_md)
    elif not args.no_issue:
        print("⚠️  没有 GITHUB_TOKEN,跳过 GitHub Issue 同步(本地文件已生成)")


if __name__ == "__main__":
    main()
