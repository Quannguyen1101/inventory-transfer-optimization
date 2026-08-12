from src import config


def test_service_level_categories_match_product_categories():
    assert set(config.SERVICE_LEVEL_BY_CATEGORY.keys()) == set(config.CATEGORIES)


def test_z_score_mapping_covers_all_service_levels():
    used_levels = set(config.SERVICE_LEVEL_BY_CATEGORY.values())
    assert used_levels.issubset(config.Z_SCORE_BY_SERVICE_LEVEL.keys())


def test_lead_time_covers_all_categories():
    assert set(config.CATEGORY_LEAD_TIME_DAYS.keys()) == set(config.CATEGORIES)
