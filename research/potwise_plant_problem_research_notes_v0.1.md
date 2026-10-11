# PotWise Plant Problem Helper — Research Notes (v0.1)

**Research snapshot:** 10 October 2026  
**Status:** Initial research draft; review and testing required before production use.

## Scope

This first pass covers the 15 plants currently in PotWise's knowledge base. It is a conservative **symptom-screening database**, not a definitive diagnostic model and not a substitute for a local plant clinic. Each problem contains possible causes, distinguishing clues, follow-up questions, safe initial actions, advice to avoid without stronger evidence, and source IDs.

## Core design decision: season is context, not a watering schedule

PotWise should not assume that a plant received rain because the current season is rainy, or that a plant needs less water simply because it is winter. The flow should ask about actual rain exposure, moisture at the root zone, drainage, light, temperature changes, and indoor/outdoor placement. A forecast can inform the questions and reminders; it cannot report whether one individual pot is wet.

The general seasonal rules in the JSON use conditions (heatwave, persistently wet spell, low-light/cool period, abrupt environmental change, warm-humid period without rain) rather than fixed months. This is intended to transfer across countries and climate zones.

## First-pass coverage by plant

- **Aloe vera:** soft/yellow/water-soaked leaves; visible pests or lesions.
- **Money plant / pothos:** yellow leaves and leaf drop; brown tips/spots; leggy growth.
- **Tulsi:** powdery mildew-like symptoms; rolled/chewed leaves; wilting in wet soil.
- **Snake plant:** yellow/soft leaf bases; mealybugs/spider mites or light scorch.
- **Spider plant:** brown tips; scorch or waterlogging.
- **ZZ plant:** yellow leaflets/stalks; scale or root/rhizome rot.
- **Jade plant:** leaf fall/soft leaves; visible sap-feeding pests.
- **Areca palm:** possible mite/whitefly/scale signs; brown tips/frond decline (marked preliminary).
- **Peace lily:** brown tips; drooping/yellow leaves with moisture/pest differential.
- **Rose:** black spot-like lesions; powdery mildew-like symptoms; possible insect damage.
- **Hibiscus:** bud/leaf drop after environmental change; scale-like pest signs.
- **Marigold:** wilt/stem decline; leaf spots/powder; distorted growth/pests.
- **Curry leaf:** possible leaf-chewing insects; watering/root stress (marked preliminary because the accessible case evidence is limited).
- **Lucky bamboo:** yellow leaves/stem rot; brown tips or visible pests.
- **Rubber plant:** leaf drop; mealybugs/scale/mites; scorch or cold-related damage.

## Source-quality and confidence notes

The draft prioritizes university extension plant profiles and Indian agricultural sources (Tamil Nadu Agricultural University and an ICAR-authored journal record). General houseplant diagnostic guidance is explicitly identified as general, not plant-specific. An Ask Extension response about a curry-leaf plant is case-specific and therefore lower-strength evidence; the JSON labels that pathway preliminary. The areca-palm brown-tip pathway is also marked preliminary because the cited species profile supports humidity preferences and pest risks, but not one definitive cause for tip browning.

The TNAU marigold page includes field-crop pesticide instructions. These instructions have **not** been imported as consumer treatment recommendations. The database instead prefers inspection, moisture/drainage checks, cultural adjustments, and pest confirmation.

## Required engineering behavior

1. Do not output “diagnosis confirmed.” Use “possible cause,” “clues that fit,” and “what to check next.”
2. Rank a candidate cause only when user observations match its clues; otherwise ask another question or say there is insufficient evidence.
3. Avoid watering advice until the user has checked root-zone moisture and drainage, where that is relevant.
4. Ask whether rain reached the pot; never assume that because a weather API reports rain or the user says “monsoon,” the pot received water.
5. Separate indoor and outdoor context. A houseplant can experience low light and slow drying during a cool season; an outdoor plant can experience direct sun, wind, or actual rainfall.
6. Do not recommend chemicals without verified pest identity and locally applicable label directions.
7. Keep source URLs in the dataset and show them in a “Why PotWise suggests this” expandable panel.
8. Add regression tests for ambiguous yellow leaves, wilting in wet versus dry soil, leggy growth, visible mealybugs, rose-like black spots and cases with insufficient clues.

## Limitations / next validation phase

- Coverage is a first pass, not exhaustive for every cultivar, local climate, or growing method.
- More India-specific, plant-specific sources should be added for curry leaf, Tulsi disease/pest management, hibiscus, and marigold as time allows.
- Image-only diagnosis should remain cautious; ask follow-up questions about moisture, light, recent changes, and visible pests.
- Before release, validate every record against the actual `plants.json` IDs and run schema tests. Do not replace the existing care dataset with this diagnostic database; keep it as a separate file (e.g. `data/plant_problems.json`).

## Source catalogue

- **NC_Aloe — Aloe Vera — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/aloe-vera/common-name/aloe-vera/  
  Scope: Plant-specific care, pests, leaf spot/rust, and overwatering/root rot.

- **KY_AloeSpots — Spots on aloe — Ask Extension** (University of Kentucky / Ask Extension)  
  https://ask.extension.org/kb/faq.php?id=285650  
  Scope: Aloe leaf spots and tip dieback can have moisture-related, disease, or pest causes; emphasizes diagnosis rather than assuming one cause.

- **WI_Pothos — Pothos (Epipremnum aureum) — Wisconsin Horticulture** (University of Wisconsin–Madison Extension)  
  https://hort.extension.wisc.edu/articles/pothos-epipremmum-aureum/  
  Scope: Pothos-specific yellowing, root rot, brown margins/tips, pests, and care.

- **UMD_Pothos — Pothos plant has yellow leaf and brown-spotted leaf — Ask Extension** (University of Maryland Extension / Ask Extension)  
  https://ask.extension.org/kb/faq.php?id=855914  
  Scope: Example diagnostic response emphasizing moisture, light, pests, normal old-leaf ageing, and uncertainty around leaf spots.

- **TNAU_Tulsi — Horticulture: Medicinal Crops — Tulsi** (Tamil Nadu Agricultural University)  
  https://www.agritech.tnau.ac.in/horticulture/horti_medicinal%20crops_tulsi.html  
  Scope: Tulsi cultivation, rainfall/soil-moisture-based irrigation, leaf rollers, powdery mildew, and root-rot/seedling-blight mention.

- **NC_Tulsi — Tulsi — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/ocimum-tenuiflorum/common-name/tulsi/  
  Scope: Species identity and general cultivation reference; use alongside TNAU for pest/disease notes.

- **NC_Snake — Snake Plant (Dracaena trifasciata) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/dracaena-trifasciata/common-name/snake-plant/  
  Scope: Snake-plant watering, root rot risk, and monitoring for mealybugs/spider mites.

- **NC_Dracaena — Dracaena — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/dracaena/  
  Scope: General Dracaena-family risk clues: waterlogging/root rot, leaf spot, browning from salts/low humidity, and leaf scorch.

- **NC_Spider — Spider Plant (Chlorophytum comosum) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/chlorophytum-comosum/common-name/chlorophytum/  
  Scope: Spider-plant-specific light, moisture, tap-water sensitivity and leaf-tip burn.

- **NC_SpiderVariegated — Reverse Spider Plant — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/chlorophytum-comosum-variegatum/common-name/reverse-spider-plant/  
  Scope: Cultivar page mentions waterlogging/root rot, brown tips, pest monitoring, and sun scorch; use as supporting genus-level context.

- **NC_ZZ — ZZ Plant (Zamioculcas zamiifolia) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/zamioculcas-zamiifolia/common-name/zz-plant/  
  Scope: ZZ plant identification and pest notes; generally low pest burden with scale monitoring.

- **UF_ZZ — Florida Foliage House Plant Care: ZZ Plant** (University of Florida IFAS Extension)  
  https://ask.ifas.ufl.edu/publication/EP480  
  Scope: ZZ plant: drought tolerance, scale, prolonged wet soil/root rot and cold-related discoloration.

- **Ask_ZZ — ZZ Plant — Ask Extension** (University of Maryland Extension / Ask Extension)  
  https://ask.extension.org/kb/faq.php?id=896161  
  Scope: Yellowing may relate to over-/underwatering, nutrition, or normal older-leaf ageing; an example, not a universal diagnostic rule.

- **NC_Jade — Jade Plant (Crassula ovata) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/crassula-ovata/  
  Scope: Jade plant root rot/leaf fall from overwatering and common sap-feeding pests.

- **NC_Areca — Areca Palm (Chrysalidocarpus lutescens) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/chrysalidocarpus-lutescens/common-name/yellow-palm/  
  Scope: Areca palm indoor light/humidity preferences and susceptibility to scale, whiteflies and spider mites.

- **NC_PeaceLily — Peace Lily (Spathiphyllum) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/spathiphyllum/common-name/peace-lily/  
  Scope: Peace-lily care, brown leaf tips, mealybugs, cold stress, and fertilizer/salt issues.

- **NC_Rose — Roses (Rosa) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/rosa/common-name/roses/  
  Scope: Rose pest and disease list, including mites, thrips, powdery mildew and leaf spots.

- **TNAU_RoseBlackSpot — Rose diseases: Black spot — TNAU Crop Protection** (Tamil Nadu Agricultural University)  
  https://agritech.tnau.ac.in/crop_protection/rose_diseases_1.html  
  Scope: Black spot signature: black lesions with feathery margins/yellow tissue and premature leaf fall; cultural prevention.

- **TNAU_RosePowdery — Rose diseases: Powdery mildew — TNAU Crop Protection** (Tamil Nadu Agricultural University)  
  https://agritech.tnau.ac.in/crop_protection/rose_diseases_2.html  
  Scope: Powdery mildew signature on young leaves, shoots and buds; distortion and poor bud opening; seasonal conditions noted.

- **NC_Hibiscus — Chinese Hibiscus (Hibiscus rosa-sinensis) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/hibiscus-rosa-sinensis/common-name/hibiscus/  
  Scope: Hibiscus sensitivity to environmental change and bud/leaf drop after moving; scale monitoring.

- **TNAU_Marigold — Horticulture: Flower Crops — Marigold** (Tamil Nadu Agricultural University)  
  https://www.agritech.tnau.ac.in/horticulture/horti_flower%20crops_marigold.html  
  Scope: Marigold pest signs (mealybug, thrips), leaf spot/root rot and water stagnation cautions; pesticide rates intentionally not carried into consumer advice.

- **NC_Marigold — Marigold (Tagetes) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/tagetes/common-name/marigold/  
  Scope: Marigold susceptibility to wilt, stem rot, leaf spots, botrytis and aster yellows; spider mites and slugs.

- **ICAR_CurryBeetle — Sporadic outbreak of curry leaf tortoise beetle on curry leaf — Pest Management in Horticultural Ecosystems** (Indian Agricultural Research Institute / ICAR-NBAIR authors; journal record)  
  https://indianjournals.com/article/pmhe-27-2-031  
  Scope: India-based research reporting tortoise beetle infestation on curry leaf; supports inspecting for leaf-chewing beetle damage, not a universal prevalence claim.

- **Ask_Curry — Curry leaf plant dying from top — Ask Extension** (Ask Extension)  
  https://ask.extension.org/kb/faq.php?id=272106  
  Scope: Case-specific expert reply considered overwatering after recent transplanting/frequent daily watering; low-strength anecdotal support only.

- **NC_LuckyBamboo — Lucky Bamboo (Dracaena sanderiana) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/dracaena-sanderiana/  
  Scope: Lucky bamboo yellowing/stem rot with excess water, brown tips with low humidity, and mealybug/mites/scale monitoring.

- **NC_Rubber — Rubber Plant (Ficus elastica) — North Carolina Extension Plant Toolbox** (NC State Extension)  
  https://plants.ces.ncsu.edu/plants/ficus-elastica/common-name/indian-rubber-plant/  
  Scope: Rubber plant leaf drop from overwatering/cold drafts, normal lower-leaf ageing, and mealybug/scale/spider-mite risk.

- **UMD_IndoorDiagnosis — Diagnose Indoor Plant Problems** (University of Maryland Extension)  
  https://extension.umd.edu/resource/diagnose-indoor-plant-problems  
  Scope: General indoor-plant differential diagnosis using visible pest clues, root condition and symptoms; not plant-specific.

- **UMD_IndoorInsects — Indoor Plant Insects** (University of Maryland Extension)  
  https://extension.umd.edu/resources/yard-garden/indoor-plants/indoor-plant-insects  
  Scope: General pest monitoring and linked identification resources for mealybugs, scale, mites, thrips, aphids, whiteflies and fungus gnats.

- **UMD_Mealybugs — Mealybugs on Indoor Plants** (University of Maryland Extension)  
  https://extension.umd.edu/resource/mealybugs-indoor-plants  
  Scope: White cottony wax, leaf/stem/underside location, honeydew/sooty mold, yellowing/stunting clues.

- **UMN_Lighting — Lighting for indoor plants and starting seeds** (University of Minnesota Extension)  
  https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/lighting-for-indoor-plants  
  Scope: Light level changes growth and water use; plants in lower light tend to grow more slowly and use less water.

- **UMN_Spring — Spring houseplant care** (University of Minnesota Extension)  
  https://extension.umn.edu/houseplants/spring-houseplant-care  
  Scope: Seasonal change and stronger spring light; transition plants gradually to brighter conditions to reduce scorch risk.

- **UMN_Winter — Winter houseplant tips** (University of Minnesota Extension)  
  https://extension.umn.edu/about/our-stories/news/winter-houseplant-tips  
  Scope: Reduced winter light, stretching toward light, indoor pest checks and monitoring.

