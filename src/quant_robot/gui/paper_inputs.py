"""Pin explicit GUI paper inputs without granting research or source authority."""
from __future__ import annotations

import hashlib
import math
from numbers import Real
from pathlib import Path
import re

from quant_robot.gui.research_access import normalize_gui_source, require_gui_research_access
from quant_robot.paper.fixed_hold_attachment import attach_fixed_hold_comparison, load_fixed_hold_entries

FILE_PIN_FIELDS = {
    'corporate_actions_path': 'corporate_actions_fingerprint',
    'fixed_hold_benchmark_path': 'fixed_hold_benchmark_sha256',
}
MAX_INPUT_BYTES = 16 * 1024 * 1024


class PaperInputError(ValueError):
    """An explained local simulation input error, with no successful receipt."""


def prepare_gui_paper_inputs(*, source='demo_fixture', market='ALL',
                             corporate_actions_path=None, fixed_hold_benchmark_path=None):
    source = normalize_gui_source(source)
    require_gui_research_access(source, market)
    paths = {'corporate_actions_path': corporate_actions_path,
             'fixed_hold_benchmark_path': fixed_hold_benchmark_path}
    pins, files = {}, []
    for field, path in paths.items():
        if path is None or path == '':
            continue
        if not isinstance(path, (str, Path)):
            raise PaperInputError('输入文件路径必须是本地文件名')
        try:
            with Path(path).open('rb') as stream:
                raw = stream.read(MAX_INPUT_BYTES + 1)
        except OSError as exc:
            raise PaperInputError(f'无法读取模拟输入文件：{path}') from exc
        if len(raw) > MAX_INPUT_BYTES:
            raise PaperInputError('模拟声明文件超过16MB，尚未固定输入版本')
        fingerprint = hashlib.sha256(raw).hexdigest()
        pins[FILE_PIN_FIELDS[field]] = fingerprint
        files.append({'field':field, 'path':str(path), 'bytes':len(raw), 'sha256':fingerprint})
    return {'stage':'gui_paper_input_versions', 'source':source, 'market':market.strip().upper(),
            'pins':pins, 'files':files, 'source_quality_verified':False,
            'research_admission_verified':False, 'executable':False}


def validate_gui_paper_inputs(*, source, market, market_impact_bps, max_participation_rate,
                              corporate_actions_path=None, fixed_hold_benchmark_path=None,
                              corporate_actions_fingerprint=None, fixed_hold_benchmark_sha256=None):
    require_gui_research_access(normalize_gui_source(source), market)
    for value, name in ((market_impact_bps, '冲击成本'), (max_participation_rate, '成交参与率')):
        if value is None and name == '成交参与率':
            continue
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
            raise PaperInputError(f'{name}必须是有效的非负数')
    if max_participation_rate is not None and not 0 < max_participation_rate <= 1:
        raise PaperInputError('成交参与率必须大于0且不超过1')
    if fixed_hold_benchmark_path and (market.strip().upper() != 'CN_ETF' or
            not corporate_actions_path or max_participation_rate is None):
        raise PaperInputError('固定持有对照需要CN_ETF、明确权益文件和成交参与率')
    paths = {'corporate_actions_path': corporate_actions_path,
             'fixed_hold_benchmark_path': fixed_hold_benchmark_path}
    expected = {'corporate_actions_fingerprint':corporate_actions_fingerprint,
                'fixed_hold_benchmark_sha256':fixed_hold_benchmark_sha256}
    for field, pin in FILE_PIN_FIELDS.items():
        if paths[field]:
            if not isinstance(expected[pin], str) or not re.fullmatch('[0-9a-f]{64}', expected[pin]):
                raise PaperInputError('请先读取并固定输入文件版本，再运行模拟')
        elif expected[pin] is not None and expected[pin] != '':
            raise PaperInputError('文件版本信息缺少对应的输入路径')
    prepared = prepare_gui_paper_inputs(source=source, market=market, **paths)
    if any(expected[key] != value for key, value in prepared['pins'].items()):
        raise PaperInputError('输入文件版本已变化，请重新读取后再运行')
    entries = load_fixed_hold_entries(fixed_hold_benchmark_path) if fixed_hold_benchmark_path else None
    if entries and entries[1] != fixed_hold_benchmark_sha256:
        raise PaperInputError('固定持有清单版本在读取时发生变化')
    return prepared, entries


def verify_result_input_pins(result, prepared):
    actual = result.get('request', {})
    if any(actual.get(key) != value for key, value in prepared['pins'].items()):
        raise PaperInputError('模拟实际使用的文件版本与已固定版本不一致')


def complete_gui_paper_inputs(bars, result, prepared, fixed_hold, benchmark_path):
    if fixed_hold is not None:
        result = attach_fixed_hold_comparison(bars, result, entries=fixed_hold[0],
            source_path=benchmark_path, source_sha256=fixed_hold[1])
    verify_result_input_pins(result, prepared)
    result['input_versions'] = prepared
    result['request']['source'] = prepared['source']
    return result
