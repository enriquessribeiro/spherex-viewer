"""Alvos do desafio: posição propagada pelo movimento próprio."""

from pathlib import Path

from astropy.coordinates import SkyCoord
import astropy.units as u
from pytest import approx

from pipeline.targets import Target, load_targets

J2000_MJD = 51544.5
J2016_MJD = 57388.5


def test_barnard_propagada_de_j2000_para_j2016_coincide_com_o_gaia_dr3():
    # Posição e movimento próprio do SIMBAD (época J2000).
    barnard = Target(
        id="barnard", name="Barnard's Star",
        ra=269.4520769586187, dec=4.693364966576667,
        pm_ra_masyr=-801.551, pm_dec_masyr=10362.394, ref_mjd=J2000_MJD,
    )

    ra, dec = barnard.position_at(J2016_MJD)

    # Fonte independente: Gaia DR3 source_id 4472832130942575872, ref_epoch 2016.0.
    gaia = SkyCoord(269.44850252544 * u.deg, 4.73942005111 * u.deg)
    assert SkyCoord(ra * u.deg, dec * u.deg).separation(gaia).arcsec < 0.5


def test_alvos_do_desafio_estao_todos_configurados():
    targets = load_targets(Path(__file__).parents[2] / "targets.yaml")

    assert {t.id for t in targets} == {"barnard", "epsindib", "wise0855", "rwaur", "rdra"}
    wise = next(t for t in targets if t.id == "wise0855")
    assert wise.pm_ra_masyr == approx(-8123.7)
