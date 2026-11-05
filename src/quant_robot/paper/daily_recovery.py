"""Fixed prospective pause policy; never changes the global drawdown peak."""
from decimal import Decimal

RECOVERY = dict(daily_loss_fraction_previous_NAV=.02,
    complete_flat_sessions=5, exit='next_session_open_subject_to_constraints',
    resume='new_preexisting_signal_cycle_only_no_retry',
    drawdown='original_8percent_peak_permanent_no_reset')


class DailyRecovery:
    def __init__(self, policy):
        if policy != RECOVERY:
            raise ValueError('Exact frozen daily recovery policy required')
        self.paused = False
        self.flat_index = None
        self.journal = []

    def before_open(self, index, day, *, positions, permanently_halted):
        if (self.paused and not permanently_halted and not positions
                and self.flat_index is not None and index > self.flat_index + 5):
            self.paused = False
            self.flat_index = None
            self.journal.append(dict(date=day,kind='eligible_after_five_complete_flat_sessions'))

    def after_close(self, index, day, *, previous, equity, positions):
        threshold = previous * Decimal('.02')
        if previous-equity >= threshold:
            self.paused = True
            self.flat_index = None
            self.journal.append(dict(date=day,kind='daily_loss_pause',
                previous_NAV=previous,loss=previous-equity,threshold=threshold))
        if self.paused and not positions and self.flat_index is None:
            self.flat_index = index
            self.journal.append(dict(date=day,kind='flat_cooldown_started',
                earliest_eligible_session_index=index+6))
