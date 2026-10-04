"""French monthly RF for a SPY-proxy CAPM; never subtract RF twice."""
from __future__ import annotations
import io
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .data import sha256_file

URL = 'https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip'


def parse_french_rf(text: str) -> pd.Series:
    rows = []
    for line in text.splitlines():
        fields = [field.strip() for field in line.split(',')]
        if len(fields) == 5 and re.fullmatch(r'\d{6}', fields[0]):
            value = float(fields[4])
            if value <= -99:
                raise ValueError('Missing French RF sentinel encountered.')
            date = pd.Period(fields[0][:4] + '-' + fields[0][4:], freq='M').to_timestamp('M')
            rows.append((date, value / 100))
    if not rows:
        raise ValueError('No monthly RF observations found.')
    result = pd.Series(dict(rows), name='rf').sort_index()
    if len(result) != len(rows):
        raise ValueError('Duplicate RF months.')
    result.index.name = 'date'
    return result


def download_rf(output_dir: str | Path) -> pd.Series:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(URL, headers={'User-Agent': 'sector-momentum-research/0.1'})
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = response.read()
    archive_path = directory / 'french_factors.zip'
    archive_path.write_bytes(payload)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith('.csv')]
        if len(names) != 1:
            raise ValueError('Expected one French factor CSV.')
        rf = parse_french_rf(archive.read(names[0]).decode('utf-8-sig'))
    rf.loc['2000-01-31':'2025-12-31'].to_csv(directory / 'risk_free.csv', float_format='%.17g')
    metadata = {'source_url': URL, 'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
                'archive_sha256': sha256_file(archive_path),
                'risk_free_csv_sha256': sha256_file(directory / 'risk_free.csv'),
                'units': 'decimal monthly RF; source percentage divided by 100',
                'note': 'SPY total return is the market proxy. French Mkt-RF is not used. Historical supplier revisions, including CRSP format changes, remain possible.'}
    (directory / 'rf_manifest.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    return rf


def load_rf(path: str | Path, months: pd.DatetimeIndex) -> pd.Series:
    frame = pd.read_csv(path, parse_dates=['date'], float_precision='round_trip').set_index('date')
    if list(frame.columns) != ['rf'] or not frame.index.is_unique:
        raise ValueError('RF CSV must have unique date and rf columns.')
    rf = frame['rf'].reindex(months)
    if rf.isna().any() or not (abs(rf) < 1).all():
        raise ValueError('Complete, decimal monthly RF is required.')
    return rf
