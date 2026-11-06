"""Narrow retained-2024-report adapters for 518880 historical input diagnostics.

Re-extract original PDF pages, bind the official catalog/capture receipts, and
require a separately reviewed metadata fingerprint in application code. The
annual report was obtained later: it cannot establish a 2024 information set,
daily tradability, absence of intraday suspensions, or strategy qualification.
"""
from datetime import datetime, timedelta
from hashlib import sha256
import io
from pathlib import Path
import re
import unicodedata

from quant_robot.ops.paper_source_bundle import BundleError, Evidence, SourceAdapter


TYPE = 'sse_annual_518880_2024_input_v1'
ASSET = 'CN_ETF_XSHG_518880'
FUND = '华安易富黄金交易型开放式证券投资基金'
TITLE = FUND + '2024年年度报告'
REPORT_URL = 'https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-03-31/518880_20250331_1BBG.pdf'
PAGES = (1, 2, 5, 15, 52)


def _compact(text):
    return ''.join(unicodedata.normalize('NFKC', text).split())


def parse_annual_sections(pages):
    """Only the observed fixed layout; incompatible reports require new review."""
    if (set(pages) != set(PAGES) or any(not isinstance(value, str) or not value
            or len(value) > 20000 for value in pages.values())):
        raise BundleError('bounded_selected_annual_sections_required')
    text = {page: _compact(value) for page, value in pages.items()}
    if (not text[1].startswith(TITLE) or '送出日期:2025年3月31日' not in text[1]
            or '本报告期自2024年1月1日起至12月31日止。' not in text[2]):
        raise BundleError('annual_identity_publication_or_coverage_mismatch')
    required = ('基金名称'+FUND, '基金主代码518880', '基金运作方式交易型开放式',
                '基金份额上市的证券交易所上海证券交易所', '上市日期2013年7月29日')
    if any(value not in text[5] for value in required):
        raise BundleError('annual_ETF_identity_or_listing_mismatch')
    distribution = re.findall(r'4\.8管理人对报告期内基金利润分配情况的说明(.*?)4\.9', text[15])
    if distribution != ['本报告期不进行收益分配。']:
        raise BundleError('annual_explicit_no_distribution_statement_required')
    split = re.findall(r'本报告期基金拆分变动份额(.*?)本报告期期末基金份额总额', text[52])
    if split != ['-']:
        raise BundleError('annual_explicit_no_split_movement_required')
    return dict(asset_id=ASSET, report_year=2024, publication_date='2025-03-31',
        listing_date='2013-07-29', coverage_start='2024-01-01', coverage_end='2024-12-31',
        no_cash_distributions_reported=True, no_split_movement_reported=True,
        historical_point_in_time_certified=False, daily_tradability_certified=False)


def _extract_pdf(raw):
    if not raw.startswith(b'%PDF-') or len(raw) > 2_000_000:
        raise BundleError('bounded_original_annual_PDF_required')
    try:
        import pypdf
    except ImportError as exc:
        raise BundleError('optional_pdf_sources_dependency_required') from exc
    reader = pypdf.PdfReader(io.BytesIO(raw))
    if reader.is_encrypted or not 52 <= len(reader.pages) <= 100:
        raise BundleError('unsupported_annual_PDF_layout')
    pages = {number: reader.pages[number-1].extract_text() or '' for number in PAGES}
    return pages, pypdf.__version__


def _utc(value):
    if not isinstance(value, str) or 'T' not in value:
        raise BundleError('annual_receipt_UTC_required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise BundleError('annual_receipt_UTC_required')
    return parsed.isoformat().replace('+00:00', 'Z')


def _capture(context, raw_ref, receipt_ref, *, scope_hash, url):
    raw = context.read_bytes(raw_ref)
    receipt = context.read_json(receipt_ref)
    if (receipt.get('status') != 'retained_current_source_version'
            or receipt.get('http_status') != 200 or receipt.get('url') != url
            or receipt.get('sha256') != raw_ref['sha256'] or receipt.get('bytes') != len(raw)
            or receipt.get('scope_sha256') != scope_hash
            or Path(receipt.get('path', '')).as_posix() != Path(raw_ref['path']).as_posix()):
        raise BundleError('annual_capture_receipt_does_not_bind_original')
    started, received = _utc(receipt['claimed_at']), _utc(receipt['completed_at'])
    if datetime.fromisoformat(started.replace('Z','+00:00')) > datetime.fromisoformat(received.replace('Z','+00:00')):
        raise BundleError('annual_capture_clock_order_invalid')
    if (datetime.fromisoformat(received.replace('Z','+00:00'))+timedelta(hours=8)).date().isoformat() < '2025-03-31':
        raise BundleError('annual_receipt_precedes_publication_date')
    return raw, received


def _catalog(context, raw_ref):
    catalog = context.read_json(raw_ref)
    page = catalog['pageHelp']
    rows = catalog['result']
    if (not isinstance(rows, list) or not 1 <= len(rows) <= 100 or page['data'] != rows
            or page['pageNo'] != 1 or page['pageCount'] != 1 or page['total'] != len(rows)
            or catalog.get('actionErrors') != [] or catalog.get('fieldErrors') != {}):
        raise BundleError('complete_single_page_annual_catalog_required')
    matches = [row for row in rows if row.get('TITLE') == TITLE]
    if (len(matches) != 1 or matches[0].get('SECURITY_CODE') != '518880'
            or matches[0].get('SSEDATE') != '2025-03-31'
            or 'https://www.sse.com.cn'+matches[0].get('URL','') != REPORT_URL):
        raise BundleError('official_annual_catalog_identity_mismatch')


def retained_annual_adapters(*, reviewed_metadata_sha256):
    """Application registration pins the independently reviewed original bundle.

    The returned empty action index is a *derived annual coverage summary*, not
    an empty provider action query or claimed first-publication-time snapshot.
    Identity units name the existing normalized CN-ETF daily-price contract.
    """
    if re.fullmatch(r'[0-9a-f]{64}', reviewed_metadata_sha256 or '') is None:
        raise BundleError('independently_reviewed_annual_metadata_binding_required')

    def parse(context, ref):
        if ref['sha256'] != reviewed_metadata_sha256:
            raise BundleError('annual_metadata_not_reviewed_version')
        metadata = context.read_json(ref)
        required = {'artifact_type','created_at','source_scope','pdf','pdf_receipt','catalog','catalog_receipt'}
        if set(metadata) != required or metadata['artifact_type'] != TYPE:
            raise BundleError('exact_reviewed_annual_metadata_required')
        scope = context.read_json(metadata['source_scope'])
        if scope.get('stage') != 'fixed_geopolitical_account_source_preparation':
            raise BundleError('original_annual_capture_scope_mismatch')
        pdf, pdf_received = _capture(context, metadata['pdf'], metadata['pdf_receipt'],
            scope_hash=metadata['source_scope']['sha256'], url=REPORT_URL)
        _, index_received = _capture(context, metadata['catalog'], metadata['catalog_receipt'],
            scope_hash=metadata['source_scope']['sha256'], url='https://query.sse.com.cn/commonQuery.do')
        _catalog(context, metadata['catalog'])
        pages, pdf_version = _extract_pdf(pdf)
        observations = parse_annual_sections(pages)
        if context.component == 'identity':
            facts = dict(asset_id=ASSET, instrument_type='ETF', currency='CNY',
                price_unit='CNY_per_fund_unit', volume_unit='fund_units', amount_unit='CNY',
                listing_date=observations['listing_date'], delisting_date=None,
                valid_from=observations['coverage_start'], valid_through=observations['coverage_end'])
        elif context.component == 'actions':
            facts = dict(asset_id=ASSET, coverage_start=observations['coverage_start'],
                coverage_end=observations['coverage_end'],
                pages=[dict(page_number=1,total_pages=1,total_records=0,records=[])], notices=[])
        else:
            raise BundleError('annual_adapter_component_not_supported')
        created = _utc(metadata['created_at'])
        if any(datetime.fromisoformat(created.replace('Z','+00:00')) < datetime.fromisoformat(value.replace('Z','+00:00'))
               for value in (pdf_received,index_received)):
            raise BundleError('annual_metadata_predates_its_originals')
        received = max((pdf_received,index_received,created),
                       key=lambda value:datetime.fromisoformat(value.replace('Z','+00:00')))
        context.recheck()
        return Evidence(facts, None, received, 'synthetic_only' if context.synthetic_seen else 'recorded_observation',
            dict(parser='pypdf', version=pdf_version,
                 implementation_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                 coverage_basis='retained_annual_report_explicit_no_distributions_and_no_split_movement',
                 source_vintage='later_retained_version_not_2024_information_set',
                 provider_first_publication_at=None, historical_point_in_time_certified=False))

    parameters = dict(reviewed_metadata_sha256=reviewed_metadata_sha256,
                      supported_asset=ASSET, report_year=2024)
    return {kind: SourceAdapter(kind, parse, parameters) for kind in ('identity','actions')}
