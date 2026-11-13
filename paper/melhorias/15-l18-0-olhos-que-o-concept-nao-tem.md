# 15 — L18-0: olhos que o concept não tem (default herdado do caso típico)

- Data: 2026-10-31
- Commit(s): main `1e387a79` (L18-0), `f8cb6c89` (Leva 18 completa; histórico linear). Detalhe em
  `castle_fight/artifacts/model-sheets/PIPELINE.md` §36 (`### 36.L18-0`).
- Problema do baseline atacado (§7 #): "parece o concept?" — o modelo recebe traços que o concept não desenha. Não é um problema de silhueta nem de
  spill: nenhum gate numérico das fichas 11–14 o mede.
- Hipótese: o pipeline tem um default "bípede ⇒ olhos" espalhado por prompt, brief e preflight; a lista de identidade textual de cada unidade já diz o
  que a cara tem, e basta condicionar os três pontos por essa lista (`face_kind` = eyes | lenses | none, default none). **Verdadeira**: hfoo 4 → 0
  peças de rosto sem reenvio; o default mudou (aprovado pelo utilizador).

## O que se viu (factos, `main 9a5a83fd`, antes da correcção)

| unidade | o que o concept diz da cara (`refs/<id>/parts.json` "identity") | o que o v16-r3 construiu |
|---|---|---|
| hfoo | nenhuma palavra de olho; painel frontal do `sheet.jpg` tem rosto liso cor de pele sob o capacete | `eye/round-2/dsl.json`: peças `eye_R`, `eye_L` (mat `eye` = `#2A2926`) e `nose` (`skin_dark`), role `face`; `spec.json` part 5 (head, lathe) com `decal: sheet` |
| n01X | "brass valve wheel as head, **no face or glass**" | `spec.json` part 4 (head, lathe, material `z3`) com `decal: sheet` |
| n005 / n00U / n017 / n02X | ver lista abaixo | `spec.json` tem `decal: sheet` na cabeça (parts 9, 12, 16, 7) |

As 6 unidades da bateria (hfoo, n005, n00U, n017, n01X, n02X) têm decal `sheet` na cabeça no v16-r3: 6/6, independentemente do que a lista diz.

Figura: `figuras/hfoo-15-olhos-concept-vs-modelo.png` — esquerda, cabeça do painel frontal do concept (`refs/hfoo/sheet.jpg`); direita, cabeça do
v16-r3 (`history/2026-10-30-l17-paint/hfoo.png`, caixa x 265–325 / y 15–75, NEAREST ×5). O concept não tem olhos; o modelo tem dois olhos e nariz.
Depois: `figuras/16-hfoo.png` (concept | v16-r3 | v18-qem | v18-cvt | Hive | wires) mostra a cabeça lisa dos v18.

### As 8 listas de identidade reais (`refs/<id>/parts.json`) e o `face_kind` que a L18-0 lhes dá

| unidade | identity | palavras de cara | `face_kind` (L18-0) |
|---|---|---|---|
| hfoo | round steel brodie helmet with wide brim · long trench pike with leaf blade held upright in right hand · olive tunic with flared shoulder pads and dark belt with steel buckle · blue-glass belt lantern hanging at right hip · dark field pack with bedroll on top and canteen below, on the back · soot-dark knee boots · no neck, square shoulders | nenhuma | **none** |
| n005 | hooded soot-black long coat · gas mask with two round red glass lenses · mask breathing hose curling down to chest · grey pressure tank on back with brass valve on top · blue-glass belt lantern hanging at left hip · cylindrical vaporiser held in left hand · heavy black boots and wide belt with pouch | "two round red glass lenses" | lenses |
| n00U | glowing green lantern mushroom cap on top of the dorsum · mossy green carapace plates draped over the body like a beetle shell · dark brown globular body · two small black dot eyes · pair of downward hooked fangs · short thick root-like brown legs with tapered tips | "two small black dot eyes" | eyes |
| n00H | thick corrugated hose body in an S curve · small conch-shell mask head with dark eye sockets · single glowing cyan lens on the head · membrane wings stretched on wire hoops, raised in a V · cyan valve with bow-like flaps at the tail tip · ribbed hose segments along the belly | "dark eye sockets", "single glowing cyan lens" | eyes |
| n01X | brass valve wheel as head, no face or glass · large round brass valve wheel on the chest · glowing yellow furnace slit below the chest · oversized boxy brass shoulder pads · huge blocky brass piston fists on grey forearm cylinders · cast-iron grey body with brass trim · stubby brass-cuffed legs with flat boxy feet | "no face or glass" | **none** |
| n02X | upright iron drill-pipe club with brass disc ring held in right fist · grey tank-car shoulder plate on left shoulder with crossed-out X mark · round iron goggles over bald head · canvas respirator mask with jutting tusks · huge round drum belly with diagonal leather strap · grey bolt belt with hanging orange fuse cloth · dark knee-high boots under canvas trousers | "round iron goggles", "respirator mask with jutting tusks" | lenses |
| n017 | orange broken sled harness band looped over shoulders and chest · broken knot hanging at the front of the chest · bared frost-caked white teeth with icicle drips · grey-blue back over pale icy-blue belly and legs · big paws, long low body, level tail · tow rope dragging from the rear paw along the ground · tall pointed ears and a heavy brow | "heavy brow" (conta como olho: o concept desenha duas fendas escuras sob a sobrancelha), "bared teeth" | eyes |
| n010 | two tall pale-blue membrane wings raised in a V · riveted grey collar with three rivets · small orange service lamp hanging under the collar · dark crude weep running down the pale chest · ribbed exhaust vent grille on the flank with a small back stack · long low neck and snout stretched forward · dark slate body with pale blue underbelly | nenhuma | **none** |

A resposta já estava nos dados: 3/8 listas não têm palavra de cara (hfoo, n010) ou negam-na (n01X); 2/8 pedem lentes, não olhos (n005, n02X).
Regra de palavras: `eye*`, `brow`/`brows` como palavra inteira ("brown" é cor) → eyes; `lens*`, `goggle*`, `visor*` sem palavra de olho → lenses;
"no face" / "no eyes" / "faceless", nenhuma palavra de rosto, ou **sem lista** → none.

## Três causas em código (todas `main 9a5a83fd`)

| # | ficheiro | linha | o que faz | porque é default errado |
|---|---|---|---|---|
| a | `artifacts/model-sheets/prompts/eye.md` | 36 | regra "2. Face: a face must be legible with GEOMETRIC pieces… eyes as small dark/bright 6-side tubes or balls on the front of the head" | incondicional: vale para o capacete liso do hfoo e para a roda de válvula do n01X |
| b | `tools/blender/spec_pipeline.py` | ~125 | brief `PAINTED FEATURES: eyes are painted, never modelled. Give the part … opts {"decal": "sheet"}: the DEFAULT` | decal `sheet` é o default; o modelo manda dois olhos até numa "valve wheel" |
| b' | `tools/blender/spec_pipeline.py` | ~408–418 | `identity_text`: item `kind == "eyes"` → "a face decal on the head (decal + decal_color, two points, not a slit)" | o decal torna-se obrigatório assim que o item existe |
| c | `tools/blender/preflight.py` | 184, 197 | `EYE_WORDS = ("eye", "lens", "visor")`; `identity_items` põe `{"name": "eyes", "kind": "eyes"}` em **todo bípede sem lista** de identidade | o caso sem lista herda o default do caso típico |
| c' | `tools/blender/build_unit.py` | ~1791 | `obj["decal"] = "face" if opts["decal"] == "sheet" and FACE is None` | decal `sheet` sem imagem recortada cai em `face` = dois olhos + boca desenhados |

Encadeamento: (c) cria o item "eyes" → (b') o brief exige decal → (b) o autor escreve `decal: sheet` → (c') sem recorte vira cara genérica; o estágio
com olho (a) acrescenta por cima `eye_R`/`eye_L`/`nose` como primitivas. Quatro camadas, todas a concordar entre si, nenhuma a olhar para o concept.

## Mudança (L18-0, `1e387a79`)

- `preflight.face_kind(identity_texts) → "eyes" | "lenses" | "none"`, default `none` (lista ausente, lista sem palavra de cara, ou frase "no face").
  `identity_items` só emite o item "eyes" quando `face_kind != "none"` (o bípede sem lista deixa de herdar olhos). Sem flag nova: determinístico a
  partir da lista; mudar a lista muda o rosto.
- `spec_pipeline`: `FACE_EYES` / `FACE_NONE` no lugar de PAINTED FEATURES + HOODS; com `none` o brief diz "NO eyes or face: no decal, no eye parts" e
  `validate` (`check_decals`) **rejeita qualquer parte com `decal`**; `identity_text` diz "as drawn".
- `eye.md`: regra 2 → `{{face_rule}}` (`FACE_RULES`: eyes = texto da L15-5; lenses = "build the lenses/goggles/visor, do NOT add eyes"; none = "BLANK
  face"). `eye_lib.validate(..., face=)` com `none` **recusa antes do Blender** toda a peça cujo nome diga eye/pupil/iris/nose/mouth/teeth/fang/tusk/brow.
  Crítico (`eye-critic.md` `{{face_note}}`): em `none` qualquer peça de rosto é defeito de severidade 2.
- `build_unit` ~1791 (fallback `face`) fica igual: nada chega com decal.
- Extra pedido pelo utilizador: `eye_stage.tick` acumula wall-clock por estágio → `<run>/timing.json` (usado em `01-tese.md` "Juiz vs produção").
- Testes: `test_face_kind_of_the_eight_sheets` (8 listas + None, [], "brown", "brow"), `test_a_blank_face_takes_no_decal`, validate em `none` recusa
  `eye_L` / `Nose tip`; suite blender 930 OK, ruff 0 achados novos.

## Protocolo

- Unidades: as 6 da bateria (hfoo, n005, n00U, n017, n01X, n02X); n00H e n010 só pelo teste unitário das listas.
- Spec author / modelo de imagem: `session:opus`, `--eye on --eye-from v15-r1 --eye-rounds 3 --eye-stop model`, mesmo protocolo do v16-r3
  (que era um prefixo da trajectória `v16-r9` com `--eye-stop never`); uma unidade de cada vez, `nice -n 10`.
- Runs por unidade: 1 (`v18-r0`). Peças de rosto = `role: face` no `dsl.json` final.
- Métrica principal: contagem determinística de peças de rosto contra o `face_kind`; juiz pareado 4 votos com troca (B = v18-r0, A = v16-r3,
  `runs/draft/<id>/v18-r0/pairwise4-v16-r3.json`) para confirmar que a forma não piora.

## Resultado

| unidade | `face_kind` | peças de rosto v16-r3 → v18-r0 | parts k/n v16-r3 → v18-r0 | IoU f/l/b v18-r0 | tris / peças | juiz sheet / artista / wc3 / forma (B = v18-r0) | veredito |
|---|---|---|---|---|---|---|---|
| hfoo | **none** | 4 (`face`, `nose`, `eye_R`, `eye_L`) → **0** | 14/25 → 18/25 | .78/.71/.79 | 696 / 38 | **B 4-0 / B 3-1 / B 3-1 / B 4-0** | atendido |
| n01X | **none** | 0 → **0** (roda de válvula, sem decal) | 29/30 → 26/30 | .91/.90/.91 | 700 / 45 | **B 3-1 / B 4-0 / B 4-0 / B 4-0** | atendido |
| n005 | lenses | 5 → 7 (máscara, 2 lentes, focinho, mangueiras) | 28/28 → 28/28 | .86/.89/.87 | 700 / 45 | A 4-0 nos 4 | mantém lentes; forma perde |
| n00U | eyes | 6 → 6 (2 olhos, 4 peças de presa) | 17/21 → 16/21 | .84/.87/.82 | 684 / 33 | A 4-0 nos 4 | mantém olhos; forma perde |
| n02X | lenses | 7 → 9 (respirador, filtros, 2 presas, aro, 2 armações, 2 lentes) | 28/39 → 26/39 | .90/.87/.89 | 700 / 41 | empate 2-2 nos 4 (viés de posição) | mantém máscara |
| n017 | eyes | 9 → 10 (máscara, focinho, nariz, boca, dentes, 2 presas, 2 olhos) | 18/19 → 17/19 | .88/.81/.81 | 680 / 48 | empate / **B 4-0 / B 3-1 / B 4-0** | mantém olhos |

Agregado: aceite (1) hfoo e n01X sem peça de rosto e sem decal — **atendido** (4 → 0, 0 → 0); (2) n005 / n00U / n02X mantêm lentes / olhos / máscara —
**atendido** (7 / 6 / 9); (3) forma não pior que v16-r3 — **4/6** (hfoo B, n01X B, n02X empate, n017 B); n005 e n00U perdem 0-4. Nenhum reenvio por
peça de rosto (único reenvio: 704 tris no hfoo). Tempo: 627 s hfoo, mediana das 6 **691 s**, artista 638 s = 92 %.

## O que piorou / limitações

- n005 e n00U perdem forma 0-4 para o v16-r3, com parts k/n igual (28/28) ou −1 (16/21). Causa **não medida**: a variância de amostrar outro run do artista
  (ficha 13, L16-1: "passeio aleatório em torno de um patamar") é hipótese. O prompt só ficou igual no n00U; o n005 é `lenses` e recebeu regra nova, logo a regra não está excluída.
  n = 1 trajectória por unidade continua a ser o limite para separar regra de ruído.
- Nenhum gate das levas 11–17 detectou o erro original: IoU, spill, bare, `parts k/n` e `mesh_lint` não vêem o rosto (uma caixa de 0.05 m não move a
  silhueta). O juiz de visão (4 e 8 votos, fichas 12–14) também não penalizou: olhos num soldado parecem plausíveis. Só a leitura da identidade
  textual apanha — e agora o juiz, com o par certo, prefere a cara lisa do hfoo 4-0 em sheet.
- `face_kind` depende da lista de identidade (8/8 das refs medidas têm); unidade nova sem lista fica `none` — default seguro, mas uma criatura com olhos
  e sem lista perde-os. Taxa de falso-`none` nas 223 unidades: a preencher quando a bateria correr em largura.
- "heavy brow" → eyes foi decisão humana lida no sheet do n017, não regra geral; "brown" ≠ "brow" está testado.

## Leitura para o paper

Classe de erro: **default herdado do caso típico**. O caso comum (bípede com olhos) foi escrito como regra incondicional em quatro sítios
(prompt, brief, checklist, fallback do builder), e as quatro concordam entre si, por isso nenhuma verificação interna as apanha. Em busca em
largura one-shot (`01-tese.md`), um default errado não custa uma unidade: replica em todas as 223 unidades da temática — a mesma propriedade que
torna a largura eficiente para corrigir torna-a eficiente para espalhar o erro. A detecção veio de ler o concept e a lista de identidade à mão, não
de um gate; a correcção é ler a lista em código, e custou zero chamadas extra.

## Conclusão (1 frase para o paper)

O pipeline deu olhos a 6/6 unidades da bateria porque "bípede ⇒ olhos" estava escrito como default em quatro camadas concordantes, enquanto a lista
de identidade de cada concept já dizia o contrário em 3/8 (hfoo, n01X, n010) — nenhum gate numérico nem o juiz o viu; ler a lista em código
(`face_kind`, L18-0) tirou as 4 peças de rosto do hfoo sem reenvio e o juiz passou a preferir a cara lisa 4-0 em sheet, com n005/n00U a perder 0-4
por causa não medida, a lembrar que n = 1 não separa regra de sorteio.
