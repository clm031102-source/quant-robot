from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.assets.etf_universe import cn_etf_asset
from quant_robot.storage.dataset_store import DatasetStore


CN_ETF_THEME_MAP_COLUMNS = [
    "asset_id",
    "symbol",
    "name",
    "theme",
    "fund_type",
    "type",
    "list_date",
    "delist_date",
    "known_date",
    "source",
]

_THEME_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bond_cash", ("货币", "保证金", "现金", "国债", "地方政府债", "政金债", "企债", "公司债", "信用债", "可转债", "债")),
    ("commodity_gold", ("黄金", "上海金", "白银", "豆粕", "商品")),
    ("cross_border_hk", ("港股", "恒生", "H股", "香港", "中概")),
    ("cross_border_us_global", ("纳斯达克", "标普", "道琼斯", "美国", "日经", "德国", "法国", "巴西", "沙特", "QDII", "海外")),
    ("thematic_semiconductor", ("半导体", "芯片", "集成电路")),
    ("thematic_ai_digital", ("人工智能", "AI", "软件", "机器人", "互联网", "云计算", "大数据", "物联网", "信息技术", "数字", "计算机", "通信")),
    ("thematic_new_energy", ("新能源", "光伏", "电池", "储能", "碳中和", "电动汽车", "智能汽车", "绿色电力")),
    ("thematic_defense", ("军工", "国防", "航空航天")),
    ("sector_financial", ("证券", "银行", "保险", "金融", "非银", "财富管理")),
    ("sector_healthcare", ("医药", "医疗", "生物", "疫苗", "创新药", "中药")),
    ("sector_consumer", ("消费", "食品", "饮料", "白酒", "酒", "家电", "旅游", "传媒", "游戏")),
    ("sector_energy_materials", ("有色", "稀有金属", "稀土", "钢铁", "煤炭", "石油", "天然气", "化工", "材料", "原材料", "能源")),
    ("sector_agriculture", ("农业", "畜牧", "养殖", "粮食")),
    ("sector_industrials", ("工业", "机械", "装备", "基建", "运输", "物流", "电力")),
    ("dividend_value", ("红利", "高股息", "低波", "价值", "自由现金流", "分红")),
    ("size_style", ("成长", "小盘", "大盘", "中小盘", "中小板", "等权", "增强")),
    ("broad_market", ("沪深300", "中证500", "中证1000", "中证2000", "中证800", "上证50", "上证180", "深证100", "深证成指", "创业板", "科创50", "A50", "MSCI中国A股")),
)


def load_cn_etf_theme_map(root: str | Path, market: str = "CN_ETF") -> pd.DataFrame:
    if market.upper() != "CN_ETF":
        raise ValueError("CN ETF theme map requires market=CN_ETF")
    root_path = Path(root)
    snapshot = _latest_tushare_fund_basic_snapshot(root_path)
    fund_basic = DatasetStore(root_path).read_frame(
        "metadata/tushare_fund_basic",
        {"market": "E", "snapshot": snapshot},
    )
    return build_cn_etf_theme_map(fund_basic, source=f"tushare_fund_basic:{snapshot}")


def build_cn_etf_theme_map(fund_basic: pd.DataFrame, *, source: str = "tushare_fund_basic") -> pd.DataFrame:
    if fund_basic.empty:
        return pd.DataFrame(columns=CN_ETF_THEME_MAP_COLUMNS)
    required = ["symbol", "name", "market"]
    missing = [column for column in required if column not in fund_basic.columns]
    if missing:
        raise ValueError(f"Tushare fund_basic theme map is missing columns: {', '.join(missing)}")
    frame = fund_basic.copy()
    symbols = frame["symbol"].astype(str).str.upper().str.strip()
    market = frame["market"].astype(str).str.upper().str.strip()
    is_etf = frame["is_etf"].astype(bool) if "is_etf" in frame.columns else _contains_etf(frame)
    exchange_traded = symbols.str.endswith((".SH", ".SZ"))
    frame = frame[market.eq("E") & is_etf & exchange_traded].copy()
    if frame.empty:
        return pd.DataFrame(columns=CN_ETF_THEME_MAP_COLUMNS)
    frame["symbol"] = symbols[frame.index]
    frame["asset_id"] = [
        cn_etf_asset(str(row["symbol"]), str(row.get("name", ""))).asset_id for _, row in frame.iterrows()
    ]
    frame["fund_type"] = _text_column(frame, "fund_type")
    frame["type"] = _text_column(frame, "type")
    frame["name"] = _text_column(frame, "name")
    frame["theme"] = [
        classify_cn_etf_theme(name=str(row["name"]), fund_type=str(row["fund_type"]), type_=str(row["type"]))
        for _, row in frame.iterrows()
    ]
    frame["list_date"] = _date_column(frame, "list_date")
    frame["delist_date"] = _date_column(frame, "delist_date")
    found_date = _date_column(frame, "found_date")
    frame["known_date"] = frame["list_date"].where(frame["list_date"].notna(), found_date)
    frame["source"] = source
    return (
        frame[CN_ETF_THEME_MAP_COLUMNS]
        .drop_duplicates(["asset_id"], keep="first")
        .sort_values(["theme", "asset_id"])
        .reset_index(drop=True)
    )


def classify_cn_etf_theme(*, name: str, fund_type: str = "", type_: str = "") -> str:
    haystack = f"{name} {fund_type} {type_}".upper()
    for theme, keywords in _THEME_RULES:
        if any(keyword.upper() in haystack for keyword in keywords):
            return theme
    if "ETF" in haystack:
        return "other_equity"
    return "unclassified"


def _latest_tushare_fund_basic_snapshot(root: Path) -> str:
    base = root / "metadata" / "tushare_fund_basic" / "market=E"
    snapshots = sorted(
        path.name.split("=", 1)[1]
        for path in base.glob("snapshot=*")
        if path.is_dir() and "=" in path.name
    )
    if not snapshots:
        raise FileNotFoundError(f"No Tushare fund_basic snapshots found under {base}")
    return snapshots[-1]


def _contains_etf(frame: pd.DataFrame) -> pd.Series:
    columns = [column for column in ["name", "fund_type", "invest_type", "type"] if column in frame.columns]
    if not columns:
        return pd.Series([False] * len(frame), index=frame.index)
    haystack = frame[columns].fillna("").astype(str).agg(" ".join, axis=1).str.upper()
    return haystack.str.contains("ETF", regex=False)


def _text_column(frame: pd.DataFrame, column: str) -> pd.Series:
    values: Any = frame[column] if column in frame.columns else ""
    return pd.Series(values, index=frame.index).fillna("").astype(str)


def _date_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([pd.NaT] * len(frame), index=frame.index)
    return pd.to_datetime(frame[column], errors="coerce").dt.date
