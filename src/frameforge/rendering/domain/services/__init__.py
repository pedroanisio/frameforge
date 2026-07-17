"""frameforge.rendering.domain.services — the rendering domain services.

Each service is a pure resolver extracted from the monolithic SVG `Renderer`:

  ColorResolver       token/colour dereference                 (was Renderer.color)
  TextStyleResolver   text-style ref → resolved style dict     (was Renderer.text_style)
  CanvasResolver      page/master → (width, height)            (was Renderer.canvas_wh)
  StrokeResolver      object → SVG stroke attribute fragment   (was Renderer.stroke)

They hold only the token tables they need and recurse on themselves, so they
are independent of the SVG output path. Gradient *emission* (which mutates SVG
<defs>) still lives in the painter (Renderer._gradient) and is injected into the
StrokeResolver as a callable until step 4 introduces the value-object Scene.
"""
