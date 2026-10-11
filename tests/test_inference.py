from app.inference import fuse_material_prediction, normalize_material, whole_image_prediction


def test_model_labels_map_to_material_taxonomy():
    assert normalize_material("steel") == "steel"
    assert normalize_material("PET") == "PET"
    assert normalize_material("paper_cardboard") == "paper_cardboard"


def test_unrecognized_model_label_becomes_unknown():
    assert normalize_material("unmapped_label") == "unknown"


def test_kaggle_material_labels_map_to_conservative_app_materials():
    assert normalize_material("m_metal") == "metal"
    assert normalize_material("m-plastic-film") == "mixed_plastic"
    assert normalize_material("m_plastic_rigid") == "mixed_plastic"
    assert normalize_material("s_hazardous") == "battery"


def test_expanded_kaggle_categories_map_conservatively():
    assert normalize_material("battery") == "battery"
    assert normalize_material("biological") == "organic"
    assert normalize_material("clothes") == "textile"
    assert normalize_material("shoes") == "composite"
    assert normalize_material("trash") == "other_waste"
    assert normalize_material("plastic") == "mixed_plastic"


def test_confident_metal_detection_wins_over_shoe_classifier_guess():
    label, material, confidence = fuse_material_prediction("m_metal", 0.82, ("shoes", 0.98))
    assert (label, material, confidence) == ("m_metal", "metal", 0.82)


def test_confident_glass_detection_wins_over_shoe_classifier_guess():
    label, material, confidence = fuse_material_prediction("m_glass", 0.78, ("shoes", 0.97))
    assert (label, material, confidence) == ("m_glass", "glass", 0.78)


def test_matching_classifier_keeps_detected_material_label():
    label, material, confidence = fuse_material_prediction("m_metal", 0.82, ("metal", 0.91))
    assert label == "m_metal"
    assert material == "metal"
    assert confidence == 0.82


def test_weak_plastic_detection_uses_known_classifier_category():
    label, material, _ = fuse_material_prediction("m_plastic_rigid", 0.62, ("plastic", 0.96))
    assert (label, material) == ("plastic", "mixed_plastic")


def test_metal_classifier_corrects_confident_plastic_detection():
    label, material, confidence = fuse_material_prediction("m_plastic_rigid", 0.84, ("metal", 0.93))
    assert (label, material, confidence) == ("metal", "metal", 0.93)


def test_classifier_identifies_plastic_when_detection_category_is_unsupported():
    label, material, _ = fuse_material_prediction("s_other", 0.61, ("plastic", 0.99))
    assert (label, material) == ("plastic", "mixed_plastic")


def test_whole_image_fallback_identifies_known_plastic_category():
    result = whole_image_prediction(("plastic", 0.69))
    assert result["object_label"] == "plastic"
    assert result["material"] == "mixed_plastic"


def test_unrecognized_or_low_confidence_whole_image_is_unknown():
    assert whole_image_prediction(("glass", 0.49))["material"] == "unknown"
    assert whole_image_prediction(("made_up_class", 0.97))["material"] == "unknown"
    assert whole_image_prediction(None)["object_label"] == "unknown_item"


def test_dataset_general_waste_class_is_not_reported_as_unknown_item():
    result = whole_image_prediction(("trash", 0.97))
    assert result["object_label"] == "trash"
    assert result["material"] == "other_waste"


def test_whole_image_fallback_identifies_dataset_shoes_category():
    result = whole_image_prediction(("shoes", 0.99))
    assert result["object_label"] == "shoes"
    assert result["material"] == "composite"


def test_weak_detector_uses_confident_shoe_classifier_category():
    label, material, confidence = fuse_material_prediction("m_composite", 0.42, ("shoes", 0.94))
    assert (label, material, confidence) == ("shoes", "composite", 0.94)


def test_detected_composite_is_not_renamed_as_shoes_by_crop_classifier():
    label, material, _ = fuse_material_prediction("m_composite", 0.73, ("shoes", 0.94))
    assert label == "m_composite"
    assert material == "composite"

