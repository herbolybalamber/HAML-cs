# Adatvizualizációs terv (prezentációhoz)

## Cél
A demo lőfegyveres kill eseményeit úgy bemutatni, hogy gyorsan érthető legyen:
- milyen arányban történnek közel / távol,
- milyen küszöbnél érdemes párbajról beszélni,
- fegyvertípusonként mennyire tér el a távolságprofil,
- az összes kill mekkora része releváns player-vs-player lövés.

## Ajánlott slide sorrend

### 1) Kontextus és adatforrás
- Alap számok: összes kill, lőfegyveres player kill, kivételek.
- Vizualizáció: `outputs/plots/presentation/kill_type_donut.png`
- Üzenet: a minta nagy része lőfegyveres player-vs-player interakció.

### 2) Küszöbérzékenység (mit jelent 600/900/1000?)
- Vizualizáció: `outputs/plots/presentation/threshold_share_bar.png`
- Üzenet: küszöbfüggő, hogy mennyi kill számít "közeli párbajnak".

### 3) Folytonos eloszlás és választott radius
- Vizualizáció: `outputs/plots/presentation/distance_ecdf.png`
- Üzenet: az ECDF görbén jól látszik, hol van az aktív `r` és mennyi kill esik alá.

### 4) Fegyverspecifikus különbségek
- Vizualizáció: `outputs/plots/presentation/weapon_distance_boxplot_top8.png`
- Üzenet: az egyes fegyverek eltérő távolságsávban dominálnak.

## Prezentációs tippek
- Egy slide = egy fő állítás.
- A tengelyeknél mindig jelezd: unit (HU), és opcionálisan mértékegység-átváltás (1 unit ≈ 2.54 cm).
- A kiválasztott `radius` forrását mindig tüntesd fel: átlag vagy manuálisan megadott.
- Érdemes a végén érzékenységi mini-táblát mutatni (pl. 600 / 900 / 1000 küszöb).
