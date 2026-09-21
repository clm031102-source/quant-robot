"""Explicit gross-as-cash assumption for conditional historical research only."""
from quant_robot.paper.corporate_actions import CorporateActionLedger


class AnnouncedCashResearchLedger(CorporateActionLedger):
    def _cash_per_share(self, event):
        if event.get('cash_amount_basis') != 'gross':
            raise ValueError('Gross research ledger requires explicit gross amounts without mixed bases')
        return event['cash_per_share']

    def evidence(self):
        return {**super().evidence(), 'cash_amount_basis': 'gross_announcement_assumption',
            'net_cash_verified': False, 'conditional_research_only': True,
            'account_performance_admission_verified': False,
            'cash_assumption': 'full announced gross cash credited after pay-date close; investor deductions unverified'}
