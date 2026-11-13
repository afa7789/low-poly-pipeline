# 05 — Avaliação humana vs juiz LLM (2026-11-07)

Responde ao que `04-resultados-e-descobertas.md` §3–§6 e `REVIEW-2026-11-07.md` §4/§6.2 apontam como o buraco principal: o pipeline corre
em largura (165 modelos) mas ninguém mediu se os modelos **parecem** bons. Todo o "juiz" das fichas 11–19 é um LLM a avaliar o que outro
LLM fez, e `parts k/n` / IoU são proxies escolhidos pelo próprio pipeline. Esta secção monta os dois testes pedidos pelo autor — um de
computador e um humano — **na mesma amostra, com as mesmas imagens e as mesmas três perguntas**, para que se possa medir a concordância
humano↔juiz e humano↔métricas automáticas. O juiz já correu (resultados abaixo); o teste humano está pronto a correr no browser.

## 1. Protocolo

**Amostra** (`castle_fight/artifacts/model-sheets/eval/sample-30.json`, semente 7, `eval_judge.py --make-sample`): 30 unidades do
`results-roster-v6.csv`, estratificadas — 15 bípedes (uma por raça em round-robin, 14 raças, Pandaren 2) + 15 não-bípedes (primeiro uma de
cada família de rig pior: ray, wyrm, spider_high, drake, harpy, quadruped, naga, vehicle; as 7 restantes ao acaso). Só unidades com print
WC3 original e sheet aprovado (as 5 pseudo-unidades hmtm-* e as 8 sem print ficam fora da urna).

**Estímulos por unidade**, iguais nos dois testes:

| o quê | ficheiro |
|---|---|
| (a) o nosso modelo: render final frente / esquerda / câmara RTS | `runs/draft/<id>/<run>/views-final/model-{front,left,wc3}.png` (`render_unit.py`, EEVEE sem luz, 512 px) |
| (b) o concept aprovado, painel da frente, de-inked | `eval/stimuli/<id>/concept-front.png` (de `refs/<id>/sheet.jpg`, `split_sheet` + `deink_image`) |
| (c) o original WC3: print + ícone | `artifacts/reference/hive/renders/<id>.png`, `icons/<id>.png` (ícone em falta em 1: n03U) |

**Três perguntas, escala 1–5** (1 = nada, 3 = em parte, 5 = claramente):

- **Q1** Parece a unidade de WC3? (modelo vs print/ícone)
- **Q2** É fiel ao concept? (modelo vs painel da frente do concept)
- **Q3** Usaria no jogo como está (alfa)?

**Teste humano** (`artifacts/model-sheets/viewer/eval.html`, servido por `serve.py` em `/eval`): uma unidade de cada vez, ordem aleatória
por sessão (semente = carimbo da sessão, guardado em `localStorage` para retomar), progresso N/30, teclas 1–5 respondem à pergunta activa e
passam à seguinte, Enter guarda; nota livre opcional. Cada resposta vai por `POST /api/eval` para `eval/human-<sessão>.json` (reescrita
atómica, uma entrada por unidade, repetição substitui); `GET /api/eval/export` junta todas as sessões. A página **nunca** mostra a nota do
juiz nem IoU/parts. Correr:

```bash
cd castle_fight && python3 artifacts/model-sheets/viewer/serve.py      # abre http://127.0.0.1:8899/ ; ir a http://127.0.0.1:8899/eval
```

**Teste de computador** (`tools/blender/eval_judge.py --sample eval/sample-30.json --model session:sonnet --out eval/computer-<ts>.json`):
1 chamada `claude -p` por unidade (`spec_pipeline.ask_session`, mesma via de `review_pair.py`; Sonnet para poupar quota), as 6 imagens acima
em ordem fixa, o mesmo texto das três perguntas, resposta forçada por JSON schema `{q1, q2, q3: int 1–5, why: str}`. Os números automáticos
da unidade (`glb_parts_share`, `glb_front/left/rts` IoU do `results-roster-v6.csv`) seguem no mesmo ficheiro.

**Relatório** (`tools/blender/eval_report.py --computer eval/computer-<ts>.json --human eval/human-<ts>.json`): por pergunta, média humano
(média por unidade sobre avaliadores), média juiz, Spearman ρ e Kendall τ-b humano↔juiz, humano↔IoU front/left/rts e humano↔parts, o
mesmo para o juiz, e bípedes vs não-bípedes; reescreve o bloco entre os marcadores `EVAL-REPORT` desta secção. Sem `--human`, preenche só o
juiz (estado actual). `python3.14` tem scipy e imprime p-valores; `python3` imprime só ρ/τ.

## 2. Amostra

| grupo | id (nome, raça, rig, run) |
|---|---|
| bípedes (15) | n03E Sagepaw Monk (Pandaren), n02M Goblin Rocketeer (Mech), hfoo Footman (Human), n013 Ancient Wandigoo (Northern), e00C Ancient Keeper (Nature, v6e), h034 Elemental Of Earth (Elemental, v6e), n01I Corrupted Ent (Corrupted), u009 Mighty Necromancer (Undead), n00V Troll Berserker (Orc), h00U Bloodthirster (Elf), n02V Quillboar (Desert, v6e), e00B Avenging Spirit (Nightelf, v6e), n004 Suumpmolk (Naga), e00E-b Twins: Weeper (Chaos), n03T Sagepaw Soulkeeper (Pandaren) |
| não-bípedes (15) | n03U Winged Riptide Serpent (Naga, ray), n00H Winged Serpent (Naga, wyrm), n01N Giant Spider (Nature, spider_high), e000 Faerie Dragon (Nightelf, drake, v6e), n02W Harpy (Desert, harpy), n017 Frost Wolf (Northern, quadruped), n00S Naga Siren (Naga, naga, v6e), h099 Assault Tank (Mech, vehicle), n02B Ancient Bear (Nature, quadruped), u000 Frost Wyrm (Undead, bird, v6e), z000 Quill Demon (Chaos, quadruped), n01E Infernal Tank (Corrupted, sled), h03C Paladin (Human, mounted), h06S Heavy Tank (Mech, tracked), n034 Harpies' Matriarch (Desert, harpy, v6e) |

## 3. Resultados

Bloco escrito por `eval_report.py` (juiz: `computer-20261107-085131.json`, Sonnet; humano: por preencher — as colunas "humano" ficam "—"
até o autor correr o teste e o relatório com `--human`).

<!-- EVAL-REPORT:begin -->
Unidades com nota do juiz: 30; avaliadores humanos (sessões): 0; unidades com nota humana: 0.

| pergunta | média humano | média juiz | humano↔juiz | humano↔IoU front | humano↔IoU left | humano↔parts | juiz↔IoU front | juiz↔IoU left | juiz↔parts |
|---|---|---|---|---|---|---|---|---|---|
| Q1 parece WC3 | — | 2.10 (n 30) | — | — | — | — | ρ -0.40 / τ -0.32 (p 0.03) | ρ -0.17 / τ -0.14 (p 0.37) | ρ -0.26 / τ -0.20 (p 0.17) |
| Q2 fiel ao concept | — | 3.13 (n 30) | — | — | — | — | ρ 0.28 / τ 0.24 (p 0.13) | ρ 0.05 / τ 0.04 (p 0.80) | ρ 0.17 / τ 0.14 (p 0.37) |
| Q3 usaria na alfa | — | 2.27 (n 30) | — | — | — | — | ρ 0.10 / τ 0.09 (p 0.59) | ρ 0.11 / τ 0.09 (p 0.58) | ρ 0.24 / τ 0.19 (p 0.21) |

IoU rts (n menor: unidades sem painel rts): juiz q1 ρ -0.16 / τ -0.13 (p 0.53), q2 ρ 0.25 / τ 0.20 (p 0.32), q3 ρ 0.03 / τ 0.01 (p 0.92); humano q1 —, q2 —, q3 —.

| grupo | n | humano Q1 | humano Q2 | humano Q3 | juiz Q1 | juiz Q2 | juiz Q3 | IoU front | parts |
|---|---|---|---|---|---|---|---|---|---|
| bípedes | 15 | — | — | — | 1.93 | 3.20 | 2.33 | 0.77 | 0.80 |
| não-bípedes | 15 | — | — | — | 2.27 | 3.07 | 2.20 | 0.60 | 0.60 |

Por rig (juiz Q1/Q2/Q3, humano Q1/Q2/Q3 quando há):

| rig | n | juiz Q1 | juiz Q2 | juiz Q3 | humano Q1 | humano Q2 | humano Q3 |
|---|---|---|---|---|---|---|---|
| biped | 15 | 1.9 | 3.2 | 2.3 | — | — | — |
| quadruped | 3 | 2.3 | 3.0 | 2.3 | — | — | — |
| harpy | 2 | 2.0 | 3.5 | 2.5 | — | — | — |
| bird | 1 | 2.0 | 2.0 | 2.0 | — | — | — |
| drake | 1 | 2.0 | 2.0 | 1.0 | — | — | — |
| mounted | 1 | 2.0 | 3.0 | 2.0 | — | — | — |
| naga | 1 | 2.0 | 3.0 | 2.0 | — | — | — |
| ray | 1 | 3.0 | 3.0 | 2.0 | — | — | — |
| sled | 1 | 2.0 | 3.0 | 2.0 | — | — | — |
| spider_high | 1 | 3.0 | 4.0 | 3.0 | — | — | — |
| tracked | 1 | 2.0 | 4.0 | 3.0 | — | — | — |
| vehicle | 1 | 2.0 | 3.0 | 2.0 | — | — | — |
| wyrm | 1 | 3.0 | 3.0 | 2.0 | — | — | — |

Por unidade (juiz; humano quando há):

| id | nome | rig | juiz Q1 | Q2 | Q3 | humano Q1 | Q2 | Q3 | IoU front | parts | porquê (juiz) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| e000 | Faerie Dragon | drake | 2 | 2 | 1 | — | — | — | 0.66 | 0.79 | The model has a pink, orange and purple wing palette and a teal body with green legs, so it loosely echoes the concept and the Warcraft III faerie dragon. The wings are flat, blocky pentagon slabs with no bat-wing shape, the head and eyes are barely readable, and the tail curl and wing props are missing. The RTS camera view is a confusing jumble of slabs, so it isn't usable in an alpha build. |
| e00B | Avenging Spirit | biped | 3 | 4 | 3 | — | — | — | 0.59 | 0.87 | The model follows the concept closely: teal helmet with a blue gem, pointed ears, spiked shoulder pads, purple skin, a grey tabard and a dark green cape. It reads as a night-elf huntress in the WC3 style. The weaknesses are thin stick-like limbs, noisy textures, floating blade shards, no wisps and a stiff, tall build. That makes it usable as an alpha placeholder but not polished. |
| e00C | Ancient Keeper | biped | 1 | 3 | 2 | — | — | — | 0.74 | 0.97 | The WC3 unit is a purple night-elf stag-rider (a druid of the claw type) with antlers, and the model is a brown, green-moss treant. That matches neither its colours nor its shape. It follows the concept's antlers, green chest glow, mossy pads and floating lanterns, but the model is crude and thin: the antlers are weak, the legs are stubby, and the left view is very flat. The floating lantern and stick parts are disconnected and look like errors, so it would need rework before use. |
| e00E-b | Twins: Weeper | biped | 1 | 3 | 2 | — | — | — | 0.80 | 0.79 | The model is a black-clad figure with a pale mask and a wheel prop, which doesn't resemble the WC3 unit (a gnome-like figure with a red vest and brown trousers). It follows the concept's overall silhouette and wheel prop, but the face is much simpler, the colours are flatter and the proportions are slimmer. It would need rework before use, though it reads clearly as a unit. |
| h00U | Bloodthirster | biped | 1 | 3 | 2 | — | — | — | 0.76 | 0.72 | The model doesn't resemble the Warcraft III unit. That unit is a gold and black armoured elf with a large shield and blades, and the model is a teal-coated goblin with a staff. It follows the concept's overall layout (ears, sash, staff, arm bracer, yellow boots), but the head is a flat yellow blob with no goggle eye, the tunic is a plain slab, and the proportions are flat and thin. It would read as a rough placeholder in the RTS camera. |
| h034 | Elemental Of Earth | biped | 2 | 3 | 2 | — | — | — | 0.84 | 0.86 | The model keeps the concept's hulking silhouette, with the dark arms, grey torso and legs, the spike on the back and the orange drill on the shoulder. But it is squat and hunched, the head is tiny and lost in the shoulders, the orange chest crystal is missing, and the claws are barely visible. It reads as a generic brown brute rather than the craggy, glowing WC3 rock golem, and the muddy texture and odd proportions fall short of alpha quality. |
| h03C | Paladin | mounted | 2 | 3 | 2 | — | — | — | 0.79 | 0.84 | The model reads as a red-clad rider on an orange horse with a banner and a cleaver, so it follows the concept's basic idea. The WC3 reference is a gold-armoured knight, and the reference render is a garbled texture sheet, so the match to WC3 is weak. Against the concept, the palette and props are roughly right. The shoulder pads are missing, the horse head is a blocky grey wedge, and the textures are smeared, so it is too messy to use as it is, even for an alpha. |
| h06S | Heavy Tank | tracked | 2 | 4 | 3 | — | — | — | 0.87 | 1.00 | The model follows the concept sheet closely: a face front, blue turret, two exhaust stacks, orange side pods, grey wheels and black spikes. It only loosely resembles the Warcraft III steam tank, which is a gold and wood armoured vehicle with a cannon and a beast-head ram. The colours are blotchy, the face is lower quality than the concept's, and the red wheel hubs with gold crosses don't match the reference. It would work as an alpha placeholder, but it isn't polished. |
| h099 | Assault Tank | vehicle | 2 | 3 | 2 | — | — | — | 0.81 | 0.88 | The model has the right ingredients: a yellow and grey body, a front plow blade, two black exhaust pipes, orange side pods and chunky wheels. The pieces look disconnected, though. The blade is a flat slab, and in the left view it floats detached from the body. The body is boxy and the turret is a lump, so it doesn't read as the ornate WC3 siege engine. It follows the concept's layout loosely, but the wheels are too big and the shapes are crude. The floating blade and rough read mean it would need fixes before going into an alpha build. |
| hfoo | Footman | biped | 1 | 4 | 2 | — | — | — | 0.82 | 0.46 | The Warcraft III footman is a knight in silver and black plate armour with a sword and shield. The model is a grey-green WWI-style rifleman, so it doesn't match the reference at all. It does follow the concept sheet closely (helmet, blue collar, crossed bandoleers, rifle), though the head is muddy, the arms are shapeless and the textures are noisy, so it isn't ready for an alpha build. |
| n004 | Suumpmolk | biped | 3 | 4 | 3 | — | — | — | 0.73 | 0.58 | The model keeps the concept's teal body, orange frill, glowing cyan eyes, yellow-green belly and back spikes, and it reads as a green dinosaur-like beast like the WC3 unit. It is thin and flat from the front, the claws and teeth are barely there, and the texture is noisy. That makes it usable as an alpha placeholder, but it is not polished. |
| n00H | Winged Serpent | wyrm | 3 | 3 | 2 | — | — | — | 0.28 | 0.15 | The colours and overall layout match the winged blue, green and yellow flyer with a spiny tail. The wings are thin and flat, nearly invisible from the front. The head is a blob with no antennae or menacing face, and the body is small and crude. It reads as a flying creature from the game camera but is weak as a unit. |
| n00S | Naga Siren | naga | 2 | 3 | 2 | — | — | — | 0.67 | 0.44 | The colours match the concept (blue torso, orange hair and fins, cream belly, purple coil). The shapes are messy, though. The snake-hair heads and the face are lost, the arms are thin slivers, and the tail is a lumpy blob. It reads only loosely as a naga, and the geometry looks too broken for an alpha build. |
| n00V | Troll Berserker | biped | 2 | 3 | 2 | — | — | — | 0.78 | 0.73 | The model has the purple muscular biped with the red mohawk, dark bracers and loincloth, but it is too thin and slim, with no bulky shoulders. Its head is small and unreadable, the cleavers are thin sticks, and the texture is smeared and noisy. It matches the concept's colour layout, but the heavy proportions, the X-straps and the chunky cleavers are lost, so it is too rough to use in an alpha build. |
| n013 | Ancient Wandigoo | biped | 2 | 3 | 2 | — | — | — | 0.75 | 0.92 | The model follows the concept sheet's broad palette and silhouette: a white-furred gorilla with purple hands, feet and face, an orange canister and a grey spike. The concept's menacing face, tusks and curled tail are mostly lost: the face is a small blob and the tail is a thin grey stick. The WC3 reference render is a red/white horned, spiky creature and the icon is a purple-faced white-furred beast with big tusks, so the match to it is only loose. The body is blocky and the head is tiny, so the model reads as a generic yeti and would need work before an alpha build. |
| n017 | Frost Wolf | quadruped | 2 | 3 | 2 | — | — | — | 0.18 | 0.31 | The model is a white wolf with a gold sash and dark lower legs, which matches the concept's colours and props. But the legs are very tall and spindly, the body is thin and not bulky or hunched like the stocky WC3 wolf, and the paws float detached from the legs. The snarling face is missing, and the rope on the ground looks odd. It would need rework before an alpha build. |
| n01E | Infernal Tank | sled | 2 | 3 | 2 | — | — | — | 0.79 | 0.74 | The model keeps the black, gold and bone-white palette, the green glowing face and the spikes and wheels, so it reads loosely as the spiked siege engine. The silhouette is muddled, though. The front view shows a flat triangular face plate, the bone tusks are flat shards, and the cannon and wheel structure is hard to read from the game camera. Compared with the concept it is blurry and blocky, and it lacks the round cannon-muzzle ring and the curved claws. It would need rework before going into an alpha build. |
| n01I | Corrupted Ent | biped | 1 | 3 | 2 | — | — | — | 0.80 | 0.88 | The model follows the concept's olive stump-headed brute with a green eye, a dark claw arm and a club on its back. But the concept's hollow stump top, collar ring, chest axe emblem and clear claw are lost or muddy. It looks nothing like the WC3 unit, which is a purple, crystal-spiked, fanged tree creature. The blocky shape and blurry face make it weak even for an alpha build. |
| n01N | Giant Spider | spider_high | 3 | 4 | 3 | — | — | — | 0.50 | 0.25 | The model reads as a spider with a green face, red eyes, pale fangs, purple legs and a dark abdomen. That matches the concept sheet's colours and layout, but the legs are stiff straight sticks and there are only four red eyes. It resembles the WC3 spider (green head, large eyes, furry fangs) only loosely, and the WC3 render's purple and gold armoured legs are missing. It's usable as an alpha placeholder, but the legs and proportions are crude. |
| n02B | Ancient Bear | quadruped | 2 | 3 | 2 | — | — | — | 0.79 | 0.91 | The model keeps the concept's palette (orange fur, red antlers and crest, green mane, cream muzzle), so it reads as an antlered bear. It is a crude, faceted blob with no snarling face or visible claws, and it is a quadruped, where the concept stands upright on its front paws. It barely resembles the WC3 icon's bear with red mohawk, and the purple humanoid in the WC3 render not at all, so I wouldn't ship it as is. |
| n02M | Goblin Rocketeer | biped | 3 | 4 | 3 | — | — | — | 0.85 | 0.93 | The model keeps the main features of the concept: green goblin, grey helmet, red shoulder pads and chest, brown gloves and apron, and a rocket tube on the back. It reads as a goblin sapper, close to the WC3 unit's red body with a big tube. The face is muddy, there is no clear gas mask or goggles, and the textures are noisy. The tube's gold cap looks like a hat from the front. It's usable for an alpha, but only just. |
| n02V | Quillboar | biped | 2 | 3 | 2 | — | — | — | 0.78 | 0.65 | The model reads as a boar-like quadruped with a grey mane ridge and red patches, but it lacks the tusks, the snout detail and the spiky bristle mane of the WC3 razormane boar. It also has a flat, boxy head and messy texture artifacts. It matches the concept's colours and general layout, but the face, ears and scars are lost, so it needs rework before alpha. |
| n02W | Harpy | harpy | 2 | 4 | 3 | — | — | — | 0.79 | 0.97 | The model follows the concept sheet closely: a brown bird-humanoid with a spiky crest, a grey beak-face, two-tone wings with claws, and yellow talons. It is a bit stiff and flat, with simple wings, but it reads clearly. It looks little like the Warcraft III harpy, which is a pale female humanoid with green and yellow feathers, so the concept already departed from the original. It is usable as an alpha placeholder, though it is rough. |
| n034 | Harpies' Matriarch | harpy | 2 | 3 | 2 | — | — | — | 0.75 | 0.82 | The model follows the concept's palette (maroon body, red and yellow wings, gold crown with a purple gem, yellow talons) and reads as a feathered bird-person. But the WC3 harpy is a winged woman with an orange feather crest, and the model has a bird-like shape and a grey beaked face. Compared with the concept, the wings are thin and ragged, the crown is sparse, and the head is blocky. The muddy textures and stubby, awkward form need rework before alpha. |
| n03E | Sagepaw Monk | biped | 3 | 3 | 3 | — | — | — | 0.76 | 0.83 | The model keeps the pandaren monk's main features: a straw hat, a red collar, a grey robe with gold trim, and a red staff with a disc head. It reads as the unit at a glance. The face is a messy skull-like white blob with no clear panda eyes or muzzle, and the body is a slim, straight column. The concept shows a clean, readable face and a wider, sturdier build. The textures are patchy and smeared, so it is usable for an alpha build but would need cleanup. |
| n03T | Sagepaw Soulkeeper | biped | 2 | 3 | 3 | — | — | — | 0.81 | 0.92 | The model keeps the concept's main read: a panda in a straw hat and grey robe, with a red-handled mace and a stove on its front. It is a blocky, muddy version of the concept. The face is weak, the red sash is missing, and the stove reads as a box. In the RTS view the head looks orange and the red backpack is oversized. It only loosely matches the WC3 pandaren, which is a grey-furred brawler in an open jacket with a red collar. It is usable as an alpha placeholder but not polished. |
| n03U | Winged Riptide Serpent | ray | 3 | 3 | 2 | — | — | — | 0.46 | 0.08 | The model has the right colours and features: a blue ray body, lime horns, a red brow band, a tan jaw with tusks, and a tailed stinger. It reads as a manta ray. Its head is small, its wings are flat slabs, and the front view is very thin, so the concept's expressive face is mostly lost. The tail and fork are present but look awkward, and the model would be hard to read at game-camera distance. |
| u000 | Frost Wyrm | bird | 2 | 2 | 2 | — | — | — | 0.34 | 0.30 | The palette matches (bone, purple, black spikes, cyan face), but the build is wrong. It has stick limbs, flat panel wings with square cyan windows and a thin body, with no skull-like head, ribcage or bat-wing membrane. It follows the concept's colours and spiky crest, but the wings are blocky planes rather than bony-fingered membranes, so it isn't good enough for an alpha. |
| u009 | Mighty Necromancer | biped | 2 | 2 | 2 | — | — | — | 0.76 | 0.86 | The model keeps the concept's palette (brown robe, purple vest, green crystal staff and hand flames, horns), but the skeleton face, ribs, belt and flame effects are gone. The result is a flat, blocky robed figure with a blank face and no clear silhouette. It has little in common with the bearded, horned Warcraft III unit shown in the icon, and the RTS-camera view is a muddy brown blob, so it needs rework before an alpha. |
| z000 | Quill Demon | quadruped | 3 | 3 | 3 | — | — | — | 0.39 | 0.47 | The model keeps the concept's main features: a red, quadruped, horned body, two raised bone-blade arms, orange eyes and tusks. It is clearly a lower-detail version. The body is small and blocky with noisy textures, and the head and tusks are weak. It reads loosely as the WC3 unit, whose icon is orange and purple. It would pass as an alpha placeholder, but it isn't polished. |
<!-- EVAL-REPORT:end -->

## 4. Leitura (juiz só; a reescrever quando houver humano)

- **Juiz (Sonnet, 30/30 chamadas válidas): Q1 2,10, Q2 3,13, Q3 2,27.** Na escala de 1–5 o juiz diz que os modelos são "em parte" fiéis
  ao concept, pouco parecidos com a unidade WC3 e não usáveis na alfa como estão (Q3 = 3 em 9/30, nunca 4 ou 5; Q2 = 4 em 7/30, nunca 5 — ver
  tabela por unidade). Bípedes 1,93 / 3,20 / 2,33 vs não-bípedes 2,27 / 3,07 / 2,20: **a diferença de .17 de IoU front
  e .20 de parts entre os grupos não aparece na nota do juiz**.
- **Q1 correlaciona negativamente com o IoU front** (ρ −0,40, p 0,03): as unidades com melhor silhueta contra o concept são as que o juiz acha
  *menos* parecidas com o WC3. É coerente com a ficha 17: o concept é um redesign dieselpunk, e quanto melhor o modelo segue o concept
  menos se parece com o original. Q2 (fiel ao concept) tem a correlação positiva fraca esperada com IoU front (ρ 0,28, p 0,13) e nenhuma com
  left/parts. Q3 não correlaciona com nada (|ρ| ≤ .24). Os proxies do pipeline (IoU, parts) não prevêem a nota de "usável".
- O juiz é um teste **do mesmo tipo** dos das fichas 11–19 (LLM a olhar renders) mas com perguntas de produto, não de par A/B, e na mesma
  amostra que o humano vai ver. Sozinho não prova qualidade; serve para calibrar: se ρ humano↔juiz for alto, o juiz pode substituir o humano
  em largura; se for baixo, as "notas" das fichas não valem como medida.
- O mesmo vale para IoU/parts: a correlação humano↔IoU é o que diz se o gate do pipeline mede o que interessa (REVIEW §6.5).
- Limites: n = 30, 1 chamada por unidade (sem repetição: o juiz tem ruído próprio, ficha 13), 1 avaliador humano previsto (o autor, que também
  aprovou os sheets — não é cego ao concept); ≥ 3 avaliadores e concordância inter-avaliador ficam como trabalho futuro (04 §6.1).

## 5. Ficheiros

- `castle_fight/artifacts/model-sheets/eval/sample-30.json`, `eval/stimuli/<id>/concept-front.png`, `eval/computer-<ts>.json`, `eval/human-<ts>.json`
- `castle_fight/tools/blender/eval_judge.py`, `tools/blender/eval_report.py`
- `castle_fight/artifacts/model-sheets/viewer/eval.html`, `serve.py` (rotas `/eval`, `/api/eval`, `/api/eval/export`, `/eval/concept/<id>.png`)
