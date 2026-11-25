---
name: asset-passports
description: >-
  Standardized identity sheets and metadata passports for characters, props, vehicles, and environments across generative AI pipelines.
---

# Asset Passports for Generative AI Pipelines

Asset Passports define permanent, invariant specifications for every asset used across multi-shot AI storytelling and game production.

## Asset Passport Specification (YAML)
```yaml
asset_id: "char_maya_cyberpunk_01"
type: "character"
invariant_attributes:
  gender: "female"
  apparent_age: "26"
  ethnicity: "East Asian"
  hair: "asymmetrical neon-blue bob cut, left side shaved"
  eyes: "dark brown with subtle gold prosthetic ring in right eye"
  wardrobe:
    jacket: "oversized weathered matte black bomber jacket with orange inner lining"
    top: "grey fitted techwear turtleneck"
    accessories: "titanium hoop earring on left ear"
negative_invariants:
  - "blonde hair"
  - "clean brand-new clothing"
  - "sunglasses"
reference_images:
  front_shot: "assets/refs/maya_front.png"
  profile_shot: "assets/refs/maya_side.png"
```
