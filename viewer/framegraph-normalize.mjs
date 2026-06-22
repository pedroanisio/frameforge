const USE_KEYS = new Set(["type", "id", "symbol", "box", "params", "decorative"]);

function clone(value) {
  if (Array.isArray(value)) return value.map(clone);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, clone(v)]));
  }
  return value;
}

function substitute(value, context) {
  if (typeof value === "string" && value.startsWith("$")) {
    const key = value.slice(1);
    return context[key] !== undefined ? clone(context[key]) : value;
  }
  if (Array.isArray(value)) return value.map((item) => substitute(item, context));
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, substitute(v, context)]));
  }
  return value;
}

function expandUseObject(obj, symbols) {
  if (!obj || typeof obj !== "object") return obj;
  if (obj.type !== "use") {
    if (Array.isArray(obj.children)) {
      return { ...obj, children: obj.children.map((child) => expandUseObject(child, symbols)) };
    }
    return obj;
  }

  const symbol = symbols[obj.symbol];
  if (!symbol || !Array.isArray(symbol.objects)) {
    return { ...obj, type: "group", children: [] };
  }
  const params = obj.params && typeof obj.params === "object" ? obj.params : {};
  const slots = Object.fromEntries(
    Object.entries(obj).filter(([key]) => !USE_KEYS.has(key)),
  );
  const context = { ...params, ...slots };
  const children = symbol.objects
    .map((child) => substitute(clone(child), context))
    .map((child) => expandUseObject(child, symbols));
  return {
    type: "group",
    id: obj.id,
    box: obj.box || symbol.box,
    decorative: obj.decorative,
    children,
    meta: { source_symbol: obj.symbol },
  };
}

function normalizeLegacyDeck(doc) {
  const deck = doc.deck || {};
  const symbols = deck.symbols || {};
  const slides = Array.isArray(doc.slides) ? doc.slides : [];
  return {
    dsl: "FrameGraph",
    version: "2.2.0",
    profile: "deck",
    title: doc.title || deck.title || "FrameGraph presentation deck",
    description: doc.description,
    defs: { ...(doc.defs || {}), tokens: { ...((doc.defs || {}).tokens || {}), ...(deck.tokens || {}) } },
    pages: slides.map((slide, index) => ({
      mode: "page",
      id: slide.id || `slide_${index + 1}`,
      title: slide.title,
      canvas: slide.canvas || deck.canvas,
      layers: (slide.visual?.layers || []).map((layer) => ({
        ...layer,
        objects: (layer.objects || []).map((obj) => expandUseObject(obj, symbols)),
      })),
      meta: {
        ...(slide.meta || {}),
        source_kind: doc.kind,
        slide: slide.slide,
        description: slide.description,
        notes: slide.notes,
      },
    })),
    meta: { ...(doc.meta || {}), source_kind: doc.kind },
  };
}

export function normalizeFrameGraphDoc(doc) {
  if (!doc || typeof doc !== "object") return doc;
  if (Array.isArray(doc.pages)) return doc;
  if (doc.dsl === "FrameGraph" && doc.kind === "presentation-deck" && Array.isArray(doc.slides)) {
    return normalizeLegacyDeck(doc);
  }
  return doc;
}
