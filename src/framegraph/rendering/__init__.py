"""framegraph.rendering — the rendering bounded context.

Layering (hexagonal):

  domain/         pure, backend-agnostic, dependency-free core
                  (value objects + domain services that resolve and lay out
                   a FrameGraph document into a backend-neutral scene)
  application/    use cases that orchestrate the pipeline      (later step)
  infrastructure/ adapters: loaders, painters, measurers, writers (later step)

Step 2–3 of the migration extract the *pure* parts (geometry helpers and the
token/style/canvas/stroke resolvers) out of tooling/render_fixtures.py. The
legacy `Renderer` now delegates to these; SVG output is unchanged.
"""
