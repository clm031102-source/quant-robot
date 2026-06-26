from __future__ import annotations

from collections.abc import Callable
from time import sleep

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.config.secrets import require_env_secret
from quant_robot.data.adapters.base import FetchRequest, MarketDataAdapter, require_optional_dependency
from quant_robot.data.sources.tushare_mapping import (
    map_tushare_adj_factor,
    map_tushare_balance_sheet,
    map_tushare_cashflow_statement,
    map_tushare_daily,
    map_tushare_daily_basic,
    map_tushare_etf_share_size,
    map_tushare_fina_indicator,
    map_tushare_fund_basic,
    map_tushare_fund_portfolio,
    map_tushare_income_statement,
    map_tushare_moneyflow,
    map_tushare_stock_basic,
    map_tushare_trade_cal,
)


class TushareAdapter(MarketDataAdapter):
    name = "tushare"

    def __init__(
        self,
        client: object | None = None,
        max_retries: int = 3,
        retry_sleep_seconds: float = 1.0,
        request_sleep_seconds: float = 0.0,
    ) -> None:
        self._client = client
        self.max_retries = max_retries
        self.retry_sleep_seconds = retry_sleep_seconds
        self.request_sleep_seconds = request_sleep_seconds

    def supports(self, asset: Asset) -> bool:
        return asset.market.upper() in {"CN", "CN_ETF"}

    def fetch_ohlcv(self, asset: Asset, request: FetchRequest) -> pd.DataFrame:
        method = self.client.fund_daily if asset.market.upper() == "CN_ETF" else self.client.daily
        raw = self._call(
            method,
            ts_code=asset.symbol,
            start_date=_date_to_tushare(request.start),
            end_date=_date_to_tushare(request.end),
        )
        return map_tushare_daily(raw)

    def fetch_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        raw = self._call(self.client.daily, trade_date=_date_to_tushare(trade_date))
        return map_tushare_daily(raw)

    def fetch_etf_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        raw = self._call(self.client.fund_daily, trade_date=_date_to_tushare(trade_date))
        return map_tushare_daily(raw)

    def fetch_daily_basic_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        raw = self._call(self.client.daily_basic, trade_date=_date_to_tushare(trade_date))
        return map_tushare_daily_basic(raw)

    def fetch_moneyflow_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        raw = self._call(self.client.moneyflow, trade_date=_date_to_tushare(trade_date))
        return map_tushare_moneyflow(raw)

    def fetch_margin_detail_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        return self._call(self.client.margin_detail, trade_date=_date_to_tushare(trade_date))

    def fetch_hk_hold_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        return self._call(self.client.hk_hold, trade_date=_date_to_tushare(trade_date))

    def fetch_moneyflow_hsgt_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        return self._call(self.client.moneyflow_hsgt, trade_date=_date_to_tushare(trade_date))

    def fetch_top_list_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        return self._call(self.client.top_list, trade_date=_date_to_tushare(trade_date))

    def fetch_top_inst_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        return self._call(self.client.top_inst, trade_date=_date_to_tushare(trade_date))

    def fetch_index_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._call(
            self.client.index_daily,
            ts_code=ts_code,
            start_date=_date_to_tushare(start_date),
            end_date=_date_to_tushare(end_date),
        )

    def fetch_index_dailybasic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._call(
            self.client.index_dailybasic,
            ts_code=ts_code,
            start_date=_date_to_tushare(start_date),
            end_date=_date_to_tushare(end_date),
        )

    def fetch_index_weight(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._call(
            self.client.index_weight,
            index_code=index_code,
            start_date=_date_to_tushare(start_date),
            end_date=_date_to_tushare(end_date),
        )

    def fetch_shibor_by_date(self, date: str) -> pd.DataFrame:
        return self._call(self.client.shibor, date=_date_to_tushare(date))

    def fetch_shibor_lpr(self) -> pd.DataFrame:
        return self._call(self.client.shibor_lpr)

    def fetch_stk_limit_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        return self._call(self.client.stk_limit, trade_date=_date_to_tushare(trade_date))

    def fetch_suspend_d_by_date(self, trade_date: str) -> pd.DataFrame:
        return self._call(self.client.suspend_d, trade_date=_date_to_tushare(trade_date))

    def fetch_namechange(self, start_date: str, end_date: str) -> pd.DataFrame:
        return self._call(
            self.client.namechange,
            start_date=_date_to_tushare(start_date),
            end_date=_date_to_tushare(end_date),
        )

    def fetch_fina_indicator(
        self,
        ts_code: str = "",
        period: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> pd.DataFrame:
        raw = self._call(
            self.client.fina_indicator,
            ts_code=ts_code,
            period=_date_to_tushare(period) if period else "",
            start_date=_date_to_tushare(start_date) if start_date else "",
            end_date=_date_to_tushare(end_date) if end_date else "",
        )
        return map_tushare_fina_indicator(raw)

    def fetch_income_statement(
        self,
        ts_code: str = "",
        period: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> pd.DataFrame:
        raw = self._call(
            self.client.income,
            ts_code=ts_code,
            period=_date_to_tushare(period) if period else "",
            start_date=_date_to_tushare(start_date) if start_date else "",
            end_date=_date_to_tushare(end_date) if end_date else "",
        )
        return map_tushare_income_statement(raw)

    def fetch_balance_sheet(
        self,
        ts_code: str = "",
        period: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> pd.DataFrame:
        raw = self._call(
            self.client.balancesheet,
            ts_code=ts_code,
            period=_date_to_tushare(period) if period else "",
            start_date=_date_to_tushare(start_date) if start_date else "",
            end_date=_date_to_tushare(end_date) if end_date else "",
        )
        return map_tushare_balance_sheet(raw)

    def fetch_cashflow_statement(
        self,
        ts_code: str = "",
        period: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> pd.DataFrame:
        raw = self._call(
            self.client.cashflow,
            ts_code=ts_code,
            period=_date_to_tushare(period) if period else "",
            start_date=_date_to_tushare(start_date) if start_date else "",
            end_date=_date_to_tushare(end_date) if end_date else "",
        )
        return map_tushare_cashflow_statement(raw)

    def fetch_adj_factor(self, ts_code: str = "", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        raw = self._call(
            self.client.adj_factor,
            ts_code=ts_code,
            start_date=_date_to_tushare(start_date) if start_date else "",
            end_date=_date_to_tushare(end_date) if end_date else "",
        )
        return map_tushare_adj_factor(raw)

    def fetch_adj_factor_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        raw = self._call(self.client.adj_factor, trade_date=_date_to_tushare(trade_date))
        return map_tushare_adj_factor(raw)

    def fetch_trade_calendar(self, start_date: str, end_date: str, exchange: str = "SSE") -> pd.DataFrame:
        raw = self._call(
            self.client.trade_cal,
            exchange=exchange,
            is_open="1",
            start_date=_date_to_tushare(start_date),
            end_date=_date_to_tushare(end_date),
        )
        return map_tushare_trade_cal(raw, open_only=True)

    def fetch_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        raw = self._call(
            self.client.stock_basic,
            exchange="",
            list_status=list_status,
            fields="ts_code,symbol,name,area,industry,market,exchange,list_status,list_date,delist_date,is_hs",
        )
        return map_tushare_stock_basic(raw)

    def fetch_fund_basic(self, market: str = "E", status: str = "L") -> pd.DataFrame:
        raw = self._call(
            self.client.fund_basic,
            market=market,
            status=status,
            fields=(
                "ts_code,name,management,custodian,fund_type,found_date,due_date,"
                "list_date,issue_date,delist_date,status,invest_type,type,market"
            ),
        )
        return map_tushare_fund_basic(raw)

    def fetch_etf_share_size_by_trade_date(self, trade_date: str, exchange: str = "") -> pd.DataFrame:
        raw = self._call(
            self.client.etf_share_size,
            trade_date=_date_to_tushare(trade_date),
            exchange=exchange,
            fields="trade_date,ts_code,etf_name,total_share,total_size,nav,close,exchange",
        )
        return map_tushare_etf_share_size(raw)

    def fetch_fund_portfolio(self, ts_code: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        raw = self._call(
            self.client.fund_portfolio,
            ts_code=ts_code,
            start_date=_date_to_tushare(start_date) if start_date else "",
            end_date=_date_to_tushare(end_date) if end_date else "",
            fields="ts_code,ann_date,end_date,symbol,mkv,amount,stk_mkv_ratio,stk_float_ratio",
        )
        return map_tushare_fund_portfolio(raw)

    def fetch_report_rc(self, start_date: str = "", end_date: str = "", ts_code: str = "") -> pd.DataFrame:
        kwargs = {
            "start_date": _date_to_tushare(start_date) if start_date else "",
            "end_date": _date_to_tushare(end_date) if end_date else "",
            "ts_code": ts_code,
        }
        return self._call(self.client.report_rc, **{key: value for key, value in kwargs.items() if value})

    @property
    def client(self) -> object:
        if self._client is None:
            self._client = _create_tushare_client()
        return self._client

    def _call(self, method: Callable[..., pd.DataFrame], **kwargs: object) -> pd.DataFrame:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                result = method(**kwargs)
                if self.request_sleep_seconds > 0:
                    sleep(self.request_sleep_seconds)
                return result
            except Exception as exc:  # pragma: no cover - exercised with live providers
                last_error = exc
                if attempt < self.max_retries - 1:
                    sleep(self.retry_sleep_seconds)
        detail = f": {last_error}" if last_error is not None else ""
        raise RuntimeError(f"Tushare request failed after {self.max_retries} attempts{detail}") from last_error


def _create_tushare_client() -> object:
        require_optional_dependency("tushare")
        import tushare as ts  # type: ignore[import-not-found]

        return ts.pro_api(require_env_secret("TUSHARE_TOKEN"))


def _date_to_tushare(value: str) -> str:
    return value.replace("-", "")
