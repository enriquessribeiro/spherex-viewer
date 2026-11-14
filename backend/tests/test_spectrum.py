"""Espectro sob demanda (docs/06-testes.md §2.1: "fonte com espectro plantado").

Cada exposição do SPHEREx mede o alvo num comprimento de onda diferente (filtro de variação
linear): juntando as exposições, sai o espectro. Os valores esperados vêm do que plantamos.
"""

import math

import pytest

from pipeline.spectrum import APERTURE_PX, measure_spectrum
from tests.synthetic import PIXEL_SCALE_DEG, PSF_SIGMA_PX, SyntheticArchive, SyntheticExposure, SyntheticSource

RA0, DEC0 = 133.76, -7.24
SIZE_DEG = 0.15
PIXEL_SR = math.radians(PIXEL_SCALE_DEG) ** 2
# Brilho total de uma fonte gaussiana de pico F (MJy/sr) em µJy, dentro da abertura de raio R.
APERTURE_FRACTION = 1 - math.exp(-(APERTURE_PX**2) / (2 * PSF_SIGMA_PX**2))


def ujy(peak_mjy_sr: float) -> float:
    return peak_mjy_sr * 2 * math.pi * PSF_SIGMA_PX**2 * PIXEL_SR * 1e12 * APERTURE_FRACTION


def _medir(sources, exposures, position_at=None):
    archive = SyntheticArchive(sources=sources, exposures=exposures)
    alvo = sources[0]
    return measure_spectrum(archive, archive.query(RA0, DEC0), RA0, DEC0, SIZE_DEG,
                            position_at or alvo.position_at)


def test_recupera_a_linha_plantada_no_comprimento_de_onda_certo():
    """Anã fria de mentira: pico em 4,6 µm sobre um contínuo."""
    linha = lambda lam: 1 + 3 * math.exp(-((lam - 4.6) ** 2) / (2 * 0.05**2))
    fonte = SyntheticSource(ra=RA0, dec=DEC0, flux=50, spectrum=linha)
    expos = [SyntheticExposure(det="D6", mjd=60800 + i, wavelength_um=4.40 + 0.02 * i, offset_px=(i % 3, -(i % 2)))
             for i in range(25)]

    pontos = _medir([fonte], expos)

    assert len(pontos) == 25
    pico = max(pontos, key=lambda p: p.flux_ujy)
    assert pico.wavelength_um == pytest.approx(4.6, abs=0.02)  # ± 1 canal
    for p in pontos:
        assert p.flux_ujy == pytest.approx(ujy(50 * linha(p.wavelength_um)), rel=0.03)


def test_comprimento_de_onda_e_lido_no_pixel_do_alvo():
    """O λ muda ao longo do detector: tem de ser o do pixel onde o alvo caiu, não o do centro."""
    fonte = SyntheticSource(ra=RA0, dec=DEC0 + 10 * PIXEL_SCALE_DEG, flux=50)  # 10 px ao norte
    expo = SyntheticExposure(det="D6", mjd=60800, wavelength_um=4.6, wavelength_per_px=0.004)

    (p,) = _medir([fonte], [expo])

    assert p.wavelength_um == pytest.approx(4.6 + 0.004 * 10, abs=0.002)
    assert p.bandwidth_um == pytest.approx(0.03, abs=1e-4)


def test_alvo_que_se_move_e_medido_onde_esta_em_cada_exposicao():
    fonte = SyntheticSource(ra=RA0, dec=DEC0, flux=50, pm_north_arcsec_yr=6.15 * 4)  # 4 px/ano
    expos = [SyntheticExposure(det="D2", mjd=60800 + 90 * i, wavelength_um=1.3) for i in range(5)]  # até 4 px

    pontos = _medir([fonte], expos)

    assert [p.flux_ujy for p in pontos] == pytest.approx([ujy(50)] * 5, rel=0.03)


def test_fundo_local_e_descontado():
    fonte = SyntheticSource(ra=RA0, dec=DEC0, flux=50)
    (p,) = _medir([fonte], [SyntheticExposure(det="D6", mjd=60800, wavelength_um=4.6, bias=7.0)])
    assert p.flux_ujy == pytest.approx(ujy(50), rel=0.03)


def test_erro_vem_da_variancia_da_abertura_e_do_fundo():
    fonte = SyntheticSource(ra=RA0, dec=DEC0, flux=50)
    (p,) = _medir([fonte], [SyntheticExposure(det="D6", mjd=60800, wavelength_um=4.6, variance=4.0)])
    n_pix = sum(1 for dx in range(-3, 4) for dy in range(-3, 4) if dx * dx + dy * dy <= APERTURE_PX**2)
    minimo = math.sqrt(n_pix * 4.0) * PIXEL_SR * 1e12  # só a abertura; o fundo estimado soma um pouco
    assert minimo <= p.flux_err_ujy <= minimo * 1.3


def test_pixel_ruim_na_abertura_descarta_a_exposicao_e_suspeito_so_marca():
    fonte = SyntheticSource(ra=RA0, dec=DEC0, flux=50)
    quente = SyntheticExposure(det="D6", mjd=60800, wavelength_um=4.6, flagged=((1, 0, 10, 1e4),))  # HOT
    suspeito = SyntheticExposure(det="D6", mjd=60801, wavelength_um=4.62, flagged=((1, 0, 0, None),))  # TRANSIENT
    limpo = SyntheticExposure(det="D6", mjd=60802, wavelength_um=4.64)

    pontos = _medir([fonte], [quente, suspeito, limpo])

    assert [(p.exposure_id, p.flagged) for p in pontos] == [("syn0001_D6", True), ("syn0002_D6", False)]


def test_exposicao_sem_tabela_de_comprimento_de_onda_e_pulada():
    fonte = SyntheticSource(ra=RA0, dec=DEC0, flux=50)
    pontos = _medir([fonte], [SyntheticExposure(det="D6", mjd=60800),
                              SyntheticExposure(det="D6", mjd=60801, wavelength_um=4.6)])
    assert [p.exposure_id for p in pontos] == ["syn0001_D6"]


def test_alvo_fora_do_recorte_e_pulado():
    fonte = SyntheticSource(ra=RA0, dec=DEC0 + 1.0, flux=50)  # 1° ao norte: fora do recorte de 0,15°
    assert _medir([fonte], [SyntheticExposure(det="D6", mjd=60800, wavelength_um=4.6)]) == []


def test_estrela_vizinha_dentro_da_abertura_e_apontada():
    """WISE 0855 real: uma estrela a 9″ (1,45 px) domina o fluxo abaixo de ~3 µm."""
    from pipeline.field import build_field
    from pipeline.spectrum import neighbors_in_aperture

    alvo = SyntheticSource(ra=RA0, dec=DEC0, flux=20)
    vizinha = SyntheticSource(ra=RA0, dec=DEC0 + 1.45 * PIXEL_SCALE_DEG, flux=200)
    longe = SyntheticSource(ra=RA0, dec=DEC0 - 12 * PIXEL_SCALE_DEG, flux=200)
    expos = [SyntheticExposure(det="D1", mjd=60800 + i, variance=0.01, offset_px=(0.3 * i, 0)) for i in range(4)]
    campo = build_field(RA0, DEC0, 6, SyntheticArchive(sources=[alvo, vizinha, longe], exposures=expos))

    achadas = neighbors_in_aperture(campo, alvo.position_at)

    # Uma só vizinha, em D1. A distância é a verdadeira (8,9″) a menos de 1 px (6,15″): a 1,45 px a
    # vizinha se mistura com o alvo e o centroide é puxado um pouco para ele.
    assert [v["detector"] for v in achadas] == ["D1"]
    assert achadas[0]["distance_arcsec"] == pytest.approx(1.45 * 6.15, abs=6.15)


def test_alvo_sozinho_nao_tem_vizinhas():
    from pipeline.field import build_field
    from pipeline.spectrum import neighbors_in_aperture

    alvo = SyntheticSource(ra=RA0, dec=DEC0, flux=200)
    expos = [SyntheticExposure(det="D6", mjd=60800 + i, variance=0.01) for i in range(3)]
    campo = build_field(RA0, DEC0, 6, SyntheticArchive(sources=[alvo], exposures=expos))
    assert neighbors_in_aperture(campo, alvo.position_at) == []
