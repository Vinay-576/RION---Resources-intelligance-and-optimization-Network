"""Illustrative guidance catalogue. Replace and source-review for each pilot facility."""

from .schemas import Material, PolicySource, Route

POLICY_VERSION = "rion-example-policy-0.2.0"
POLICY_TITLE = "Illustrative facility policy (not local disposal guidance)"
NOTICE = (
    "This starter uses illustrative example rules, not verified local facility guidance. "
    "Confirm the route with your municipality or recycler before acting."
)

_CATALOG: dict[Material, dict[str, object]] = {
    "steel": {
        "route": "recyclable",
        "reason": "Example rule: clean steel items may be accepted in a metal recycling stream; confirm item format locally.",
        "possible_outputs": ["new steel products", "construction or manufacturing feedstock"],
        "reuse_ideas": ["Reuse a sound container for non-food storage after checking for sharp edges and residues."],
    },
    "metal": {
        "route": "needs_review",
        "reason": "The Kaggle training class is broad metal, not steel specifically. A photo cannot reliably distinguish steel from aluminum or confirm local acceptance; check a material mark or ask a person.",
        "possible_outputs": ["metal feedstock for products accepted by a local processor"],
        "reuse_ideas": ["Reuse an intact item only when its prior contents, edges, and intended use are known to be safe."],
    },
    "rubber": {
        "route": "reusable",
        "reason": "Example rule: reuse may be suitable when the rubber item is intact, clean, and safe for the intended use.",
        "possible_outputs": ["crumb rubber for selected surfaces", "rubber-modified products where a processor accepts it"],
        "reuse_ideas": ["Consider a sound tire for a reviewed non-food use; avoid burning or using contaminated rubber."],
    },
    "PET": {
        "route": "recyclable",
        "reason": "Example rule: some facilities accept clean PET containers; acceptance depends on item shape and local sorting rules.",
        "possible_outputs": ["polyester fiber", "recycled PET feedstock for selected packaging"],
        "reuse_ideas": ["Use a clean, intact container only for a suitable non-food purpose."],
    },
    "HDPE": {
        "route": "recyclable",
        "reason": "Example rule: some facilities accept selected HDPE containers; verify colors, lids, and container requirements locally.",
        "possible_outputs": ["recycled HDPE products", "pipes or durable goods where specifications allow"],
        "reuse_ideas": ["Reuse a clean, undamaged container for non-food storage."],
    },
    "PVC": {
        "route": "refuse_processing",
        "reason": "Illustrative facility rule only: this sample policy refuses PVC in its configured container stream. Other facilities may differ.",
        "possible_outputs": ["No output is promised by this example policy; ask a specialist facility about accepted PVC products."],
        "reuse_ideas": ["Reuse only if the item is intact and its previous contents and intended use are known."],
    },
    "LDPE": {
        "route": "needs_review",
        "reason": "Thin films and flexible LDPE often require a dedicated collection stream; this example cannot confirm acceptance.",
        "possible_outputs": ["plastic lumber or film feedstock at participating specialist facilities"],
        "reuse_ideas": ["Reuse a clean, undamaged bag where local hygiene and safety rules permit."],
    },
    "PP": {
        "route": "needs_review",
        "reason": "PP acceptance depends on the item format and local facility equipment; confirm before placing it in a stream.",
        "possible_outputs": ["selected recycled PP goods where a processor accepts the material"],
        "reuse_ideas": ["Reuse a clean, intact item for its original non-food purpose when safe."],
    },
    "PS": {
        "route": "needs_review",
        "reason": "PS foam and rigid PS may follow different routes; this image model cannot establish local acceptance.",
        "possible_outputs": ["specialist recycled PS feedstock where collection and processing exist"],
        "reuse_ideas": ["Reuse clean packaging only when it is intact and suitable for the intended use."],
    },
    "mixed_plastic": {
        "route": "needs_review",
        "reason": "Composite or mixed plastics need facility-specific review; visual appearance alone does not establish recyclability.",
        "possible_outputs": ["material recovery only where a local process accepts the specific composite"],
        "reuse_ideas": ["Reuse only if the item is intact, clean, and safe for its intended purpose."],
    },
    "glass": {
        "route": "recyclable",
        "reason": "Example rule: selected glass containers may be accepted; ceramics, mirrors, and heat-resistant glass often differ.",
        "possible_outputs": ["new glass containers", "glass aggregate in some local processes"],
        "reuse_ideas": ["Reuse an intact jar for storage after cleaning and checking for cracks."],
    },
    "paper_cardboard": {
        "route": "recyclable",
        "reason": "Example rule: clean, dry paper or cardboard may be accepted; coatings and food contamination can change the route.",
        "possible_outputs": ["recycled paper", "paperboard or packaging feedstock"],
        "reuse_ideas": ["Reuse a clean box for storage or shipping if it remains structurally sound."],
    },
    "battery": {
        "route": "needs_review",
        "reason": "Battery chemistry and condition are not visible reliably. Keep batteries out of ordinary recycling and use a locally approved battery collection point; isolate damaged batteries only under local safety guidance.",
        "possible_outputs": ["metals and battery materials recovered by an authorized processor"],
        "reuse_ideas": [],
    },
    "organic": {
        "route": "recyclable",
        "reason": "Organic waste may be composted or sent to anaerobic digestion where a local program accepts it. Check for packaging and contamination first.",
        "possible_outputs": ["compost or soil amendment", "biogas and digestate where anaerobic digestion is available"],
        "reuse_ideas": ["Use suitable clean plant scraps for home compost only when local guidance allows."],
    },
    "textile": {
        "route": "reusable",
        "reason": "Clean, dry, intact clothing may be reused or donated. Damaged or contaminated textiles need a local textile collection rule.",
        "possible_outputs": ["recovered textile fiber", "insulation or wiping cloth feedstock at participating processors"],
        "reuse_ideas": ["Donate wearable items or repurpose clean fabric as a repair patch or cloth."],
    },
    "composite": {
        "route": "needs_review",
        "reason": "Shoes and other multi-material items combine materials that a photo cannot separate. Ask a local reuse or specialist take-back program.",
        "possible_outputs": ["component recovery only where a specialist processor accepts the item"],
        "reuse_ideas": ["Reuse only if clean, intact, and safe for the intended use."],
    },
    "other_waste": {
        "route": "needs_review",
        "reason": "The training set's general-waste category does not identify its contents. Separate and identify the items before choosing a recycling or disposal stream.",
        "possible_outputs": [],
        "reuse_ideas": [],
    },
    "unknown": {
        "route": "needs_review",
        "reason": "The predicted class is unknown or unsupported. A person should identify the item and check local guidance.",
        "possible_outputs": [],
        "reuse_ideas": [],
    },
}


def get_guidance(material: Material, facility_id: str = "example_facility") -> dict[str, object]:
    """Prefer a facility row in RDS; otherwise return explicitly illustrative fixtures."""
    from .policy_repository import find_facility_guidance

    facility_rule = find_facility_guidance(material, facility_id)
    if facility_rule is not None:
        return facility_rule
    item = _CATALOG[material]
    return {
        **item,
        "policy_source": PolicySource(title=POLICY_TITLE, is_example=True),
        "needs_review": item["route"] == "needs_review" or item["route"] == "refuse_processing",
    }


def get_policy_version(facility_id: str = "example_facility") -> str:
    from .policy_repository import get_facility_policy_version

    return get_facility_policy_version(facility_id) or POLICY_VERSION


def list_guidance() -> list[dict[str, object]]:
    return [{"material": name, **get_guidance(name)} for name in _CATALOG]

