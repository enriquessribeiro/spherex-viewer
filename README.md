# Dados pré-processados (snapshot)

Dados dos alvos do SPHEREx Viewer gerados **localmente** por `pipeline.build_static` em 14/11/2026
(16:54 UTC), a partir dos recortes do IRSA em cache, e validados por `pytest -m science`
(16 testes) no commit `7b8bdd7` da `main`.

Existe porque o serviço TAP do IRSA estava fora do ar no momento da primeira publicação.
É usado só pelo workflow manual `publish-snapshot.yml`; o workflow normal (`update-data.yml`)
gera os dados de novo e substitui esta publicação quando roda com sucesso.
