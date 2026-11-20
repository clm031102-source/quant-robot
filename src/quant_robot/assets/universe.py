"""Canonical asset universe resolvers for CN ETF, US ETF, CN stock, HK, and crypto."""
from __future__ import annotations

from quant_robot.assets.etf_universe import cn_etf_asset
from quant_robot.assets.models import Asset

CN_ETF_NAMES: dict[str, str] = {
    "510300.SH": "沪深300ETF",
    "510500.SH": "中证500ETF",
    "159915.SZ": "创业板ETF",
    "588000.SH": "科创50ETF",
    "510880.SH": "红利ETF",
    "511010.SH": "国债ETF",
    "511260.SH": "十年国债ETF",
    "511880.SH": "银华日利货币ETF",
    "518880.SH": "黄金ETF",
    "513100.SH": "纳指ETF",
    "513050.SH": "中概互联ETF",
    "159941.SZ": "纳指ETF(深)",
}

US_ETF_NAMES: dict[str, str] = {
    "SPYM": "SPDR Portfolio S&P 500 ETF",
    "SPY": "SPDR S&P 500 ETF",
    "QQQ": "Invesco QQQ Trust",
    "EFA": "iShares MSCI EAFE ETF",
    "IEF": "iShares 7-10 Year Treasury Bond ETF",
    "SHY": "iShares 1-3 Year Treasury Bond ETF",
    "GLDM": "SPDR Gold MiniShares Trust",
    "GLD": "SPDR Gold Shares",
}


def us_etf_asset(symbol: str, name: str = "") -> Asset:
    code = symbol.strip().upper()
    return Asset(
        asset_id=f"US_ETF_XNYS_{code}",
        symbol=code,
        market="US_ETF",
        exchange="XNYS",
        asset_type="etf",
        currency="USD",
        timezone="America/New_York",
        calendar="XNYS",
        name=name or US_ETF_NAMES.get(code, code),
        lot_size=1.0,
        tick_size=0.01,
    )


def resolve_asset(symbol: str, market: str) -> Asset:
    market_upper = market.strip().upper()
    code = symbol.strip().upper()
    if market_upper == "CN_ETF":
        normalized = code if "." in code else (f"{code}.SZ" if code.startswith(("15", "16")) else f"{code}.SH")
        return cn_etf_asset(normalized, CN_ETF_NAMES.get(normalized, normalized))
    if market_upper in {"US", "US_ETF"}:
        return us_etf_asset(code)
    if market_upper == "CN":
        normalized = code if "." in code else (f"{code}.SH" if code.startswith("6") else f"{code}.SZ")
        exchange = "XSHG" if normalized.endswith(".SH") else "XSHE"
        return Asset(
            asset_id=f"CN_{exchange}_{normalized.split('.', 1)[0]}",
            symbol=normalized,
            market="CN",
            exchange=exchange,
            asset_type="stock",
            currency="CNY",
            timezone="Asia/Shanghai",
            calendar=exchange,
            name=normalized,
            lot_size=100.0,
            tick_size=0.01,
        )
    if market_upper == "HK":
        return Asset(
            asset_id=f"HK_XHKG_{code.replace('.HK', '')}",
            symbol=code if code.endswith(".HK") else f"{code}.HK",
            market="HK",
            exchange="XHKG",
            asset_type="stock",
            currency="HKD",
            timezone="Asia/Hong_Kong",
            calendar="XHKG",
            name=code,
            lot_size=100.0,
            tick_size=0.01,
        )
    if market_upper == "CRYPTO":
        safe = code.replace("/", "_")
        return Asset(
            asset_id=f"CRYPTO_SPOT_{safe}",
            symbol=code,
            market="CRYPTO",
            exchange="SPOT",
            asset_type="crypto_spot",
            currency="USDT",
            timezone="UTC",
            calendar="24/7",
            name=code,
            lot_size=0.0001,
            tick_size=0.01,
        )
    raise ValueError(f"Unsupported market: {market}")
