# sentei_1

木の剪定シミュレーション

## FSPM モジュール

設計仕様書に沿った簡易的な FSPM 計算モジュールを `src/fspm` に用意しています。

```python
from fspm import (
    AppleTree,
    BudStatus,
    Environment,
    Metamer,
    RootSystem,
    simulate_step,
)

root_system = RootSystem(nitrogen_uptake=1.2, cytokinin_level=0.6)

tree = AppleTree(
    genotype_params={
        "apical_dominance": 0.85,
        "internode_length": 0.05,
        "branching_angle": 0.78,
        "flower_rate": 0.4,
    },
    root_system=root_system,
)

metamer = Metamer(
    id=1,
    parent_id=None,
    order=0,
    length=0.05,
    thickness=0.4,
    angle_world=(0.0, 1.0, 0.0),
    biomass_carbon=1.2,
    nsc_store=0.8,
    bud_status=BudStatus.DORMANT,
    leaf_area=30.0,
    incident_light=1200.0,
)

tree.add_metamer(metamer)
result = simulate_step(tree, Environment(temperature_c=25.0))
print(result.total_assimilation)
```
