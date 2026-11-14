"""Gera a fixture de contrato do frontend com o gravador real do backend (campo sintético de 1′).

    cd backend && rm -rf ../frontend/tests/fixtures && uv run python scripts/gerar_fixture_frontend.py ../frontend/tests/fixtures

Regenerar sempre que o formato do field.json mudar.
"""
import sys
from datetime import UTC, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from pipeline.field import build_field
from pipeline.output import write_field
from pipeline.targets import Target
from tests.synthetic import SyntheticArchive, SyntheticExposure, SyntheticSource

ra, dec = 133.79513, -7.24515
arquivo = SyntheticArchive(
    sources=[SyntheticSource(ra=ra, dec=dec, pm_east_arcsec_yr=-12.3, ref_mjd=60800.0)],
    exposures=[SyntheticExposure(det="D6", mjd=60800.0), SyntheticExposure(det="D1", mjd=60800.1),
               SyntheticExposure(det="D6", mjd=60980.0)],
)
field = build_field(ra, dec, 1, arquivo)
alvo = Target(id="sintetico", name="Alvo sintético", ra=ra, dec=dec, pm_ra_masyr=-12300, ref_mjd=60800.0,
              default_detector="D6", description="Fixture gerada por scripts do backend")
path = write_field(field, Path(sys.argv[1]), target=alvo, generated_at=datetime(2026, 11, 14, tzinfo=UTC))
print(path)
