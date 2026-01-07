# sentei_1

木の剪定シミュレーション

## FSPM モジュール

設計仕様書に沿った簡易的な FSPM 計算モジュールを `src/fspm` に用意しています。

```python
from fspm import (
    Bud,
    BudState,
    Environment,
    Leaf,
    Metamer,
    Stem,
    simulate_step,
)

metamer = Metamer(
    stem=Stem(length_cm=5.0, diameter_cm=0.4, mass_g=12.0),
    leaf=Leaf(area_cm2=30.0, nitrogen_g_m2=1.8, incident_light_umol=1200.0),
    bud=Bud(state=BudState.ACTIVE, distance_from_apex_cm=2.0),
)

result = simulate_step([metamer], Environment(temperature_c=25.0, auxin_apex=0.8, cytokinin_root=0.6))
print(result.total_assimilation)
```
