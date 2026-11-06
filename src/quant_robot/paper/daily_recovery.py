"""Fixed prospective pause policy; never changes the global drawdown peak."""
from decimal import Decimal

RECOVERY = dict(daily_loss_fraction_previous_NAV=.02,
    complete_flat_sessions=5, exit='next_session_open_subject_to_constraints',
    resume='new_preexisting_signal_cycle_only_no_retry',
    drawdown='original_8percent_peak_permanent_no_reset')

RECOVERY_40 = {**RECOVERY,
    'drawdown': 'global_40percent_pause_on_exposed_session_no_peak_reset'}

RECOVERY_40_DAILY_RETRY = {**RECOVERY_40,
    'resume': 'current_daily_desired_position_after_five_complete_flat_sessions'}


class DailyRecovery:
    def __init__(self, policy):
        if policy not in (RECOVERY, RECOVERY_40, RECOVERY_40_DAILY_RETRY):
            raise ValueError('Exact frozen daily recovery policy required')
        self.recover_drawdown = policy in (RECOVERY_40, RECOVERY_40_DAILY_RETRY)
        self.paused = False
        self.flat_index = None
        self.journal = []

    def before_open(self, index, day, *, positions, permanently_halted):
        if (self.paused and not permanently_halted and not positions
                and self.flat_index is not None and index > self.flat_index + 5):
            self.paused = False
            self.flat_index = None
            self.journal.append(dict(date=day,kind='eligible_after_five_complete_flat_sessions'))

    def after_close(self, index, day, *, previous, equity, positions,
                    drawdown=None, had_exposure=None):
        if self.recover_drawdown and (drawdown is None or had_exposure is None):
            raise ValueError('Global drawdown and exposure state required')
        threshold = previous * Decimal('.02')
        if previous-equity >= threshold:
            self.paused = True
            self.flat_index = None
            self.journal.append(dict(date=day,kind='daily_loss_pause',
                previous_NAV=previous,loss=previous-equity,threshold=threshold))
        if self.recover_drawdown and had_exposure and drawdown >= Decimal('.40'):
            self.paused = True
            self.flat_index = None
            self.journal.append(dict(date=day,kind='global_drawdown_pause',
                global_drawdown=drawdown,threshold=Decimal('.40')))
        # Cash-only days below the original peak must not restart cooling.
        if self.paused and not positions and self.flat_index is None:
            self.flat_index = index
            self.journal.append(dict(date=day,kind='flat_cooldown_started',
                earliest_eligible_session_index=index+6))
