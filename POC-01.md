## Proposed solution: **Vector Drawing Coach MCP**

Build **one MCP server** exposing **N drawing capabilities/tools** that guide an AI model through a disciplined, multi-step vector drawing process.

The core principle:

```text
User intent
→ semantic scene model
→ geometric construction
→ perspective projection
→ layered vector plan
→ style grammar application
→ SVG/vector generation
→ visual critique
→ iterative refinement
```

The MCP should not simply “generate SVG.” It should act like a **drawing instructor, geometry engine, style interpreter, layer planner, and vector validator**.

---

# 1. Goal

Create an MCP that teaches/guides an AI to draw:

```text
any subject
in any style
from any perspective
using vectors
over multiple steps
with explicit layers
with self-correction
```

The AI should learn to think like this:

```text
Do not draw the final image immediately.

First:
1. Understand the subject.
2. Decompose it into volumes.
3. Choose camera/perspective.
4. Build construction guides.
5. Plan layers.
6. Draw primitive forms.
7. Apply style.
8. Add detail.
9. Validate geometry.
10. Refine.
```

---

# 2. High-level architecture

```text
┌──────────────────────────────┐
│          AI Model             │
│  reasoning / planning / style │
└──────────────┬───────────────┘
               │ MCP calls
               ▼
┌────────────────────────────────────────────┐
│          Vector Drawing Coach MCP           │
├────────────────────────────────────────────┤
│  1. Intent Parser                           │
│  2. Subject Decomposer                      │
│  3. Perspective Engine                      │
│  4. Style Grammar Engine                    │
│  5. Layer Planner                           │
│  6. Vector Primitive Generator              │
│  7. SVG Composer                            │
│  8. Visual Critic                           │
│  9. Iteration / Version Manager             │
│ 10. Teaching / Explanation Engine           │
└────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│       SVG / Vector Output     │
│ layers, groups, paths, styles │
└──────────────────────────────┘
```

The AI remains responsible for creative direction.
The MCP provides structure, geometry, reusable tools, validation, and iterative feedback.

---

# 3. Core representation

The MCP should use an intermediate representation instead of generating SVG directly.

## `DrawingIntent`

```json
{
  "subject": "cybernetic crab",
  "style": "Moebius-inspired clean sci-fi line art",
  "perspective": "low-angle 3/4 view",
  "mood": "mythic, surreal, precise",
  "output": {
    "format": "svg",
    "canvas": {
      "width": 1600,
      "height": 2200
    }
  }
}
```

## `SceneGraph`

```json
{
  "objects": [
    {
      "id": "crab_body",
      "type": "ellipsoid_volume",
      "position": [0, 0, 0],
      "scale": [3.2, 1.4, 1.0],
      "semantic_role": "main mass"
    },
    {
      "id": "left_claw",
      "type": "compound_volume",
      "semantic_role": "dominant foreground gesture"
    }
  ]
}
```

## `CameraModel`

```json
{
  "view": "three_quarter",
  "horizon_y": 880,
  "vanishing_points": {
    "left": [-1200, 850],
    "right": [2600, 850],
    "vertical": null
  },
  "lens_feel": "mild wide-angle",
  "angle": "low"
}
```

## `StyleProfile`

```json
{
  "line_quality": {
    "outer_contour": "thick confident lines",
    "inner_detail": "thin precise lines",
    "hatching": "sparse directional"
  },
  "shape_language": {
    "primary": "organic curves",
    "secondary": "mechanical angular inserts"
  },
  "color_strategy": {
    "palette": "limited muted cyan, rust, bone white",
    "shading": "flat cel shading with controlled gradients"
  }
}
```

## `LayerPlan`

```json
{
  "layers": [
    "00_canvas",
    "01_perspective_guides",
    "02_construction_volumes",
    "03_base_silhouettes",
    "04_major_forms",
    "05_mechanical_details",
    "06_line_art",
    "07_flat_colors",
    "08_shadows",
    "09_highlights",
    "10_texture_marks",
    "11_final_overpaint_vectors"
  ]
}
```

This gives the AI a stable cognitive scaffold.

---

# 4. MCP capabilities

The MCP exposes tools grouped by capability.

## A. Intent and prompt structuring tools

### `parse_drawing_intent`

Converts user input into a structured drawing brief.

```text
Input:
"Draw a samurai frog in ukiyo-e style, top-down perspective, jumping over water."

Output:
DrawingIntent
```

### `clarify_missing_drawing_constraints`

Finds missing information, but should also provide defaults when possible.

```json
{
  "missing": ["canvas ratio", "level of detail"],
  "defaults": {
    "canvas_ratio": "4:5 portrait",
    "detail_level": "medium-high"
  }
}
```

### `expand_subject_semantics`

Breaks the subject into visual concepts.

```text
samurai frog
→ frog anatomy
→ armor plates
→ katana
→ jumping pose
→ water splash
→ ukiyo-e wave motifs
```

---

## B. Subject decomposition tools

### `decompose_subject_to_forms`

Turns a subject into primitive volumes.

```json
{
  "frog_head": "sphere",
  "frog_torso": "squashed_ellipsoid",
  "thighs": "tapered_cylinders",
  "armor": "layered_curved_planes",
  "katana": "long thin rectangular prism"
}
```

### `create_anatomy_or_object_landmarks`

Creates anchor points.

```json
{
  "landmarks": [
    "head_center",
    "eye_left",
    "eye_right",
    "shoulder_left",
    "shoulder_right",
    "hip_left",
    "hip_right",
    "weapon_tip"
  ]
}
```

### `build_pose_skeleton`

Creates a gesture skeleton before details.

```json
{
  "gesture": "compressed spring-like jump",
  "spine_curve": "C-shaped",
  "limb_flow": "diagonal upward motion",
  "dominant_action_line": "bottom-left to top-right"
}
```

---

## C. Perspective and geometry tools

This is one of the most important parts.

The AI should not fake perspective. It should construct it.

### `solve_perspective_camera`

Given a perspective description, returns horizon, vanishing points, and projection rules.

```json
{
  "perspective": "low-angle 3/4 view",
  "camera": {
    "horizon_y": 1200,
    "left_vp": [-900, 1180],
    "right_vp": [2500, 1180],
    "vertical_vp": null
  }
}
```

### `generate_perspective_grid`

Returns SVG guide lines.

```text
Layer:
01_perspective_guides
```

### `project_3d_point_to_2d`

Projects object landmarks into the drawing plane.

```json
{
  "input": {
    "point_3d": [1.2, 0.5, 3.0],
    "camera": "camera_01"
  },
  "output": {
    "point_2d": [843, 1102]
  }
}
```

### `construct_box_in_perspective`

Useful for vehicles, buildings, rooms, furniture, robots, weapons, machinery.

### `construct_ellipse_in_perspective`

Crucial for heads, wheels, cups, cylinders, eyes, planets, tunnels.

### `validate_perspective_consistency`

Detects common mistakes:

```text
- edges do not converge to correct vanishing point
- ellipses do not match plane orientation
- foreground scale inconsistent
- overlapping objects violate depth order
```

---

## D. Style grammar tools

The AI needs style as rules, not as vague adjectives.

### `create_style_profile`

Turns a named style into operational vector rules.

Example:

```text
"ligne claire sci-fi comic style"
```

Becomes:

```json
{
  "line_weight": {
    "outer": 4,
    "inner": 1.5,
    "detail": 0.8
  },
  "fills": "flat",
  "shadows": "minimal",
  "texture": "controlled hatching",
  "color_count": "limited",
  "edge_behavior": "clean closed contours",
  "detail_density": "medium-high"
}
```

### `compare_style_profiles`

Useful when the user asks for hybrid styles:

```text
"Moebius + Brazilian cordel + cyberpunk"
```

The MCP can resolve tensions:

```text
Moebius:
- clean contour
- spacious composition
- precise sci-fi details

Cordel:
- high-contrast black cuts
- folk texture
- symbolic simplification

Cyberpunk:
- dense signage
- neon accents
- machinery clutter
```

Result:

```text
Use Moebius for line discipline,
cordel for texture marks,
cyberpunk for props and lighting accents.
```

### `apply_style_to_layer_plan`

Maps style rules to each layer.

```json
{
  "06_line_art": {
    "outer_contour": 4,
    "inner_detail": 1.2,
    "hatching": "sparse"
  },
  "07_flat_colors": {
    "palette": ["bone", "rust", "cyan", "charcoal"]
  },
  "08_shadows": {
    "method": "flat cel shadow",
    "opacity": 0.28
  }
}
```

---

## E. Layer planning tools

### `create_layer_stack`

Generates drawing stages.

```text
1. Guides
2. Construction
3. Silhouette
4. Main masses
5. Secondary forms
6. Details
7. Line art
8. Color
9. Shadow
10. Highlights
11. Texture
12. Final cleanup
```

### `plan_layer_dependencies`

Prevents premature detail.

```json
{
  "mechanical_detail_layer": {
    "depends_on": ["base_silhouette", "major_forms"]
  },
  "shadows": {
    "depends_on": ["flat_colors", "light_direction"]
  }
}
```

### `validate_layer_order`

Detects bad sequencing:

```text
Error:
Detail layer created before construction volume.

Suggestion:
Create silhouette and major form layers first.
```

---

## F. Vector generation tools

The MCP should expose low-level vector primitives.

### `create_svg_canvas`

Creates base SVG.

### `create_path_from_points`

Creates Bézier paths.

```json
{
  "points": [
    [100, 200],
    [180, 140],
    [300, 210]
  ],
  "curve_type": "smooth_bezier",
  "closed": false
}
```

### `create_contour_path`

Creates silhouette outlines.

### `create_hatching_pattern`

Creates controlled vector hatching.

```json
{
  "area": "shadow_under_claw",
  "direction": "diagonal",
  "density": "medium",
  "style": "woodcut"
}
```

### `create_vector_texture`

Supports:

```text
- stippling
- engraving
- halftone
- crosshatching
- dry brush imitation
- manga speed lines
- comic ink texture
- ukiyo-e wave marks
- blueprint grid
```

### `boolean_shape_operation`

Supports:

```text
union
subtract
intersect
clip
mask
```

### `simplify_path`

Reduces unnecessary path complexity.

### `smooth_path`

Improves curves.

### `validate_svg`

Checks:

```text
- invalid path commands
- unclosed shapes
- broken groups
- excessive path count
- invisible elements
- malformed transforms
```

---

## G. Rendering and preview tools

Even if the final output is SVG, the MCP should support raster preview for critique.

### `render_svg_preview`

Turns SVG into PNG preview.

### `analyze_preview`

Detects visual issues.

```text
- weak silhouette
- confusing overlaps
- poor contrast
- inconsistent line weight
- anatomy/perspective distortion
- style drift
- cluttered focal point
```

### `compare_preview_to_intent`

Checks against the original brief.

```json
{
  "matches_subject": 0.92,
  "matches_style": 0.78,
  "matches_perspective": 0.84,
  "composition_strength": 0.71
}
```

---

## H. Critique and self-correction tools

### `critique_drawing_stage`

Used after each major phase.

```text
Stage:
construction

Critique:
The crab body has clear volume, but the legs do not follow the same perspective grid.
Foreground claw reads well. Rear legs need scale reduction.
```

### `suggest_next_vector_operations`

The MCP returns the next operations instead of vague advice.

```json
{
  "next_operations": [
    {
      "tool": "adjust_path",
      "target": "rear_left_leg",
      "reason": "scale too large for depth position"
    },
    {
      "tool": "add_occlusion_shadow",
      "target": "under_body",
      "reason": "improves grounding"
    }
  ]
}
```

### `score_drawing_quality`

Scores:

```text
composition
perspective
layer discipline
style consistency
semantic clarity
path cleanliness
readability at small size
```

---

# 5. The actual teaching process

The MCP should enforce a staged workflow.

## Stage 1 — Intent normalization

```text
Input:
"Draw a cybernetic crab like a mythological creature, viewed from below, in a clean French comic style."

MCP output:
- subject: cybernetic crab
- style: clean European sci-fi comic
- perspective: low-angle
- mood: mythological / monumental
- output: layered SVG
```

The AI is instructed:

```text
Do not create SVG yet.
First create a DrawingIntent object.
```

---

## Stage 2 — Visual decomposition

The subject is decomposed into drawable parts.

```text
cybernetic crab
├── organic crab body
│   ├── shell
│   ├── eyes
│   ├── legs
│   └── claws
├── cybernetic components
│   ├── armor plates
│   ├── cables
│   ├── sensors
│   └── mechanical joints
└── mythological cues
    ├── heroic scale
    ├── halo-like framing
    ├── symbolic marks
    └── monumental pose
```

The AI learns:

```text
Every subject becomes:
- gesture
- volumes
- landmarks
- surface details
- symbolic features
```

---

## Stage 3 — Perspective construction

For a low-angle view:

```text
- horizon line moves low or high depending camera intent
- foreground parts enlarge
- underside planes become visible
- verticals may converge if dramatic
- rear legs become smaller and partially occluded
```

The MCP returns:

```text
- horizon
- vanishing points
- perspective grid
- projection rules
- expected size falloff
```

The AI draws guides first.

---

## Stage 4 — Layer plan

Example layer stack:

```text
00_canvas
01_perspective_guides
02_gesture_skeleton
03_construction_volumes
04_depth_blocks
05_base_silhouette
06_primary_anatomy
07_cybernetic_components
08_clean_line_art
09_flat_colors
10_shadows
11_highlights
12_texture_marks
13_final_polish
```

Important rule:

```text
No detail layer before silhouette and volume layers are stable.
```

---

## Stage 5 — Primitive vector blocking

The AI uses simple shapes first:

```text
shell → ellipse / distorted oval
claws → tapered compound curves
legs → segmented cylinders
joints → ellipses in perspective
armor → clipped polygonal plates
cables → Bézier curves
```

The SVG is still rough, but structurally correct.

---

## Stage 6 — Silhouette validation

Before detail, the MCP checks:

```text
Can the subject be recognized in black silhouette?
Is the pose readable?
Does the perspective feel intentional?
Is the focal point clear?
Are important shapes overlapping badly?
```

If silhouette fails, the MCP says:

```text
Do not add detail yet.
Fix gesture, scale, and occlusion first.
```

This is critical.

Bad vector art often fails because the model adds decorative detail over weak structure.

---

## Stage 7 — Style application

The style engine transforms generic construction into a specific visual language.

For example:

```text
Clean European sci-fi comic style:
- use precise closed shapes
- avoid messy sketch marks
- use confident outer contours
- use minimal gradients
- use sparse technical details
- preserve negative space
```

The MCP applies style to:

```text
line weights
curves
corners
fills
shadow logic
texture density
detail frequency
color palette
```

---

## Stage 8 — Detail pass

Details are added only after the image reads correctly.

```text
Cybernetic details:
- mechanical seams following shell curvature
- small circular sensors
- cable loops
- rivets
- segmented armor plates
- asymmetrical repairs
```

The MCP checks:

```text
Do details follow form?
Do they respect perspective?
Do they reinforce the style?
Do they create clutter?
```

---

## Stage 9 — Color and light

The MCP defines a lighting model.

```json
{
  "light_direction": "upper left",
  "shadow_type": "flat cel shadow",
  "highlight_type": "thin rim highlight",
  "ambient": "cool blue"
}
```

Then each layer receives color instructions.

```text
flat colors first
shadows second
highlights third
texture last
```

---

## Stage 10 — Critique loop

The drawing is evaluated.

```text
Perspective score: 0.82
Style consistency: 0.76
Silhouette readability: 0.91
Layer cleanliness: 0.88
Vector quality: 0.80
```

Then the MCP proposes corrections.

```text
Fix:
1. Rear right leg is too large.
2. Left claw contour is too smooth for mechanical style.
3. Shadow layer does not follow light direction.
4. Detail density is too high near the secondary legs.
```

The AI applies changes over iterations.

---

# 6. Example MCP tool set

A practical first version could expose these tools:

```text
intent.parse
intent.expand_subject

style.create_profile
style.merge_profiles
style.apply_to_layer

geometry.solve_camera
geometry.create_perspective_grid
geometry.project_point
geometry.construct_box
geometry.construct_ellipse
geometry.validate_perspective

subject.decompose
subject.create_landmarks
subject.create_pose_skeleton

layers.create_plan
layers.validate_order

vector.create_canvas
vector.create_path
vector.create_closed_shape
vector.create_ellipse
vector.create_hatching
vector.create_texture
vector.boolean
vector.simplify
vector.validate_svg

render.preview_svg
render.analyze_preview

critic.review_stage
critic.suggest_next_steps
critic.score
```

That is already enough for a serious v1.

---

# 7. The AI-facing protocol

Every drawing task should follow this instruction protocol:

```text
You are drawing through the Vector Drawing Coach MCP.

Rules:
1. Never generate the final vector immediately.
2. Always create a DrawingIntent first.
3. Always decompose the subject into forms.
4. Always solve perspective before drawing.
5. Always create a layer plan.
6. Always block large shapes before details.
7. Always validate silhouette before detail.
8. Always apply style as explicit rules.
9. Always critique after each major stage.
10. Always preserve editable SVG structure.
```

---

# 8. Multi-step execution loop

```text
while drawing_not_approved:

    intent = MCP.intent.parse(user_goal)

    subject = MCP.subject.decompose(intent.subject)

    camera = MCP.geometry.solve_camera(intent.perspective)

    style = MCP.style.create_profile(intent.style)

    layers = MCP.layers.create_plan(subject, camera, style)

    construction = MCP.vector.block_forms(subject, camera, layers)

    critique_1 = MCP.critic.review_stage("construction", construction)

    if critique_1.has_blocking_issues:
        construction = MCP.critic.suggest_next_steps(construction)
        continue

    silhouette = MCP.vector.create_silhouette(construction)

    critique_2 = MCP.critic.review_stage("silhouette", silhouette)

    if critique_2.silhouette_score < threshold:
        revise gesture/composition

    line_art = MCP.style.apply_to_layer("line_art", silhouette, style)

    colors = MCP.style.apply_to_layer("flat_colors", line_art, style)

    shadows = MCP.vector.apply_lighting(colors, style.light_model)

    details = MCP.vector.add_details(shadows, subject.detail_plan)

    preview = MCP.render.preview_svg(details)

    final_critique = MCP.render.analyze_preview(preview)

    if final_critique.acceptable:
        return SVG
    else:
        apply corrections
```

---

# 9. Key design choice: style as grammar, not prompt text

Bad approach:

```text
"Draw it in cyberpunk ukiyo-e style."
```

Better approach:

```json
{
  "style": {
    "composition": "asymmetrical vertical drama",
    "line": "bold contour with carved internal marks",
    "color": "limited palette with neon accent",
    "texture": "woodcut-inspired hatching",
    "shape_language": "organic creature plus angular technology",
    "negative_space": "large flat areas preserved"
  }
}
```

The MCP should turn style names into executable constraints.

That is how the AI can generalize across styles.

---

# 10. Key design choice: perspective as math, not vibes

Bad approach:

```text
"Make it dramatic perspective."
```

Better approach:

```json
{
  "camera": {
    "type": "3_point_perspective",
    "horizon_y": 1320,
    "left_vp": [-1100, 1300],
    "right_vp": [2700, 1300],
    "vertical_vp": [800, -1800],
    "foreground_scale_factor": 1.35
  }
}
```

The AI should use geometry tools to construct the image.

This makes the system capable of drawing:

```text
top-down
low-angle
isometric
orthographic
fisheye-like approximation
one-point perspective
two-point perspective
three-point perspective
exploded technical view
cutaway view
blueprint view
comic panel view
```

---

# 11. Output SVG structure

The final SVG should remain editable.

Example:

```xml
<svg width="1600" height="2200" viewBox="0 0 1600 2200">
  <g id="00_canvas"></g>
  <g id="01_perspective_guides" opacity="0.15"></g>
  <g id="02_construction_volumes" opacity="0.25"></g>
  <g id="03_base_silhouette"></g>
  <g id="04_major_forms"></g>
  <g id="05_mechanical_details"></g>
  <g id="06_line_art"></g>
  <g id="07_flat_colors"></g>
  <g id="08_shadows"></g>
  <g id="09_highlights"></g>
  <g id="10_texture_marks"></g>
  <g id="11_final_polish"></g>
</svg>
```

Each object should have semantic IDs:

```xml
<path id="left_claw_outer_contour" ... />
<path id="right_eye_sensor_ring" ... />
<g id="rear_legs_depth_group">...</g>
```

This enables later editing:

```text
"Make the left claw larger."
"Remove construction guides."
"Change the style to manga ink."
"Rotate the camera slightly."
"Add more cordel texture."
```

---

# 12. Recommended MVP

Do not start with “any style, any perspective.”

Start with a strong constrained MVP:

## MVP scope

```text
Output:
- SVG only

Subjects:
- creatures
- objects
- simple characters
- vehicles

Perspectives:
- front
- side
- 3/4
- top-down
- low-angle
- isometric

Styles:
- clean line art
- flat icon
- comic book
- manga ink
- blueprint
- woodcut
- children’s book
```

## MVP tools

```text
intent.parse
subject.decompose
geometry.solve_camera
geometry.generate_grid
layers.create_plan
style.create_profile
vector.create_svg
vector.create_path
vector.create_shape
vector.validate_svg
render.preview
critic.review
```

That is enough to prove the architecture.

---

# 13. Later advanced capabilities

After MVP:

```text
1. Reference image ingestion
2. Style extraction from examples
3. Reusable style packs
4. Pose libraries
5. Anatomy libraries
6. Object construction libraries
7. Automatic SVG cleanup
8. Constraint-based path optimization
9. Animation-ready layer exports
10. Figma / Illustrator / Inkscape export
11. Procedural texture generation
12. Multi-panel comic composition
13. Storyboard-to-vector pipeline
14. SVG-to-Lottie conversion
15. Interactive correction loop
```

---

# 14. Core insight

The MCP should not try to make the model “better at drawing” by giving it more prompts.

It should make the model draw through a **repeatable external discipline**:

```text
semantic decomposition
+ geometric construction
+ perspective validation
+ style grammar
+ layer discipline
+ vector primitives
+ visual critique loop
```

That is the difference between:

```text
AI as image generator
```

and:

```text
AI as trained vector illustrator with tools, process, and self-correction.
```

The final concept could be named:

```text
VectorCraft MCP
```

or more explicitly:

```text
Vector Drawing Coach MCP
```

Its role:

```text
Teach the AI how to think before drawing,
how to construct before styling,
how to layer before detailing,
and how to critique before finalizing.
```
