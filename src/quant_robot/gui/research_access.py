"""Keep unregistered GUI requests out of protected research datasets.

The generic GUI carries no fingerprinted preregistration, consumed-run ledger,
source authority or holdout authorization. A date range, a source path or a
client flag cannot supply those missing capabilities. Authorized research uses
its dedicated reviewed entrypoint; this module does not issue authorizations.
"""
from __future__ import annotations


class GuiResearchAccessDenied(ValueError):
    def __init__(self, market: str):
        super().__init__(
            '当前界面尚未接入真实数据研究准入。请使用已完成预注册、数据范围和研究额度核验的'
            '专用入口；界面可继续使用示例数据演练。此请求未读取真实行情或生成信号。'
        )
        self.market = market

    def payload(self) -> dict[str, object]:
        return {'stage': 'gui_research_access', 'status': 'research_access_denied',
                'error': str(self), 'market': self.market,
                'reason': 'generic_gui_has_no_bound_research_authorization',
                'factor_generation_allowed': False, 'forward_return_read_allowed': False,
                'paper_signal_allowed': False, 'live_boundary_allowed': False}


def require_gui_research_access(source: str, market: str) -> None:
    """Reject protected processed-data work before any candidate/data reads.

ALL includes the protected CN_ETF market. No query flag, environment flag or
arbitrary local authorization file is accepted as a generic bypass.
"""
    normalized_source = source.strip().lower().replace('_', '-')
    normalized_market = market.strip().upper()
    if normalized_source == 'processed-bars' and normalized_market in {'CN_ETF', 'CN', 'ALL'}:
        raise GuiResearchAccessDenied(normalized_market)
