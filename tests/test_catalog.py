from app.catalog import get_guidance, list_guidance


def test_guidance_covers_all_requested_routes():
    routes = {item["route"] for item in list_guidance()}
    assert routes == {"recyclable", "reusable", "refuse_processing", "needs_review"}


def test_unknown_material_abstains_and_is_marked_example():
    guidance = get_guidance("unknown")
    assert guidance["route"] == "needs_review"
    assert guidance["needs_review"] is True
    assert guidance["policy_source"].is_example is True


def test_catalog_has_recycling_outputs_and_reuse_ideas():
    steel = get_guidance("steel")
    rubber = get_guidance("rubber")
    assert steel["possible_outputs"]
    assert rubber["reuse_ideas"]


def test_generic_metal_is_sent_to_human_review():
    metal = get_guidance("metal")
    assert metal["route"] == "needs_review"
    assert metal["needs_review"] is True


def test_added_category_guidance_is_conservative():
    battery = get_guidance("battery")
    textile = get_guidance("textile")
    composite = get_guidance("composite")
    assert battery["route"] == "needs_review"
    assert textile["route"] == "reusable"
    assert composite["route"] == "needs_review"


def test_general_waste_class_is_reviewed_without_being_unknown():
    guidance = get_guidance("other_waste")
    assert guidance["route"] == "needs_review"
    assert "general-waste category" in guidance["reason"]

