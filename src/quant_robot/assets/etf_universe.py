from __future__ import annotations

from quant_robot.assets.models import Asset


DEFAULT_CN_ETFS: tuple[tuple[str, str], ...] = (
    ("510300.SH", "沪深300 ETF"),
    ("510500.SH", "中证500 ETF"),
    ("159915.SZ", "创业板 ETF"),
    ("588000.SH", "科创50 ETF"),
    ("512100.SH", "中证1000 ETF"),
    ("512880.SH", "证券 ETF"),
    ("512690.SH", "酒 ETF"),
    ("515790.SH", "光伏 ETF"),
    ("516160.SH", "新能源 ETF"),
    ("159819.SZ", "人工智能 ETF"),
    ("511880.SH", "货币 ETF"),
)


def default_cn_etf_assets() -> list[Asset]:
    return [cn_etf_asset(symbol, name) for symbol, name in DEFAULT_CN_ETFS]


def resolve_cn_etf_asset(symbol: str) -> Asset:
    normalized = _normalize_symbol(symbol)
    names = {_normalize_symbol(item_symbol): name for item_symbol, name in DEFAULT_CN_ETFS}
    return cn_etf_asset(normalized, names.get(normalized, "A股ETF"))


def cn_etf_asset(symbol: str, name: str = "") -> Asset:
    normalized = _normalize_symbol(symbol)
    exchange = _exchange_for_symbol(normalized)
    return Asset(
        asset_id=f"CN_ETF_{exchange}_{normalized.split('.', 1)[0]}",
        symbol=normalized,
        market="CN_ETF",
        exchange=exchange,
        asset_type="etf",
        currency="CNY",
        timezone="Asia/Shanghai",
        calendar=exchange,
        name=name,
        lot_size=100.0,
        tick_size=0.001,
    )


def _normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if "." not in value:
        if value.startswith(("15", "16")):
            return f"{value}.SZ"
        return f"{value}.SH"
    return value


def _exchange_for_symbol(symbol: str) -> str:
    suffix = symbol.rsplit(".", 1)[-1]
    if suffix == "SH":
        return "XSHG"
    if suffix == "SZ":
        return "XSHE"
    raise ValueError(f"Unsupported CN ETF symbol suffix: {symbol}")
