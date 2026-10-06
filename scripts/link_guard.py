"""
link_guard.py — 記事内リンクの安全性チェック（全エンジン共通）

LLM が生成した記事には、偽情報サイト・詐欺サイトへのリンクが混入することがある
（2026-10 に nihonnews.jp.net の偽ニュースを複数モデルが出典として掲載した事例）。
モデルの判断に頼らず、公開前に Python で決定論的にリンクを検査する。

  - 許可リスト（ALLOW_*）に一致 → リンクをそのまま残す
  - 拒否リスト（BLOCK_*）に一致 → リンクを外し「不審サイトのためリンク削除」と注記
  - どちらにも一致しない       → リンクを外し「未確認の出典のためリンク省略」と注記

信頼できる出典がリンク省略された場合は、ログ（"link_guard:"）を確認して
ALLOW_DOMAINS に追加していくこと。
"""

import re
from urllib.parse import urlparse

# 公的機関・学術機関などのドメイン末尾（サフィックス一致）
ALLOW_SUFFIXES = (
    ".go.jp", ".lg.jp", ".ac.jp", ".ed.jp",
    ".gov", ".edu", ".int", ".gov.uk", ".ac.uk",
)

# 個別に信頼できると判断したドメイン（サブドメインも含めて許可）
ALLOW_DOMAINS = {
    # 気象・防災・学術
    "tenki.jp", "weathernews.jp", "weathernews.com", "weather-jwa.jp", "jwa.or.jp",
    "metsoc.jp", "jstage.jst.go.jp", "jamstec.go.jp", "wmo.int", "un.org",
    "unic.or.jp", "ecmwf.int", "noaa.gov", "nasa.gov", "copernicus.eu",
    "nature.com", "science.org", "agu.org", "arxiv.org", "doi.org",
    "rief-jp.org", "climatefactchecks.org", "deepmind.google", "blog.google",
    # 報道機関
    "nhk.or.jp", "news.web.nhk", "nikkei.com", "asahi.com", "mainichi.jp",
    "yomiuri.co.jp", "sankei.com", "tokyo-np.co.jp", "47news.jp", "kyodonews.jp",
    "jiji.com", "tv-asahi.co.jp", "tbs.co.jp", "ntv.co.jp", "fnn.jp", "tv-tokyo.co.jp",
    "okinawatimes.co.jp", "ryukyushimpo.jp", "agara.co.jp", "sanspo.com",
    # 大手ニュースの配信ポータル
    "news.yahoo.co.jp", "news.livedoor.com", "topics.smt.docomo.ne.jp",
    "reuters.com", "bbc.com", "bbc.co.uk", "apnews.com", "cnn.co.jp",
    "afpbb.com", "bloomberg.co.jp", "theguardian.com", "nytimes.com",
    # 技術・総合メディア
    "technologyreview.jp", "wired.jp", "wired.com", "impress.co.jp", "itmedia.co.jp",
    "gigazine.net", "mynavi.jp", "response.jp", "sustainablejapan.jp",
    "ja.wikipedia.org", "en.wikipedia.org",
}

# 明確に不審と判断したドメイン（サブドメインも含めて拒否）
BLOCK_DOMAINS = {
    "nihonnews.jp.net",  # 2026-10: 偽ニュース「気象庁AI台風予測30%向上」の出典
}

# 誰でも安価にサブドメインを取得できる疑似的な第2階層ドメイン（CentralNic 等）。
# 公式サイト風に見せかけやすいため一律拒否する。
BLOCK_PSEUDO_SLD = (
    "jp.net", "jpn.com", "uk.com", "uk.net", "us.com", "us.org", "eu.com",
    "cn.com", "gb.com", "gb.net", "de.com", "kr.com", "ru.com", "sa.com",
    "br.com", "za.com", "ae.org", "hu.net", "se.net", "in.net",
)

ALLOW = "allow"
BLOCK = "block"
UNKNOWN = "unknown"

NOTE_BLOCK = "（不審サイトのためリンク削除）"
NOTE_UNKNOWN = "（未確認の出典のためリンク省略）"


def _host(url: str) -> str:
    try:
        return (urlparse(url.strip()).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def _match(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def classify_url(url: str) -> str:
    """URL を allow / block / unknown に分類する"""
    host = _host(url)
    if not host:
        return UNKNOWN
    if any(_match(host, d) for d in BLOCK_DOMAINS):
        return BLOCK
    if any(host.endswith("." + d) for d in BLOCK_PSEUDO_SLD):
        return BLOCK
    if any(host.endswith(s) for s in ALLOW_SUFFIXES):
        return ALLOW
    if any(_match(host, d) for d in ALLOW_DOMAINS):
        return ALLOW
    return UNKNOWN


def is_fetch_blocked(url: str) -> bool:
    """fetch_url での取得を拒否すべきか（未確認ドメインは調査のため取得を許可する）"""
    return classify_url(url) == BLOCK


# [テキスト](URL) 形式（画像 ![..](..) も含む）
_MD_LINK = re.compile(r"(!?)\[([^\]]*)\]\((https?://[^)\s]+)\)")
# 自動リンク <URL>（中の URL は裸 URL として検査する）
_AUTOLINK = re.compile(r"<(https?://[^\s<>]+)>")
# 裸の URL（Markdown リンクの外側だけに適用する）
_BARE_URL = re.compile(r"https?://[^\s()<>\[\]\"'|（）]+")


def sanitize_links(text: str):
    """記事本文のリンクを検査して置換する。戻り値: (置換後テキスト, 除去したURLのリスト[(分類, URL)])"""
    removed = []

    def _md(m):
        bang, label, url = m.group(1), m.group(2), m.group(3)
        kind = classify_url(url)
        if kind == ALLOW:
            return m.group(0)
        removed.append((kind, url))
        note = NOTE_BLOCK if kind == BLOCK else NOTE_UNKNOWN
        return f"{label}{note}" if label else note

    text = _MD_LINK.sub(_md, text)
    text = _AUTOLINK.sub(lambda m: m.group(1) if classify_url(m.group(1)) != ALLOW else m.group(0), text)

    def _bare(m):
        url = m.group(0)
        kind = classify_url(url)
        if kind == ALLOW:
            return url
        removed.append((kind, url))
        return NOTE_BLOCK if kind == BLOCK else NOTE_UNKNOWN

    # 許可済みの Markdown リンク・自動リンクの URL 部分を誤って裸 URL として扱わないよう、
    # それらの外側だけを処理する
    parts = []
    pos = 0
    keep = re.compile(_MD_LINK.pattern + "|" + _AUTOLINK.pattern)
    for m in keep.finditer(text):
        parts.append(_BARE_URL.sub(_bare, text[pos:m.start()]))
        parts.append(m.group(0))
        pos = m.end()
    parts.append(_BARE_URL.sub(_bare, text[pos:]))
    return "".join(parts), removed


def format_report(removed) -> str:
    """ログ用の除去レポート"""
    if not removed:
        return "link_guard: 除去なし"
    lines = [f"link_guard: {len(removed)} 件のリンクを除去"]
    for kind, url in removed:
        lines.append(f"  [{kind}] {url}")
    return "\n".join(lines)
