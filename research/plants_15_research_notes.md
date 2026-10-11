# PotWise: 15-plant knowledge-base research notes

## What this dataset is

`plants_15_source_backed.json` contains 15 initial plant records using the current PotWise record fields. Plant identification names, light preferences, watering principles, and common mistakes were drawn from the source URLs stored in each record. Where possible, India-relevant cultivation guidance from Tamil Nadu Agricultural University (TNAU) was included for Tulsi, curry leaf, rose, and marigold.

## Important watering behavior

The seasonal watering strings are cautious rules of thumb, not an irrigation calendar. For container plants, check the actual soil moisture and recent rainfall before watering. Pot type, mix, pot size, light, airflow, root size, and local weather change drying speed. The weather API should adjust contextual reminders, not override the plant profile or make the application water automatically.

## Soil mix ratios: be transparent

The `soil_mix_parts` values are **PotWise starting recipes**, not exact ratios claimed by every individual plant page. Extension sources consistently emphasize drainage and a growing medium appropriate to plant type; for succulents, Iowa State Extension gives a general approach of one part organic material to two parts mineral material. PotWise expresses that as one part potting mix, one part perlite, and one part pumice/coarse grit for the driest mixes. For other container plants, the JSON uses a simple two-parts potting mix to one-part perlite baseline, or adds compost for flowering/herb plants. These should be presented as suggested starting mixes, and can be tuned against local ingredient availability and testing.

## Source index

1. **Aloe Vera** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/aloe-vera/common-name/aloe-vera/ ; Iowa State Extension (succulents): https://yardandgarden.extension.iastate.edu/how-to/growing-succulents-indoors
2. **Money Plant / Pothos** — University of Wisconsin–Madison Extension: https://hort.extension.wisc.edu/articles/pothos-epipremmum-aureum/
3. **Tulsi** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/ocimum-tenuiflorum/common-name/tulsi/ ; Tamil Nadu Agricultural University: https://www.agritech.tnau.ac.in/horticulture/horti_medicinal%20crops_tulsi.html
4. **Snake Plant** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/dracaena-trifasciata/common-name/snake-plant/ ; Iowa State Extension (succulents): https://yardandgarden.extension.iastate.edu/how-to/growing-succulents-indoors
5. **Spider Plant** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/chlorophytum-comosum/common-name/spider-plant/
6. **ZZ Plant** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/zamioculcas-zamiifolia/
7. **Jade Plant** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/crassula-ovata/ ; University of Wisconsin–Madison Extension: https://hort.extension.wisc.edu/dependable-durable-houseplants/
8. **Areca Palm** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/chrysalidocarpus-lutescens/common-name/yellow-palm/
9. **Peace Lily** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/spathiphyllum/common-name/peace-lily/
10. **Rose** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/rosa/ ; Tamil Nadu Agricultural University: https://agritech.tnau.ac.in/horticulture/horti_flower%20crops_commercial%20rose.html
11. **Hibiscus** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/hibiscus-rosa-sinensis/common-name/chinese-hibiscus/
12. **Marigold** — Tamil Nadu Agricultural University: https://agritech.tnau.ac.in/horticulture/horti_flower%20crops_marigold.html ; NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/tagetes/
13. **Curry Leaf** — Tamil Nadu Agricultural University: https://agritech.tnau.ac.in/horticulture/horti_vegetables_curry%20leaf.html
14. **Lucky Bamboo** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/dracaena-sanderiana/
15. **Rubber Plant** — NC State Extension Plant Toolbox: https://plants.ces.ncsu.edu/plants/ficus-elastica/common-name/indian-rubber-plant/

## Before using this in the app

- Confirm the actual `plant_template.json` and soil calculator accept the `soil_mix_parts` ingredient keys used here.
- The plant records intentionally leave `own_experience_note` empty.
- This is an initial curated set, not an exhaustive plant database.
- Do not use a model-generated confidence percentage as a calibrated probability.
- Do not provide care instructions for an unsupported plant by asking Gemma to invent them.
