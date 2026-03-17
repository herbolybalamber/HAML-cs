# HAML-cs

Rendezett CS demo-elemző projekt a párbaj- és kill-távolság vizsgálatához.

## Mappastruktúra

- `src/` – Python scriptek
	- `extract_duels.py` – párbajadatok kinyerése demóból
	- `duel_stats.py` – fegyverstatisztika a kinyert adatokból
	- `shot_kill_analysis.py` – fő kill + radius elemzés
	- `presentation_visualizations.py` – prezentációs ábrák generálása
- `config/` – konfigurációs fájlok
	- `shot_kill_config.json` (`radius` paraméter)
- `data/raw/` – nyers bemenetek (`.dem`, map)
- `data/processed/` – feldolgozott CSV/JSON eredmények
- `outputs/plots/` – generált ábrák
- `docs/` – dokumentáció
	- `visualization_plan.md` – javasolt vizualizációs prezentációs terv

## Gyors futtatás

A projekt gyökeréből:

```bash
src/.venv/bin/python src/shot_kill_analysis.py
```

Config pozíciós paraméterként is működik:

```bash
src/.venv/bin/python src/shot_kill_analysis.py config/shot_kill_config.json
```

## Prezentációs ábrák generálása

```bash
src/.venv/bin/python src/presentation_visualizations.py
```

Kimenet: `outputs/plots/presentation/`