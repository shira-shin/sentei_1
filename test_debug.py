from __future__ import annotations

from src.fspm import AppleTree, BudStatus, Environment, Metamer, RootSystem, simulate_step


def build_test_tree() -> AppleTree:
    genotype_params = {
        "apical_dominance": 0.1,
        "kappa": 0.02,
        "lambda_factor": 0.5,
    }
    root_system = RootSystem(nitrogen_uptake=1.0, cytokinin_level=1.0)
    tree = AppleTree(genotype_params=genotype_params, root_system=root_system)

    trunk = Metamer(
        id=1,
        parent_id=None,
        order=0,
        length=0.05,
        thickness=0.01,
        angle_world=(0.0, 1.0, 0.0),
        biomass_carbon=0.0,
        nsc_store=5.0,
        bud_status=BudStatus.DORMANT,
        leaf_area=0.02,
        incident_light=1200.0,
    )
    tree.add_metamer(trunk)
    return tree


def main() -> None:
    tree = build_test_tree()
    env = Environment(temperature_c=25.0)

    print(
        f"Day 0: Metamers={len(tree.metamers)}, "
        f"Status={[m.bud_status for m in tree.metamers]}"
    )

    for day in range(1, 6):
        result = simulate_step(tree, env)
        print(
            f"Day {day}: Assimilation={result.total_assimilation:.2f}, "
            f"New Metamers={len(result.new_metamers)}"
        )
        for metamer in tree.metamers:
            print(
                "  "
                f"Metamer ID={metamer.id}, "
                f"Status={metamer.bud_status}, "
                f"NSC={metamer.nsc_store:.2f}"
            )

        if len(tree.metamers) > 1:
            print(
                "★★★ 成功：新しい枝（Metamer）が展開しました！ "
                f"(Total: {len(tree.metamers)})"
            )


if __name__ == "__main__":
    main()
