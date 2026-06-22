import React, {
  useState, useRef, useEffect, useLayoutEffect, useMemo, useCallback,
} from "react";
import * as yaml from "js-yaml";
import {
  ChevronLeft, ChevronRight, Maximize2, Crosshair, Upload, X,
  Palette, Layers, Type as TypeIcon, Info,
} from "lucide-react";

/* ============================================================ *
 *  Embedded demo document (Esfera deck, FrameGraph v2)
 * ============================================================ */
const DEMO_DOC = {"dsl":"FrameGraph","version":"2.2.0","profile":"deck","title":"Esfera reimagined style guide proposal deck — refined pass (improved: fit-safe label styles)","description":"Refined FrameGraph v2 deck proposing a new Esfera style guide: clearer brand rules, improved visual hierarchy, Santander relationship guidance, UI cards, palette, voice, rollout and governance.","lang":"pt-BR","defs":{"tokens":{"colors":{"bg":"#FBF7F2","bg_alt":"#F3ECE7","paper":"#FFFDF8","ink":"#181211","ink_soft":"#4A3F3B","muted":"#756963","muted_2":"#A39288","rule":"#DED1C9","rule_dark":"#BCA9A0","santander_red":"#E30613","esfera_red":"#D71920","reward_coral":"#FF6A5B","reward_orange":"#FF9F5A","reward_blush":"#F8DCD5","reward_pink":"#F6C3BE","charcoal":"#231B19","warm_dark":"#302421","success":"#4F7B57","warning":"#C47A3A","accent_soft":"#FFF1EE","white":"#FFFFFF","cream_chip":"#F7EEE8","deep_red":"#9F161E","transparent":"rgba(0,0,0,0)"},"fonts":{"sans":{"family":"DejaVu Sans","fallback":["Arial","sans-serif"]},"serif":{"family":"DejaVu Serif","fallback":["Georgia","Times New Roman","serif"]},"mono":{"family":"DejaVu Sans Mono","fallback":["Courier New","monospace"]}},"text_styles":{"eyebrow":{"font":"sans","size":20,"weight":700,"color":"esfera_red","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":13},"title_xl":{"font":"serif","size":70,"weight":500,"color":"ink","line_height":1.0,"wrap":true,"overflow":"shrink_to_fit"},"title_l":{"font":"serif","size":54,"weight":500,"color":"ink","line_height":1.05,"wrap":true,"overflow":"shrink_to_fit"},"title_m":{"font":"serif","size":40,"weight":500,"color":"ink","line_height":1.08,"wrap":true,"overflow":"shrink_to_fit"},"subtitle":{"font":"sans","size":25,"weight":400,"color":"muted","line_height":1.24,"wrap":true},"body":{"font":"sans","size":24,"weight":400,"color":"ink_soft","line_height":1.24,"wrap":true,"overflow":"clip"},"body_small":{"font":"sans","size":20,"weight":400,"color":"muted","line_height":1.22,"wrap":true,"overflow":"clip"},"body_bold":{"font":"sans","size":24,"weight":700,"color":"ink","line_height":1.2,"wrap":true},"label":{"font":"sans","size":17,"weight":700,"color":"muted","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":11},"label_ink":{"font":"sans","size":17,"weight":700,"color":"ink","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":11},"num":{"font":"serif","size":50,"weight":500,"color":"esfera_red","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":32},"quote":{"font":"serif","size":38,"weight":400,"color":"ink","line_height":1.18,"wrap":true},"caption":{"font":"sans","size":16,"weight":400,"color":"muted","line_height":1.12,"wrap":true},"table_header":{"font":"sans","size":18,"weight":700,"color":"ink","line_height":1.1,"wrap":true},"table_cell":{"font":"sans","size":17,"weight":400,"color":"ink_soft","line_height":1.12,"wrap":true},"inverse_title":{"font":"serif","size":58,"weight":500,"color":"bg","line_height":1.05,"wrap":true},"inverse_body":{"font":"sans","size":23,"weight":400,"color":"reward_blush","line_height":1.22,"wrap":true},"inverse_label":{"font":"sans","size":18,"weight":700,"color":"reward_orange","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":12},"footer":{"font":"sans","size":15,"weight":400,"color":"muted_2","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10},"footer_inverse":{"font":"sans","size":15,"weight":400,"color":"reward_blush","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10},"hero_logo":{"font":"sans","size":48,"weight":800,"color":"ink","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":31},"hero_logo_red":{"font":"sans","size":48,"weight":800,"color":"esfera_red","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":31},"metric_big":{"font":"serif","size":62,"weight":500,"color":"esfera_red","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":40},"section_kicker":{"font":"sans","size":15,"weight":800,"color":"esfera_red","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10},"micro":{"font":"sans","size":14,"weight":500,"color":"muted","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10},"micro_inverse":{"font":"sans","size":14,"weight":500,"color":"reward_blush","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10},"swatch_hex":{"font":"mono","size":14,"weight":400,"color":"muted","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10},"pill_text":{"font":"sans","size":15,"weight":700,"color":"white","align":"center","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10},"ui_button":{"font":"sans","size":16,"weight":700,"color":"white","align":"center","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10},"logo_label":{"font":"sans","size":16,"weight":700,"color":"muted","line_height":1.0,"overflow":"shrink_to_fit","min_font_size":10}},"stroke_styles":{"rule":{"stroke":"rule","stroke_width":1},"rule_dark":{"stroke":"rule_dark","stroke_width":1},"brand":{"stroke":"esfera_red","stroke_width":2},"dark":{"stroke":"charcoal","stroke_width":1},"dashed":{"stroke":"rule_dark","stroke_width":1,"stroke_dasharray":[8,6]},"red_rule":{"stroke":"esfera_red","stroke_width":2},"soft_red_rule":{"stroke":"reward_blush","stroke_width":2}},"styles":{}},"ontology":{"node_types":{"deck":{"meaning":"Presentation document"},"slide":{"meaning":"Presentation page"},"brand_token":{"meaning":"Reusable design token"},"component_guideline":{"meaning":"Guideline for UI component behavior"}},"edge_types":{"contains":{"meaning":"Composition relationship","directionality":"directed"}}}},"targets":[{"name":"16:9 presentation","canvas":{"size":[1600,900],"units":"px"}}],"pages":[{"mode":"page","id":"slide_01_cover","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_01_cover_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_01_cover_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s01_logo_txt","text":"Esfera","box":[80,86,220,52],"style":"hero_logo"},{"type":"rect","id":"s01_logo_bar","box":[264,122,58,8],"fill":"esfera_red","radius":4,"decorative":true},{"type":"text","id":"s01_eyebrow","text":"REIMAGINED STYLE GUIDE","box":[80,160,420,30],"style":"eyebrow"},{"type":"text","id":"s01_title","text":"A modern rewards brand system for Esfera","box":[80,220,920,170],"style":"title_xl"},{"type":"text","id":"s01_sub","text":"Proposal deck in FrameGraph v2. Repositions Esfera as a premium, confident and commerce-led ecosystem while preserving the Santander relationship.","box":[84,420,760,92],"style":"subtitle"},{"type":"rect","id":"s01_shape_1","box":[1130,110,330,330],"fill":"reward_blush","radius":165,"decorative":true},{"type":"rect","id":"s01_shape_2","box":[1230,240,250,250],"fill":"reward_orange","radius":125,"decorative":true,"opacity":0.84},{"type":"rect","id":"s01_shape_3","box":[1080,370,290,290],"fill":"esfera_red","radius":145,"decorative":true,"opacity":0.93},{"type":"rect","id":"s01_shape_4","box":[1220,530,180,180],"fill":"paper","radius":90,"decorative":true},{"type":"rect","id":"s01_tag","box":[84,670,430,50],"fill":"paper","stroke_style":"rule_dark","radius":25},{"type":"text","id":"s01_tag_text","text":"Brand system • UI direction • deck layouts • rollout","box":[112,686,390,20],"style":"label_ink"},{"type":"line","id":"slide_01_cover_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_01_cover_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_01_cover_footer_r","text":"01","box":[1470,846,50,22],"style":"footer","decorative":true},{"type":"rect","id":"s01_red_signal_line","box":[84,600,420,10],"fill":"esfera_red","radius":5,"decorative":true},{"type":"text","id":"s01_santander_note","text":"A Santander-born loyalty brand, reimagined as a premium rewards ecosystem.","box":[84,742,710,44],"style":"caption"},{"type":"line","id":"s01_orbit_a","from":[1040,660],"to":[1490,210],"stroke_style":"red_rule","decorative":true,"opacity":0.75},{"type":"line","id":"s01_orbit_b","from":[1030,210],"to":[1490,660],"stroke_style":"soft_red_rule","decorative":true,"opacity":0.75}]}],"meta":{"layout":"cover"}},{"mode":"page","id":"slide_02_opportunity","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_02_opportunity_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_02_opportunity_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s02_eyebrow","text":"WHY CHANGE","box":[80,80,220,28],"style":"eyebrow"},{"type":"text","id":"s02_title","text":"Esfera needs to feel less like a rewards utility and more like a desirable commerce platform","box":[80,130,1100,110],"style":"title_l"},{"type":"text","id":"s02_body","text":"The current public expression is functional and promotion-first. The opportunity is to build a system that still sells, but also signals trust, simplicity, and premium value.","box":[82,270,820,90],"style":"subtitle"},{"type":"rect","id":"s02_card_0","box":[90,420,410,250],"fill":"paper","stroke_style":"rule","radius":12},{"type":"text","id":"s02_card_h_0","text":"Today","box":[118,456,320,34],"style":"body_bold"},{"type":"text","id":"s02_card_b_0","text":"Useful but visually fragmented.\nHeavy emphasis on offer mechanics.","box":[118,512,340,110],"style":"body_small"},{"type":"text","id":"s02_card_n_0","text":"1","box":[118,610,44,44],"style":"num"},{"type":"rect","id":"s02_card_1","box":[565,420,410,250],"fill":"paper","stroke_style":"rule","radius":12},{"type":"text","id":"s02_card_h_1","text":"Risk","box":[593,456,320,34],"style":"body_bold"},{"type":"text","id":"s02_card_b_1","text":"The brand blends into generic loyalty experiences.\nLow emotional distinctiveness.","box":[593,512,340,110],"style":"body_small"},{"type":"text","id":"s02_card_n_1","text":"2","box":[593,610,44,44],"style":"num"},{"type":"rect","id":"s02_card_2","box":[1040,420,410,250],"fill":"paper","stroke_style":"rule","radius":12},{"type":"text","id":"s02_card_h_2","text":"Opportunity","box":[1068,456,320,34],"style":"body_bold"},{"type":"text","id":"s02_card_b_2","text":"Own a category between fintech trust and lifestyle rewards.","box":[1068,512,340,110],"style":"body_small"},{"type":"text","id":"s02_card_n_2","text":"3","box":[1068,610,44,44],"style":"num"},{"type":"line","id":"slide_02_opportunity_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_02_opportunity_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_02_opportunity_footer_r","text":"02","box":[1470,846,50,22],"style":"footer","decorative":true},{"type":"rect","id":"s02_shift_band","box":[85,710,1180,48],"fill":"accent_soft","radius":24,"stroke_style":"rule"},{"type":"text","id":"s02_shift_text","text":"Shift: from transactional rewards page → memorable loyalty-commerce brand","box":[115,724,1100,22],"style":"label_ink"}]}],"meta":{"layout":"problem"}},{"mode":"page","id":"slide_03_brand_vision","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_03_brand_vision_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_03_brand_vision_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s03_eyebrow","text":"BRAND VISION","box":[80,80,260,28],"style":"eyebrow"},{"type":"text","id":"s03_title","text":"Reframe Esfera around three feelings","box":[80,130,830,70],"style":"title_l"},{"type":"rect","id":"s03_blob_0","box":[190,285,160,160],"fill":"reward_blush","radius":80,"decorative":true,"opacity":0.95},{"type":"text","id":"s03_h_0","text":"Rewarding","box":[90,490,370,40],"style":"body_bold"},{"type":"text","id":"s03_b_0","text":"A brand that clearly shows benefit and momentum.","box":[90,548,380,84],"style":"body_small"},{"type":"rect","id":"s03_blob_1","box":[665,285,160,160],"fill":"reward_orange","radius":80,"decorative":true,"opacity":0.95},{"type":"text","id":"s03_h_1","text":"Confident","box":[565,490,370,40],"style":"body_bold"},{"type":"text","id":"s03_b_1","text":"A visual system that feels institutional enough for Santander trust.","box":[565,548,380,84],"style":"body_small"},{"type":"rect","id":"s03_blob_2","box":[1140,285,160,160],"fill":"esfera_red","radius":80,"decorative":true,"opacity":0.95},{"type":"text","id":"s03_h_2","text":"Desirable","box":[1040,490,370,40],"style":"body_bold"},{"type":"text","id":"s03_b_2","text":"An experience that turns offers into curated opportunities.","box":[1040,548,380,84],"style":"body_small"},{"type":"line","id":"slide_03_brand_vision_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_03_brand_vision_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_03_brand_vision_footer_r","text":"03","box":[1470,846,50,22],"style":"footer","decorative":true},{"type":"line","id":"s03_axis_0","from":[155,440],"to":[425,440],"stroke_style":"red_rule","decorative":true},{"type":"text","id":"s03_axis_label_0","text":"BENEFIT","box":[155,455,160,20],"style":"micro"},{"type":"line","id":"s03_axis_1","from":[630,440],"to":[900,440],"stroke_style":"rule_dark","decorative":true},{"type":"text","id":"s03_axis_label_1","text":"TRUST","box":[630,455,160,20],"style":"micro"},{"type":"line","id":"s03_axis_2","from":[1105,440],"to":[1375,440],"stroke_style":"rule_dark","decorative":true},{"type":"text","id":"s03_axis_label_2","text":"DESIRE","box":[1105,455,160,20],"style":"micro"}]}],"meta":{"layout":"principles"}},{"mode":"page","id":"slide_04_principles","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_04_principles_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_04_principles_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s04_eyebrow","text":"DESIGN PRINCIPLES","box":[80,80,320,28],"style":"eyebrow"},{"type":"text","id":"s04_title","text":"Five rules for every Esfera surface","box":[80,130,780,70],"style":"title_l"},{"type":"line","id":"s04_rule_0","from":[96,312],"to":[1450,312],"stroke_style":"rule"},{"type":"text","id":"s04_p_0","text":"1. Commercial, but never noisy.","box":[100,260,980,42],"style":"body_bold"},{"type":"line","id":"s04_rule_1","from":[96,404],"to":[1450,404],"stroke_style":"rule"},{"type":"text","id":"s04_p_1","text":"2. Red is a signal, not wallpaper.","box":[100,352,980,42],"style":"body_bold"},{"type":"line","id":"s04_rule_2","from":[96,496],"to":[1450,496],"stroke_style":"rule"},{"type":"text","id":"s04_p_2","text":"3. Rewards should read as value, not complexity.","box":[100,444,980,42],"style":"body_bold"},{"type":"line","id":"s04_rule_3","from":[96,588],"to":[1450,588],"stroke_style":"rule"},{"type":"text","id":"s04_p_3","text":"4. Santander trust appears through precision and clarity.","box":[100,536,980,42],"style":"body_bold"},{"type":"line","id":"s04_rule_4","from":[96,680],"to":[1450,680],"stroke_style":"rule"},{"type":"text","id":"s04_p_4","text":"5. Every screen should make the next best action obvious.","box":[100,628,980,42],"style":"body_bold"},{"type":"line","id":"slide_04_principles_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_04_principles_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_04_principles_footer_r","text":"04","box":[1470,846,50,22],"style":"footer","decorative":true}]}],"meta":{"layout":"list"}},{"mode":"page","id":"slide_05_palette","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_05_palette_bg","box":[0,0,1600,900],"fill":"charcoal","decorative":true},{"type":"rect","id":"slide_05_palette_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s05_eyebrow","text":"VISUAL CORE","box":[80,96,220,28],"style":"inverse_label"},{"type":"text","id":"s05_title","text":"The new Esfera palette","box":[80,180,680,70],"style":"inverse_title"},{"type":"text","id":"s05_body","text":"Keep the core black / white / red equity, then add a controlled reward spectrum for highlights, moments, and campaigns.","box":[84,290,660,82],"style":"inverse_body"},{"type":"rect","id":"s05_chip_0","box":[860,170,210,150],"fill":"esfera_red","radius":18},{"type":"text","id":"s05_chip_lab_0","text":"Esfera Red","box":[860,340,210,28],"style":"inverse_label"},{"type":"rect","id":"s05_chip_1","box":[1150,170,210,150],"fill":"reward_orange","radius":18},{"type":"text","id":"s05_chip_lab_1","text":"Reward Orange","box":[1150,340,210,28],"style":"inverse_label"},{"type":"rect","id":"s05_chip_2","box":[860,430,210,150],"fill":"reward_blush","radius":18},{"type":"text","id":"s05_chip_lab_2","text":"Reward Blush","box":[860,600,210,28],"style":"inverse_label"},{"type":"rect","id":"s05_chip_3","box":[1150,430,210,150],"fill":"charcoal","radius":18},{"type":"text","id":"s05_chip_lab_3","text":"Warm Charcoal","box":[1150,600,210,28],"style":"inverse_label"},{"type":"line","id":"slide_05_palette_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule_dark","decorative":true,"opacity":0.6},{"type":"text","id":"slide_05_palette_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer_inverse","decorative":true},{"type":"text","id":"slide_05_palette_footer_r","text":"05","box":[1470,846,50,22],"style":"footer_inverse","decorative":true},{"type":"text","id":"s05_hex_0","text":"#D71920","box":[860,370,210,24],"style":"micro_inverse"},{"type":"text","id":"s05_hex_1","text":"#FF9F5A","box":[1150,370,210,24],"style":"micro_inverse"},{"type":"text","id":"s05_hex_2","text":"#F8DCD5","box":[860,630,210,24],"style":"micro_inverse"},{"type":"text","id":"s05_hex_3","text":"#231B19","box":[1150,630,210,24],"style":"micro_inverse"}]}],"meta":{"layout":"section"}},{"mode":"page","id":"slide_06_typography","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_06_typography_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_06_typography_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s06_eyebrow","text":"TYPOGRAPHY","box":[80,80,220,28],"style":"eyebrow"},{"type":"text","id":"s06_title","text":"Editorial hierarchy with commerce clarity","box":[80,130,860,70],"style":"title_l"},{"type":"rect","id":"s06_panel","box":[90,250,650,440],"fill":"paper","stroke_style":"rule","radius":16},{"type":"text","id":"s06_serif_lab","text":"Display / narrative","box":[120,286,250,26],"style":"label"},{"type":"text","id":"s06_serif_demo","text":"Big ideas. Premium moments. Calm confidence.","box":[120,334,520,160],"style":"quote"},{"type":"rect","id":"s06_panel_2","box":[840,250,670,440],"fill":"paper","stroke_style":"rule","radius":16},{"type":"text","id":"s06_sans_lab","text":"UI / product / offers","box":[872,286,250,26],"style":"label"},{"type":"text","id":"s06_sans_demo","text":"Ganhe mais pontos nas lojas parceiras.\nUse seus pontos em viagens, produtos e descontos na fatura.","box":[872,340,540,100],"style":"body"},{"type":"text","id":"s06_rule_note","text":"Recommendation: keep a serif for storytelling and a clean sans for interfaces.","box":[82,735,900,34],"style":"body_small"},{"type":"line","id":"slide_06_typography_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_06_typography_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_06_typography_footer_r","text":"06","box":[1470,846,50,22],"style":"footer","decorative":true}]}],"meta":{"layout":"two-column"}},{"mode":"page","id":"slide_07_logo","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_07_logo_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_07_logo_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s07a_logo_txt","text":"Esfera","box":[100,170,220,52],"style":"hero_logo"},{"type":"rect","id":"s07a_logo_bar","box":[284,206,58,8],"fill":"esfera_red","radius":4,"decorative":true},{"type":"text","id":"s07_eyebrow","text":"LOGO SYSTEM","box":[80,80,250,28],"style":"eyebrow"},{"type":"text","id":"s07_title","text":"Preserve the Esfera wordmark, simplify its usage","box":[80,130,980,70],"style":"title_l"},{"type":"text","id":"s07_body","text":"The underscore remains the distinctive mnemonic. Use it as the single most recognizable graphic element in product, motion, and campaign assets.","box":[82,260,760,84],"style":"subtitle"},{"type":"rect","id":"s07_panel_0","box":[90,470,610,220],"fill":"paper","stroke_style":"rule","radius":14},{"type":"text","id":"s07_panel_h_0","text":"Do","box":[116,500,200,34],"style":"body_bold"},{"type":"text","id":"s07_panel_b_0","text":"Use the wordmark on light backgrounds.\nUse the underscore as an accent or progress motif.\nPair with Santander only when relationship clarity matters.","box":[116,548,540,110],"style":"body_small"},{"type":"rect","id":"s07_panel_1","box":[810,470,610,220],"fill":"paper","stroke_style":"rule","radius":14},{"type":"text","id":"s07_panel_h_1","text":"Avoid","box":[836,500,200,34],"style":"body_bold"},{"type":"text","id":"s07_panel_b_1","text":"Do not repeat red aggressively.\nDo not surround the logo with badges or noisy promo containers.\nDo not distort the underscore proportion.","box":[836,548,540,110],"style":"body_small"},{"type":"line","id":"slide_07_logo_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_07_logo_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_07_logo_footer_r","text":"07","box":[1470,846,50,22],"style":"footer","decorative":true},{"type":"rect","id":"s07_safety_box","box":[82,135,360,126],"fill":"transparent","stroke_style":"dashed"},{"type":"text","id":"s07_clearspace","text":"Clearspace: keep one underscore-height around the mark.","box":[470,188,440,38],"style":"caption"},{"type":"rect","id":"s07_santander_lockup","box":[975,160,420,82],"fill":"paper","stroke_style":"rule","radius":10},{"type":"text","id":"s07_lockup_text","text":"Uma empresa Santander","box":[1010,186,250,28],"style":"body_bold"},{"type":"rect","id":"s07_lockup_red","box":[1280,193,58,10],"fill":"santander_red","radius":5},{"type":"text","id":"s07_lockup_note","text":"Use relationship lockup for institutional trust moments, not every promo card.","box":[980,260,400,56],"style":"body_small"}]}],"meta":{"layout":"brand rules"}},{"mode":"page","id":"slide_08_ui_system","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_08_ui_system_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_08_ui_system_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s08_eyebrow","text":"PRODUCT UI","box":[80,80,220,28],"style":"eyebrow"},{"type":"text","id":"s08_title","text":"A card system that sells value instantly","box":[80,130,880,70],"style":"title_l"},{"type":"rect","id":"s08_ui_0","box":[100,300,390,280],"fill":"paper","stroke_style":"rule","radius":20},{"type":"rect","id":"s08_ui_top_0","box":[126,326,338,88],"fill":"reward_orange","radius":16},{"type":"text","id":"s08_ui_h_0","text":"Ganhe 8x pontos","box":[142,346,280,28],"style":"body_bold"},{"type":"text","id":"s08_ui_b_0","text":"Compre e pontue nas lojas parceiras","box":[142,434,300,68],"style":"body_small"},{"type":"rect","id":"s08_ui_btn_0","box":[142,520,150,38],"fill":"esfera_red","radius":19},{"type":"text","id":"s08_ui_btn_txt_0","text":"Ver oferta","box":[178,531,100,20],"style":"caption"},{"type":"rect","id":"s08_ui_1","box":[570,300,390,280],"fill":"paper","stroke_style":"rule","radius":20},{"type":"rect","id":"s08_ui_top_1","box":[596,326,338,88],"fill":"reward_blush","radius":16},{"type":"text","id":"s08_ui_h_1","text":"Use seus pontos","box":[612,346,280,28],"style":"body_bold"},{"type":"text","id":"s08_ui_b_1","text":"Troque por produtos, viagens ou cashback","box":[612,434,300,68],"style":"body_small"},{"type":"rect","id":"s08_ui_btn_1","box":[612,520,150,38],"fill":"esfera_red","radius":19},{"type":"text","id":"s08_ui_btn_txt_1","text":"Ver oferta","box":[648,531,100,20],"style":"caption"},{"type":"rect","id":"s08_ui_2","box":[1040,300,390,280],"fill":"paper","stroke_style":"rule","radius":20},{"type":"rect","id":"s08_ui_top_2","box":[1066,326,338,88],"fill":"accent_soft","radius":16},{"type":"text","id":"s08_ui_h_2","text":"Desconto na fatura","box":[1082,346,280,28],"style":"body_bold"},{"type":"text","id":"s08_ui_b_2","text":"Reduza o valor pago com seus pontos","box":[1082,434,300,68],"style":"body_small"},{"type":"rect","id":"s08_ui_btn_2","box":[1082,520,150,38],"fill":"esfera_red","radius":19},{"type":"text","id":"s08_ui_btn_txt_2","text":"Ver oferta","box":[1118,531,100,20],"style":"caption"},{"type":"text","id":"s08_note","text":"UI recommendation: high-legibility cards, fewer badges, stronger value hierarchy, and a single primary CTA per module.","box":[84,670,1120,68],"style":"subtitle"},{"type":"line","id":"slide_08_ui_system_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_08_ui_system_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_08_ui_system_footer_r","text":"08","box":[1470,846,50,22],"style":"footer","decorative":true},{"type":"text","id":"s08_ui_btn_label_refined_0","text":"Ver oferta","box":[165,530,110,20],"style":"ui_button"},{"type":"text","id":"s08_ui_btn_label_refined_1","text":"Ver oferta","box":[635,530,110,20],"style":"ui_button"},{"type":"text","id":"s08_ui_btn_label_refined_2","text":"Ver oferta","box":[1105,530,110,20],"style":"ui_button"}]}],"meta":{"layout":"cards"}},{"mode":"page","id":"slide_09_voice","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_09_voice_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_09_voice_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s09_eyebrow","text":"VOICE & MESSAGING","box":[80,80,330,28],"style":"eyebrow"},{"type":"text","id":"s09_title","text":"Esfera should sound useful, warm and direct","box":[80,130,860,70],"style":"title_l"},{"type":"rect","id":"s09_q","box":[110,275,1280,140],"fill":"paper","radius":14,"stroke_style":"rule"},{"type":"text","id":"s09_quote","text":"Before: ‘Acumule e resgate pontos.’\nAfter: ‘Transforme suas compras em vantagens reais, de um jeito simples.’","box":[150,315,1160,70],"style":"quote"},{"type":"text","id":"s09_h_0","text":"Functional copy","box":[100,500,340,28],"style":"body_bold"},{"type":"text","id":"s09_b_0","text":"Clarity first. Explain the value in one sentence.","box":[100,544,360,60],"style":"body_small"},{"type":"text","id":"s09_h_1","text":"Promotional copy","box":[570,500,340,28],"style":"body_bold"},{"type":"text","id":"s09_b_1","text":"Make the reward concrete: points, discount, miles, cashback.","box":[570,544,360,60],"style":"body_small"},{"type":"text","id":"s09_h_2","text":"Trust copy","box":[1040,500,340,28],"style":"body_bold"},{"type":"text","id":"s09_b_2","text":"Explain conditions cleanly. Reduce ambiguity, not energy.","box":[1040,544,360,60],"style":"body_small"},{"type":"line","id":"slide_09_voice_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_09_voice_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_09_voice_footer_r","text":"09","box":[1470,846,50,22],"style":"footer","decorative":true},{"type":"rect","id":"s09_do_chip","box":[112,655,190,42],"fill":"esfera_red","radius":21},{"type":"text","id":"s09_do_chip_text","text":"DO: concrete value","box":[142,668,140,18],"style":"pill_text"},{"type":"rect","id":"s09_avoid_chip","box":[332,655,220,42],"fill":"charcoal","radius":21},{"type":"text","id":"s09_avoid_chip_text","text":"AVOID: generic hype","box":[362,668,160,18],"style":"pill_text"}]}],"meta":{"layout":"quote"}},{"mode":"page","id":"slide_10_moments","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_10_moments_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_10_moments_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s10_eyebrow","text":"EXPERIENCE MOMENTS","box":[80,80,300,28],"style":"eyebrow"},{"type":"text","id":"s10_title","text":"Design the journey around the reward loop","box":[80,130,860,70],"style":"title_l"},{"type":"line","id":"s10_axis","from":[160,500],"to":[1440,500],"stroke_style":"rule_dark"},{"type":"rect","id":"s10_dot_0","box":[132,472,56,56],"fill":"esfera_red","radius":28},{"type":"text","id":"s10_num_0","text":"01","box":[142,488,38,18],"style":"caption"},{"type":"text","id":"s10_h_0","text":"Descobrir","box":[88,560,160,28],"style":"body_bold"},{"type":"text","id":"s10_b_0","text":"See relevant offers.","box":[88,602,190,46],"style":"body_small"},{"type":"rect","id":"s10_dot_1","box":[447,472,56,56],"fill":"esfera_red","radius":28},{"type":"text","id":"s10_num_1","text":"02","box":[457,488,38,18],"style":"caption"},{"type":"text","id":"s10_h_1","text":"Pontuar","box":[403,560,160,28],"style":"body_bold"},{"type":"text","id":"s10_b_1","text":"Understand how to earn.","box":[403,602,190,46],"style":"body_small"},{"type":"rect","id":"s10_dot_2","box":[762,472,56,56],"fill":"esfera_red","radius":28},{"type":"text","id":"s10_num_2","text":"03","box":[772,488,38,18],"style":"caption"},{"type":"text","id":"s10_h_2","text":"Acompanhar","box":[718,560,160,28],"style":"body_bold"},{"type":"text","id":"s10_b_2","text":"Track points and progress.","box":[718,602,190,46],"style":"body_small"},{"type":"rect","id":"s10_dot_3","box":[1077,472,56,56],"fill":"esfera_red","radius":28},{"type":"text","id":"s10_num_3","text":"04","box":[1087,488,38,18],"style":"caption"},{"type":"text","id":"s10_h_3","text":"Resgatar","box":[1033,560,160,28],"style":"body_bold"},{"type":"text","id":"s10_b_3","text":"Use points without friction.","box":[1033,602,190,46],"style":"body_small"},{"type":"line","id":"slide_10_moments_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_10_moments_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_10_moments_footer_r","text":"10","box":[1470,846,50,22],"style":"footer","decorative":true}]}],"meta":{"layout":"timeline"}},{"mode":"page","id":"slide_11_components","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_11_components_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_11_components_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s11_eyebrow","text":"COMPONENT GUIDANCE","box":[80,80,330,28],"style":"eyebrow"},{"type":"text","id":"s11_title","text":"Where the new system changes the most","box":[80,130,870,70],"style":"title_l"},{"type":"rect","id":"s11_hbg_0","box":[90,280,270,82],"fill":"reward_blush","stroke_style":"rule_dark"},{"type":"text","id":"s11_ht_0","text":"Component","box":[106,304,244,30],"style":"table_header"},{"type":"rect","id":"s11_hbg_1","box":[360,280,300,82],"fill":"reward_blush","stroke_style":"rule_dark"},{"type":"text","id":"s11_ht_1","text":"Current tendency","box":[376,304,274,30],"style":"table_header"},{"type":"rect","id":"s11_hbg_2","box":[660,280,370,82],"fill":"reward_blush","stroke_style":"rule_dark"},{"type":"text","id":"s11_ht_2","text":"New rule","box":[676,304,344,30],"style":"table_header"},{"type":"rect","id":"s11_hbg_3","box":[1030,280,370,82],"fill":"reward_blush","stroke_style":"rule_dark"},{"type":"text","id":"s11_ht_3","text":"Why it matters","box":[1046,304,344,30],"style":"table_header"},{"type":"rect","id":"s11_cbg_0_0","box":[90,362,270,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_0_0","text":"Hero banners","box":[106,380,246,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_0_1","box":[360,362,300,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_0_1","text":"Many promo messages","box":[376,380,276,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_0_2","box":[660,362,370,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_0_2","text":"One promise + one CTA","box":[676,380,346,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_0_3","box":[1030,362,370,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_0_3","text":"Improves scan speed","box":[1046,380,346,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_1_0","box":[90,444,270,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_1_0","text":"Offer cards","box":[106,462,246,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_1_1","box":[360,444,300,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_1_1","text":"Badge-heavy layouts","box":[376,462,276,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_1_2","box":[660,444,370,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_1_2","text":"Clear value hierarchy","box":[676,462,346,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_1_3","box":[1030,444,370,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_1_3","text":"Makes benefit legible","box":[1046,462,346,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_2_0","box":[90,526,270,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_2_0","text":"Points balance","box":[106,544,246,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_2_1","box":[360,526,300,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_2_1","text":"Functional counters","box":[376,544,276,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_2_2","box":[660,526,370,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_2_2","text":"Celebrate progress subtly","box":[676,544,346,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_2_3","box":[1030,526,370,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_2_3","text":"Creates retention loop","box":[1046,544,346,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_3_0","box":[90,608,270,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_3_0","text":"Checkout / redemption","box":[106,626,246,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_3_1","box":[360,608,300,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_3_1","text":"Dense instructions","box":[376,626,276,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_3_2","box":[660,608,370,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_3_2","text":"Step clarity + friction cues","box":[676,626,346,46],"style":"table_cell"},{"type":"rect","id":"s11_cbg_3_3","box":[1030,608,370,82],"fill":"paper","stroke_style":"rule"},{"type":"text","id":"s11_ct_3_3","text":"Reduces abandonment","box":[1046,626,346,46],"style":"table_cell"},{"type":"line","id":"slide_11_components_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_11_components_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_11_components_footer_r","text":"11","box":[1470,846,50,22],"style":"footer","decorative":true},{"type":"rect","id":"s11_tag_bg_0","box":[1225,414,132,22],"fill":"accent_soft","radius":11,"stroke_style":"rule"},{"type":"text","id":"s11_tag_text_0","text":"High impact","box":[1241,419,100,12],"style":"micro"},{"type":"rect","id":"s11_tag_bg_1","box":[1225,496,132,22],"fill":"accent_soft","radius":11,"stroke_style":"rule"},{"type":"text","id":"s11_tag_text_1","text":"High impact","box":[1241,501,100,12],"style":"micro"},{"type":"rect","id":"s11_tag_bg_2","box":[1225,578,132,22],"fill":"accent_soft","radius":11,"stroke_style":"rule"},{"type":"text","id":"s11_tag_text_2","text":"Medium impact","box":[1241,583,100,12],"style":"micro"},{"type":"rect","id":"s11_tag_bg_3","box":[1225,660,132,22],"fill":"accent_soft","radius":11,"stroke_style":"rule"},{"type":"text","id":"s11_tag_text_3","text":"High impact","box":[1241,665,100,12],"style":"micro"}]}],"meta":{"layout":"table"}},{"mode":"page","id":"slide_12_rollout","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_12_rollout_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_12_rollout_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s12_eyebrow","text":"ROLL OUT","box":[80,80,220,28],"style":"eyebrow"},{"type":"text","id":"s12_title","text":"How to adopt the new style guide","box":[80,130,780,70],"style":"title_l"},{"type":"rect","id":"s12_card_0","box":[90,340,300,280],"fill":"paper","stroke_style":"rule","radius":14},{"type":"text","id":"s12_a_0","text":"Phase 1","box":[114,372,200,22],"style":"label"},{"type":"text","id":"s12_b_0","text":"Brand foundation","box":[114,420,250,54],"style":"body_bold"},{"type":"text","id":"s12_c_0","text":"Palette, typography, logo rules, tone.","box":[114,494,240,84],"style":"body_small"},{"type":"rect","id":"s12_card_1","box":[460,340,300,280],"fill":"paper","stroke_style":"rule","radius":14},{"type":"text","id":"s12_a_1","text":"Phase 2","box":[484,372,200,22],"style":"label"},{"type":"text","id":"s12_b_1","text":"Product surfaces","box":[484,420,250,54],"style":"body_bold"},{"type":"text","id":"s12_c_1","text":"Home, offers, points balance, resgate.","box":[484,494,240,84],"style":"body_small"},{"type":"rect","id":"s12_card_2","box":[830,340,300,280],"fill":"paper","stroke_style":"rule","radius":14},{"type":"text","id":"s12_a_2","text":"Phase 3","box":[854,372,200,22],"style":"label"},{"type":"text","id":"s12_b_2","text":"Campaign system","box":[854,420,250,54],"style":"body_bold"},{"type":"text","id":"s12_c_2","text":"Templates for partners, sales and CRM.","box":[854,494,240,84],"style":"body_small"},{"type":"rect","id":"s12_card_3","box":[1200,340,300,280],"fill":"paper","stroke_style":"rule","radius":14},{"type":"text","id":"s12_a_3","text":"Phase 4","box":[1224,372,200,22],"style":"label"},{"type":"text","id":"s12_b_3","text":"Governance","box":[1224,420,250,54],"style":"body_bold"},{"type":"text","id":"s12_c_3","text":"Figma kit, QA checklist, design ops.","box":[1224,494,240,84],"style":"body_small"},{"type":"line","id":"slide_12_rollout_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_12_rollout_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_12_rollout_footer_r","text":"12","box":[1470,846,50,22],"style":"footer","decorative":true},{"type":"line","id":"s12_gate_line","from":[90,676],"to":[1390,676],"stroke_style":"dashed","decorative":true},{"type":"text","id":"s12_gate_note","text":"Gate: launch only after brand QA and product accessibility checks pass.","box":[96,704,780,28],"style":"body_small"}]}],"meta":{"layout":"roadmap"}},{"mode":"page","id":"slide_13_success","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_13_success_bg","box":[0,0,1600,900],"fill":"bg","decorative":true},{"type":"rect","id":"slide_13_success_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s13_eyebrow","text":"SUCCESS SIGNALS","box":[80,80,290,28],"style":"eyebrow"},{"type":"text","id":"s13_title","text":"Measure whether the brand system is working","box":[80,130,930,70],"style":"title_l"},{"type":"rect","id":"s13_m_0","box":[100,320,390,260],"fill":"paper","radius":14,"stroke_style":"rule"},{"type":"text","id":"s13_metric_0","text":"12%","box":[126,362,180,64],"style":"metric_big"},{"type":"text","id":"s13_lab_0","text":"+ scan clarity","box":[126,438,200,30],"style":"body_bold"},{"type":"text","id":"s13_desc_0","text":"Higher CTR on primary reward cards","box":[126,490,300,70],"style":"body_small"},{"type":"rect","id":"s13_m_1","box":[570,320,390,260],"fill":"paper","radius":14,"stroke_style":"rule"},{"type":"text","id":"s13_metric_1","text":"18%","box":[596,362,180,64],"style":"metric_big"},{"type":"text","id":"s13_lab_1","text":"+ trust","box":[596,438,200,30],"style":"body_bold"},{"type":"text","id":"s13_desc_1","text":"Lower confusion in redemption flows","box":[596,490,300,70],"style":"body_small"},{"type":"rect","id":"s13_m_2","box":[1040,320,390,260],"fill":"paper","radius":14,"stroke_style":"rule"},{"type":"text","id":"s13_metric_2","text":"22%","box":[1066,362,180,64],"style":"metric_big"},{"type":"text","id":"s13_lab_2","text":"+ desire","box":[1066,438,200,30],"style":"body_bold"},{"type":"text","id":"s13_desc_2","text":"More repeat visits to offers and points areas","box":[1066,490,300,70],"style":"body_small"},{"type":"line","id":"slide_13_success_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule","decorative":true,"opacity":0.6},{"type":"text","id":"slide_13_success_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer","decorative":true},{"type":"text","id":"slide_13_success_footer_r","text":"13","box":[1470,846,50,22],"style":"footer","decorative":true}]}],"meta":{"layout":"metrics"}},{"mode":"page","id":"slide_14_closing","canvas":{"size":[1600,900],"units":"px"},"rendering":{"coordinate_mode":"absolute","preserve_manual_line_breaks":true,"text":{"overflow":"clip","min_font_size":10}},"layers":[{"id":"base","z":0,"objects":[{"type":"rect","id":"slide_14_closing_bg","box":[0,0,1600,900],"fill":"charcoal","decorative":true},{"type":"rect","id":"slide_14_closing_brand_underscore_motif","box":[1358,74,102,10],"fill":"esfera_red","radius":5,"decorative":true,"opacity":0.95},{"type":"text","id":"s14_eyebrow","text":"THE ASK","box":[80,96,160,28],"style":"inverse_label"},{"type":"text","id":"s14_title","text":"Approve the reimagined Esfera brand system and design pilot","box":[80,176,1000,110],"style":"inverse_title"},{"type":"text","id":"s14_body","text":"Start with a style guide, then prove it in the highest-impact digital surfaces: home, offers, points balance and redemption.","box":[84,330,820,82],"style":"inverse_body"},{"type":"rect","id":"s14_panel","box":[82,500,620,170],"fill":"reward_blush","radius":14},{"type":"text","id":"s14_panel_h","text":"Immediate deliverables","box":[112,534,500,28],"style":"body_bold"},{"type":"rect","id":"s14_shape_1","box":[1080,180,280,280],"fill":"reward_orange","radius":140,"decorative":true,"opacity":0.9},{"type":"rect","id":"s14_shape_2","box":[1190,320,260,260],"fill":"esfera_red","radius":130,"decorative":true,"opacity":0.95},{"type":"rect","id":"s14_shape_3","box":[1040,530,190,190],"fill":"paper","radius":95,"decorative":true,"opacity":0.95},{"type":"line","id":"slide_14_closing_footer_rule","from":[80,830],"to":[1520,830],"stroke_style":"rule_dark","decorative":true,"opacity":0.6},{"type":"text","id":"slide_14_closing_footer_l","text":"Esfera Style Guide / Reimagined proposal","box":[80,846,440,22],"style":"footer_inverse","decorative":true},{"type":"text","id":"slide_14_closing_footer_r","text":"14","box":[1470,846,50,22],"style":"footer_inverse","decorative":true},{"type":"rect","id":"s14_check_0","box":[116,579,12,12],"fill":"esfera_red","radius":6},{"type":"text","id":"s14_check_text_0","text":"Brand guide","box":[138,575,280,18],"style":"body_small"},{"type":"rect","id":"s14_check_1","box":[116,601,12,12],"fill":"esfera_red","radius":6},{"type":"text","id":"s14_check_text_1","text":"UI kit","box":[138,597,280,18],"style":"body_small"},{"type":"rect","id":"s14_check_2","box":[116,623,12,12],"fill":"esfera_red","radius":6},{"type":"text","id":"s14_check_text_2","text":"Campaign templates","box":[138,619,280,18],"style":"body_small"},{"type":"rect","id":"s14_check_3","box":[116,645,12,12],"fill":"esfera_red","radius":6},{"type":"text","id":"s14_check_text_3","text":"Governance checklist","box":[138,641,280,18],"style":"body_small"}]}],"meta":{"layout":"closing"}}],"meta":{"brand_basis":{"note":"This is a proposed reimagined style guide, not an official existing brand manual.","public_signals_used":["Esfera wordmark pattern with red underscore/accent","Santander relationship and red brand equity","Rewards, points, offers, and discount ecosystem positioning"]},"status":"proposal deck template with editable content","refinement_pass":{"version":"2","changes":["Added brand underscore motif across slides.","Tuned warm palette and typography scale.","Added logo clearspace and Santander relationship guidance.","Improved CTA legibility and UI card hierarchy.","Added palette hex labels, voice chips, rollout gate and checklist closing."]},"improvement":{"finding":"deck is well-designed and renders correctly under a §3.7 text-fit renderer; the one systematic gap was label styles with no fit policy.","data_change":"added overflow:shrink_to_fit + min_font_size to 17 label/number styles that had none, so the reusable template cannot overflow on longer content (the cover kicker pill already did).","not_changed":"no text, geometry, palette, or layout altered; p11 component table left intact (its impact-badge pills would be lost by a naive table conversion); decorative compositions left as authored.","styles_made_fit_safe":["eyebrow","label","label_ink","num","inverse_label","footer","footer_inverse","hero_logo","hero_logo_red","metric_big","section_kicker","micro","micro_inverse","swatch_hex","pill_text","ui_button","logo_label"],"overlap_fix":"slide_14: removed leftover duplicate deliverables block (s14_panel_b) that overlapped the checkbox rows (s14_check_*) by ~25k px²; the four items remain as the styled checkbox list."},"fixes":["slide_14: removed orphan duplicate list 's14_panel_b' (stale combined text overlapping the bulleted s14_check_* items); widened 's14_panel_h' title box 260->500 so 'Immediate deliverables' no longer wraps into the first item."]}};

/* ============================================================ *
 *  Viewer chrome theme — a neutral graphite "light table" so the
 *  warm document reads with accurate color. Accent is used only as
 *  thin registration marks, never as large fills.
 * ============================================================ */
const UI = {
  bg: "#15171C",
  rail: "#0E1014",
  panel: "#1A1D23",
  panelAlt: "#20242B",
  hair: "#2B313A",
  hairSoft: "#22272E",
  hi: "#ECEEF1",
  mid: "#98A0AB",
  lo: "#5A626D",
  faint: "#3A4049",
  accent: "#E8553D",
  accentDim: "#B8412E",
  mono: "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace",
  sans: "'Space Grotesk', ui-sans-serif, system-ui, sans-serif",
};

const PRESET_CANVASES = {
  A3: [842, 1191],
  A4: [595, 842],
  A5: [419.5, 595.3],
  Letter: [612, 792],
  Legal: [612, 1008],
  Tabloid: [792, 1224],
  "deck-16x9": [1920, 1080],
  "deck-4x3": [1024, 768],
  square: [1080, 1080],
  phone: [390, 844],
  tablet: [834, 1112],
  web: [1280, 800],
};

/* ============================================================ *
 *  Resolver engine — turns FrameGraph tokens/objects into CSS.
 *  Pure functions, given the whole `doc` for token lookups.
 * ============================================================ */
function toPx(v) {
  if (v == null) return 0;
  if (typeof v === "number") return v;
  const m = /^(-?\d+(?:\.\d+)?)(pt|px|mm|in|cm|%|fr)?$/.exec(String(v).trim());
  if (!m) return 0;
  const n = parseFloat(m[1]);
  switch (m[2] || "px") {
    case "pt": return (n * 96) / 72;
    case "in": return n * 96;
    case "cm": return (n * 96) / 2.54;
    case "mm": return (n * 96) / 25.4;
    default: return n; // px, %, fr -> caller context (treated as px here)
  }
}

function hexToRgba(hex, a) {
  let h = hex.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  if (h.length === 8) h = h.slice(0, 6); // drop existing alpha, we override
  const n = parseInt(h, 16);
  if (Number.isNaN(n)) return hex;
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  return `rgba(${r},${g},${b},${a})`;
}
function withAlpha(color, a) {
  if (typeof color === "string" && color[0] === "#") return hexToRgba(color, a);
  return color; // named / rgba -> leave as-is
}

function resolveColor(doc, c) {
  if (c == null) return "transparent";
  const colors = doc?.defs?.tokens?.colors || {};
  if (typeof c === "string") return colors[c] != null ? resolveColor(doc, colors[c]) : c;
  return "transparent";
}

function resolveFont(doc, name) {
  const fonts = doc?.defs?.tokens?.fonts || {};
  const def = fonts[name];
  const stack = (d) => {
    if (!d) return null;
    if (typeof d === "string") return d;
    const fam = d.family ? `"${d.family}"` : "";
    const fb = (d.fallback || []).join(", ");
    return [fam, fb].filter(Boolean).join(", ");
  };
  return stack(def) || name || "system-ui, sans-serif";
}

function resolveTextStyle(doc, ref) {
  const ts = doc?.defs?.tokens?.text_styles || {};
  const styles = doc?.defs?.tokens?.styles || {};
  const raw = typeof ref === "string" ? (ts[ref] || styles[ref] || {}) : (ref || {});
  const classNames = typeof raw.class === "string" ? [raw.class] : (raw.class || raw.class_ || []);
  const merged = {};
  classNames.forEach((name) => Object.assign(merged, ts[name] || styles[name] || {}));
  Object.assign(merged, raw);
  return {
    ...merged,
    font: merged.font != null ? merged.font : merged.font_family,
    size: merged.size != null ? toPx(merged.size) : toPx(merged.font_size),
    weight: merged.weight != null ? merged.weight : (merged.font_weight != null ? merged.font_weight : (merged.bold ? 700 : undefined)),
    italic: merged.italic != null ? merged.italic : merged.font_style === "italic",
    align: merged.align != null ? merged.align : merged.text_align,
    v_align: merged.v_align != null ? merged.v_align : merged.vertical_align,
    wrap: merged.wrap != null ? merged.wrap : ["wrap", "balance", "pretty"].includes(merged.text_wrap),
    line_height: merged.line_height != null ? (typeof merged.line_height === "string" && /px|pt|in|cm|mm/.test(merged.line_height) ? `${toPx(merged.line_height)}px` : merged.line_height) : undefined,
  };
}

function resolveStyle(doc, ref) {
  return resolveTextStyle(doc, ref);
}

// 2.2.0: stroke is PAINT-ONLY (a Paint) and geometry lives in `stroke_style`
// (a named Style with CSS-named stroke_width / stroke_dasharray / stroke_linecap /
// stroke_linejoin). `geomRef` is the object's stroke_style (token name or inline
// Style); `paint` is the object's paint-only `stroke`. Both old {color,width,dash}
// bundles and the new split form are accepted, so old and migrated docs both render.
function resolveStroke(doc, geomRef, paint) {
  const ss = doc?.defs?.tokens?.stroke_styles || {};
  // resolve the geometry bundle (a Style or legacy bundle)
  let st = null;
  if (geomRef != null) {
    st = typeof geomRef === "string" ? (ss[geomRef] != null ? ss[geomRef] : { stroke: geomRef }) : geomRef;
  }
  // a legacy inline bundle may arrive as `paint` (old `stroke:{color,width,dash}`)
  if (st == null && paint != null && typeof paint === "object") { st = paint; paint = null; }
  if (st == null && paint != null) { st = { stroke: paint }; paint = null; }
  if (st == null) return null;
  if (typeof st === "string") st = { stroke: st };

  // paint: new `stroke`/`fill`-style key, else legacy `color`
  let paintVal = paint != null ? paint : (st.stroke != null ? st.stroke : st.color);
  if (paintVal === "none") return null;
  // a gradient/pattern paint object isn't a CSS border colour — fall back gracefully
  const color = (paintVal != null && typeof paintVal === "object")
    ? resolveColor(doc, "#888") : resolveColor(doc, paintVal);

  // dasharray: new stroke_dasharray (array | "none") else legacy dash
  let dash = st.stroke_dasharray != null ? st.stroke_dasharray : st.dash;
  if (dash === "none" || (Array.isArray(dash) && dash.length === 0)) dash = null;

  const px = (v) => (typeof v === "string" ? (toPx(v) ?? parseFloat(v)) : v);
  return {
    color,
    width: st.stroke_width != null ? px(st.stroke_width) : (st.width != null ? st.width : 1),
    dash: Array.isArray(dash) ? dash.map(px) : (dash || null),
    linecap: st.stroke_linecap || st.linecap || "butt",
    linejoin: st.stroke_linejoin || st.linejoin || "miter",
    arrowStart: !!st.arrow_start,
    arrowEnd: !!st.arrow_end,
    opacity: st.opacity != null ? st.opacity : 1,
  };
}

function resolveFill(doc, fill) {
  if (fill == null) return "transparent";
  const fillStyles = doc?.defs?.tokens?.fill_styles || {};
  if (typeof fill === "string") {
    if (fillStyles[fill]) return resolveFill(doc, fillStyles[fill]);
    return resolveColor(doc, fill);
  }
  if (fill.kind === "linear" || fill.kind === "radial" || fill.kind === "conic") {
    // 2.2.0: stops use `position` (Length | %); accept legacy 0..1 `offset` too
    const stopPos = (s) => {
      const p = s.position != null ? s.position : s.offset;
      if (p == null) return "";
      if (typeof p === "string") return " " + p;            // "50%" / "10px"
      return " " + (p <= 1 ? Math.round(p * 100) : Math.round(p)) + "%";
    };
    const stops = (fill.stops || [])
      .map((s) => `${resolveColor(doc, s.color)}${stopPos(s)}`)
      .join(", ");
    // angle may be a number (deg) or a CSS string like "135deg"
    const ang = (v, d) => (v == null ? d : (typeof v === "number" ? `${v}deg` : v));
    if (fill.kind === "linear") return `linear-gradient(${ang(fill.angle, "180deg")}, ${stops})`;
    if (fill.kind === "conic") return `conic-gradient(from ${ang(fill.from, "0deg")}, ${stops})`;
    return `radial-gradient(circle, ${stops})`;
  }
  if (fill.kind === "pattern") {
    const stroke = resolveStroke(doc, fill.stroke || "#888");
    const bg = resolveColor(doc, fill.background || "transparent");
    const sp = toPx(fill.spacing) || 8;
    const col = stroke.color;
    const ang = fill.angle != null ? fill.angle : 45;
    if (fill.pattern === "dots")
      return `radial-gradient(${col} 1px, ${bg} 1px) 0 0 / ${sp}px ${sp}px`;
    if (fill.pattern === "cross_hatch" || fill.pattern === "grid")
      return `repeating-linear-gradient(${ang}deg, ${col} 0 1px, transparent 1px ${sp}px), repeating-linear-gradient(${ang + 90}deg, ${col} 0 1px, ${bg} 1px ${sp}px)`;
    return `repeating-linear-gradient(${ang}deg, ${col} 0 1px, ${bg} 1px ${sp}px)`;
  }
  return "transparent";
}

function cssLength(v) {
  if (v == null) return undefined;
  if (typeof v === "number") return `${v}px`;
  if (Array.isArray(v)) return v.map(cssLength).filter(Boolean).join(" ");
  return String(v);
}

function camelCss(prop) {
  return String(prop).trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase());
}

function parseCssDeclarations(cssText) {
  if (!cssText || typeof cssText !== "string") return {};
  const out = {};
  for (const part of cssText.split(";")) {
    const idx = part.indexOf(":");
    if (idx <= 0) continue;
    const key = camelCss(part.slice(0, idx));
    const val = part.slice(idx + 1).trim();
    if (key && val) out[key] = val;
  }
  return out;
}

function cssEdges(v) {
  if (v == null) return undefined;
  if (typeof v === "number" || typeof v === "string") return cssLength(v);
  if (Array.isArray(v)) return v.map(cssLength).join(" ");
  if (typeof v === "object") {
    return [v.top, v.right, v.bottom, v.left].map((x) => cssLength(x ?? 0)).join(" ");
  }
  return undefined;
}

function cssBorder(doc, border) {
  if (!border) return undefined;
  if (typeof border === "string") return border;
  if (typeof border !== "object") return undefined;
  const width = cssLength(border.width ?? border.stroke_width ?? 1);
  const style = border.style || (border.stroke_dasharray ? "dashed" : "solid");
  const color = resolveColor(doc, border.color ?? border.stroke ?? "currentColor");
  return [width, style, color].filter(Boolean).join(" ");
}

function cssTextDecoration(doc, value) {
  if (!value || typeof value === "string") return value;
  const line = Array.isArray(value.line) ? value.line.join(" ") : value.line;
  const color = value.color ? resolveColor(doc, value.color) : undefined;
  return [line, value.style, color, cssLength(value.thickness)].filter(Boolean).join(" ");
}

function cssShadow(doc, shadow) {
  if (!shadow || shadow === "none") return shadow;
  const list = Array.isArray(shadow) ? shadow : [shadow];
  return list.map((s) => {
    if (typeof s === "string") return s;
    const inset = s.inset ? "inset " : "";
    const x = cssLength(s.offset_x ?? s.x ?? 0);
    const y = cssLength(s.offset_y ?? s.y ?? 0);
    const blur = cssLength(s.blur ?? 0);
    const spread = s.spread != null ? ` ${cssLength(s.spread)}` : "";
    const color = resolveColor(doc, s.color || "rgba(0,0,0,.25)");
    return `${inset}${x} ${y} ${blur}${spread} ${color}`;
  }).join(", ");
}

function cssFilter(fn) {
  if (!fn || fn === "none") return fn;
  const list = Array.isArray(fn) ? fn : [fn];
  return list.map((f) => {
    if (typeof f === "string") return f;
    const name = f.fn || f.kind || f.name;
    const value = f.value ?? f.amount ?? "";
    return name ? `${name}(${value})` : "";
  }).filter(Boolean).join(" ");
}

function cssPoint(point) {
  return Array.isArray(point) ? point.map(cssLength).join(" ") : point;
}

function cssClipPath(clip) {
  if (!clip || typeof clip === "string") return clip;
  const shape = clip.shape;
  const args = clip.args || {};
  if (shape === "inset") {
    return `inset(${[args.top, args.right, args.bottom, args.left].map((v) => cssLength(v ?? 0)).join(" ")})`;
  }
  if (shape === "circle") {
    const r = cssLength(args.radius ?? args.r ?? "50%");
    const at = cssPoint(args.at ?? args.center);
    return `circle(${[r, at ? `at ${at}` : ""].filter(Boolean).join(" ")})`;
  }
  if (shape === "ellipse") {
    const rx = cssLength(args.rx ?? args.radius_x ?? "50%");
    const ry = cssLength(args.ry ?? args.radius_y ?? "50%");
    const at = cssPoint(args.at ?? args.center);
    return `ellipse(${[`${rx} ${ry}`, at ? `at ${at}` : ""].filter(Boolean).join(" ")})`;
  }
  if (shape === "polygon" && Array.isArray(args.points)) {
    return `polygon(${args.points.map(cssPoint).join(", ")})`;
  }
  if (shape === "path" && args.d) {
    return `path("${String(args.d).replace(/"/g, '\\"')}")`;
  }
  return shape ? `${shape}()` : undefined;
}

function cssTransform(tx) {
  if (!tx || tx === "none") return tx;
  if (typeof tx === "string") return tx;
  const list = Array.isArray(tx) ? tx : [tx];
  return list.map((t) => {
    if (typeof t === "string") return t;
    const fn = t.fn || t.kind || t.name;
    const args = Array.isArray(t.args) ? t.args : [t.value ?? t.x, t.y].filter((x) => x != null);
    return fn ? `${fn}(${args.join(", ")})` : "";
  }).filter(Boolean).join(" ");
}

function styleToCss(doc, ref, opts = {}) {
  const st = resolveStyle(doc, ref);
  const css = {};
  if (st.visibility) css.visibility = st.visibility;
  if (st.z_index != null) css.zIndex = st.z_index;
  if (st.opacity != null) css.opacity = st.opacity;
  if (st.mix_blend_mode) css.mixBlendMode = st.mix_blend_mode;
  if (st.isolation) css.isolation = st.isolation;
  if (st.box_shadow) css.boxShadow = cssShadow(doc, st.box_shadow);
  if (st.filter) css.filter = cssFilter(st.filter);
  if (st.backdrop_filter) css.backdropFilter = cssFilter(st.backdrop_filter);
  if (st.transform) css.transform = cssTransform(st.transform);
  if (st.transform_origin) css.transformOrigin = Array.isArray(st.transform_origin) ? st.transform_origin.map(cssLength).join(" ") : st.transform_origin;
  if (st.transform_box) css.transformBox = st.transform_box;
  if (st.perspective != null) css.perspective = cssLength(st.perspective);
  if (st.clip_path) css.clipPath = cssClipPath(st.clip_path);
  if (st.mask) css.mask = typeof st.mask === "string" ? st.mask : undefined;
  if (st.padding != null) css.padding = cssEdges(st.padding);
  if (st.margin != null) css.margin = cssEdges(st.margin);
  for (const [key, cssKey] of [
    ["width", "width"], ["height", "height"], ["min_width", "minWidth"], ["max_width", "maxWidth"],
    ["min_height", "minHeight"], ["max_height", "maxHeight"],
  ]) {
    if (st[key] != null) css[cssKey] = cssLength(st[key]);
  }
  if (st.box_sizing) css.boxSizing = st.box_sizing;
  const radius = st.border_radius ?? st.radius;
  if (radius != null) css.borderRadius = cssEdges(radius);
  if (st.background) css.background = typeof st.background === "string" ? resolveColor(doc, st.background) : resolveFill(doc, st.background);
  if (st.background_color) css.backgroundColor = resolveColor(doc, st.background_color);
  if (st.background_image) css.backgroundImage = resolveFill(doc, st.background_image);
  if (st.background_position) css.backgroundPosition = st.background_position;
  if (st.background_size) css.backgroundSize = st.background_size;
  if (st.background_repeat) css.backgroundRepeat = st.background_repeat;
  if (st.background_clip) css.backgroundClip = st.background_clip;
  if (st.background_origin) css.backgroundOrigin = st.background_origin;
  if (st.background_blend_mode) css.backgroundBlendMode = st.background_blend_mode;
  if (st.border) css.border = cssBorder(doc, st.border);
  for (const [key, cssKey] of [["border_top", "borderTop"], ["border_right", "borderRight"], ["border_bottom", "borderBottom"], ["border_left", "borderLeft"]]) {
    if (st[key]) css[cssKey] = cssBorder(doc, st[key]);
  }
  if (st.outline) css.outline = cssBorder(doc, st.outline);
  if (st.outline_offset != null) css.outlineOffset = cssLength(st.outline_offset);
  if (st.overflow) css.overflow = st.overflow === "shrink_to_fit" ? "hidden" : st.overflow;
  if (st.overflow_x) css.overflowX = st.overflow_x;
  if (st.overflow_y) css.overflowY = st.overflow_y;
  if (st.fill) css.fill = resolveFill(doc, st.fill);
  if (st.fill_rule) css.fillRule = st.fill_rule;
  if (st.stroke) css.stroke = resolveFill(doc, st.stroke);
  if (st.stroke_width != null) css.strokeWidth = cssLength(st.stroke_width);
  if (st.stroke_dasharray != null) css.strokeDasharray = Array.isArray(st.stroke_dasharray) ? st.stroke_dasharray.map(cssLength).join(" ") : st.stroke_dasharray;
  if (st.stroke_dashoffset != null) css.strokeDashoffset = cssLength(st.stroke_dashoffset);
  if (st.stroke_linecap) css.strokeLinecap = st.stroke_linecap;
  if (st.stroke_linejoin) css.strokeLinejoin = st.stroke_linejoin;
  if (st.stroke_miterlimit != null) css.strokeMiterlimit = st.stroke_miterlimit;
  if (st.paint_order) css.paintOrder = st.paint_order;
  if (st.vector_effect) css.vectorEffect = st.vector_effect;
  if (opts.text) {
    if (st.color) css.color = resolveColor(doc, st.color);
    if (st.font) css.fontFamily = resolveFont(doc, st.font);
    if (st.size) css.fontSize = st.size;
    if (st.weight != null) css.fontWeight = st.weight;
    if (st.italic != null) css.fontStyle = st.italic ? "italic" : "normal";
    if (st.font_stretch) css.fontStretch = st.font_stretch;
    if (st.font_variant) css.fontVariant = st.font_variant;
    if (st.align) css.textAlign = st.align;
    if (st.text_align_last) css.textAlignLast = st.text_align_last;
    if (st.line_height != null) css.lineHeight = st.line_height;
    if (st.letter_spacing != null) css.letterSpacing = cssLength(st.letter_spacing);
    if (st.word_spacing != null) css.wordSpacing = cssLength(st.word_spacing);
    if (st.text_transform) css.textTransform = st.text_transform;
    if (st.text_decoration) css.textDecoration = cssTextDecoration(doc, st.text_decoration);
    if (st.text_indent != null) css.textIndent = cssLength(st.text_indent);
    if (st.text_shadow) css.textShadow = cssShadow(doc, st.text_shadow);
    if (st.font_variant_caps) css.fontVariantCaps = st.font_variant_caps;
    if (st.font_variant_numeric) css.fontVariantNumeric = st.font_variant_numeric;
    if (st.font_variant_ligatures) css.fontVariantLigatures = st.font_variant_ligatures;
    if (st.font_feature_settings) css.fontFeatureSettings = st.font_feature_settings;
    if (st.font_variation_settings) css.fontVariationSettings = st.font_variation_settings;
    if (st.font_kerning) css.fontKerning = st.font_kerning;
    if (st.hyphens) css.hyphens = st.hyphens;
    if (st.hanging_punctuation) css.hangingPunctuation = st.hanging_punctuation;
    if (st.hyphenate_character) css.hyphenateCharacter = st.hyphenate_character;
    if (st.hyphenate_limit_chars) css.hyphenateLimitChars = st.hyphenate_limit_chars;
    if (st.white_space) css.whiteSpace = st.white_space;
    if (st.word_break) css.wordBreak = st.word_break;
    if (st.overflow_wrap) css.overflowWrap = st.overflow_wrap;
    if (st.text_wrap) css.textWrap = st.text_wrap;
    if (st.text_overflow) css.textOverflow = st.text_overflow;
    if (st.line_clamp != null || st.max_lines != null) {
      css.display = "-webkit-box";
      css.WebkitBoxOrient = "vertical";
      css.WebkitLineClamp = st.line_clamp ?? st.max_lines;
      css.overflow = "hidden";
    }
    if (st.tab_size != null) css.tabSize = st.tab_size;
    if (st.writing_mode) css.writingMode = st.writing_mode;
    if (st.direction) css.direction = st.direction;
    if (st.unicode_bidi) css.unicodeBidi = st.unicode_bidi;
  }
  return { ...css, ...parseCssDeclarations(st.css) };
}

function canvasOf(doc, page) {
  const masters = doc?.defs?.masters || {};
  const master = page?.master ? masters[page.master] : null;
  const raw = page?.canvas || master?.canvas || doc?.targets?.[0]?.canvas || { size: [1600, 900] };
  const c = Array.isArray(raw) ? raw : (typeof raw === "string" ? (PRESET_CANVASES[raw] || [1600, 900]) : (raw.size || PRESET_CANVASES[raw.preset] || [1600, 900]));
  return { w: toPx(c[0]), h: toPx(c[1]) };
}

function rotationStyle(rot, box) {
  if (rot == null) return {};
  if (typeof rot === "number") return { transform: `rotate(${rot}deg)` };
  const angle = rot.angle || 0;
  if (rot.center && box) {
    const ox = rot.center[0] - box[0];
    const oy = rot.center[1] - box[1];
    return { transform: `rotate(${angle}deg)`, transformOrigin: `${ox}px ${oy}px` };
  }
  return { transform: `rotate(${angle}deg)` };
}

// id -> box registry for anchor refs (best effort; per page)
function buildRegistry(page) {
  const reg = {};
  const visit = (o) => {
    if (!o || typeof o !== "object") return;
    if (o.id && o.box) reg[o.id] = o.box.map(toPx);
    (o.children || []).forEach(visit);
  };
  (page.layers || []).forEach((l) => (l.objects || []).forEach(visit));
  return reg;
}
function anchorPoint(a, reg) {
  if (Array.isArray(a)) return [toPx(a[0]), toPx(a[1])];
  if (a && typeof a === "object" && a.ref && reg[a.ref]) {
    const [x, y, w, h] = reg[a.ref];
    return [x + w / 2, y + h / 2]; // center; ports not modelled
  }
  return [0, 0];
}

/* ============================================================ *
 *  FitText — implements overflow: shrink_to_fit with min_font_size
 * ============================================================ */
function FitText({ children, style, baseStyle, width, height, active }) {
  const ref = useRef(null);
  const base = style.size || 16;
  const min = style.min_font_size != null ? style.min_font_size : base;
  const wrap = !!style.wrap;
  const [size, setSize] = useState(base);

  useLayoutEffect(() => {
    if (!active) { setSize(base); return; }
    const node = ref.current;
    if (!node) return;
    const fits = (fs) => {
      node.style.fontSize = fs + "px";
      if (wrap) return node.scrollHeight <= Math.ceil(height) + 1 && node.scrollWidth <= Math.ceil(width) + 1;
      return node.scrollWidth <= Math.ceil(width) + 1;
    };
    let best;
    if (fits(base)) best = base;
    else {
      let lo = min, hi = base; best = min;
      for (let i = 0; i < 16 && lo <= hi; i++) {
        const mid = Math.round(((lo + hi) / 2) * 100) / 100;
        if (fits(mid)) { best = mid; lo = mid + 0.25; }
        else hi = mid - 0.25;
      }
    }
    node.style.fontSize = "";
    setSize(best);
  }, [children, base, min, width, height, active, wrap]);

  return (
    <div ref={ref} style={{ ...baseStyle, fontSize: size,
      width: wrap ? "100%" : "max-content",
      whiteSpace: wrap ? "pre-wrap" : "pre" }}>
      {children}
    </div>
  );
}

/* ============================================================ *
 *  Object renderers
 * ============================================================ */
function RectObj({ doc, o }) {
  const box = (o.box || [0, 0, 0, 0]).map(toPx);
  const [x, y, w, h] = box;
  const radius = o.radius != null ? toPx(o.radius) : 0;
  const stroke = resolveStroke(doc, o.stroke_style, o.stroke);   // 2.2.0: geometry from stroke_style, paint from stroke
  let bg = resolveFill(doc, o.fill);
  if (typeof o.fill === "string" && o.fill_opacity != null && o.fill_opacity < 1)
    bg = withAlpha(resolveColor(doc, o.fill), o.fill_opacity);
  const st = {
    position: "absolute", left: x, top: y, width: w, height: h,
    background: bg, borderRadius: radius, boxSizing: "border-box",
    opacity: o.opacity != null ? o.opacity : 1,
    ...styleToCss(doc, o.style),
    ...rotationStyle(o.rotation, box),
  };
  if (stroke) {
    const col = o.stroke_opacity != null ? withAlpha(stroke.color, o.stroke_opacity) : stroke.color;
    st.border = `${stroke.width}px ${stroke.dash ? "dashed" : "solid"} ${col}`;
  }
  return <div data-framegraph-object={o.id || ""} data-framegraph-type="rect" style={st} />;
}

function TextObj({ doc, o, active }) {
  const box = (o.box || [0, 0, 0, 0]).map(toPx);
  const [x, y, w, h] = box;
  const style = resolveTextStyle(doc, o.style);
  const fontFamily = resolveFont(doc, style.font);
  const color = style.color != null ? resolveColor(doc, style.color) : "#181211";
  const align = style.align || "left";
  const vAlign = style.v_align || "top";
  const justify = vAlign === "middle" ? "center" : vAlign === "bottom" ? "flex-end" : "flex-start";
  const overflow = style.overflow || "visible";
  const lineClamp = style.line_clamp;

  const baseStyle = {
    fontFamily,
    fontWeight: style.weight != null ? style.weight : 400,
    color,
    lineHeight: style.line_height != null ? style.line_height : 1.2,
    textAlign: align,
    fontStyle: style.italic ? "italic" : "normal",
    ...styleToCss(doc, o.style, { text: true }),
  };
  if (lineClamp) {
    Object.assign(baseStyle, {
      display: "-webkit-box", WebkitLineClamp: lineClamp,
      WebkitBoxOrient: "vertical", overflow: "hidden",
    });
  }
  if (style.text_overflow === "ellipsis" && !style.wrap) {
    Object.assign(baseStyle, { overflow: "hidden", textOverflow: "ellipsis" });
  }

  const content = o.spans
    ? o.spans.map((sp, i) => {
        if (typeof sp === "string" || typeof sp === "number") return <React.Fragment key={i}>{sp}</React.Fragment>;
        const ss = sp.style ? resolveTextStyle(doc, sp.style) : {};
        return (
          <span key={i} data-framegraph-span={sp.id || i} style={{
            ...styleToCss(doc, sp.style, { text: true }),
            fontWeight: ss.weight,
            fontStyle: ss.italic ? "italic" : undefined,
            color: ss.color ? resolveColor(doc, ss.color) : undefined,
            fontFamily: ss.font ? resolveFont(doc, ss.font) : undefined,
            fontSize: ss.size || undefined,
            lineHeight: ss.line_height || undefined,
            textDecoration: ss.text_decoration || undefined,
            textTransform: ss.text_transform || undefined,
          }}>{textContent(sp)}</span>
        );
      })
    : (o.text != null ? o.text : (o.field != null ? `{${typeof o.field === "string" ? o.field : "field"}}` : ""));

  const wrapStyle = {
    position: "absolute", left: x, top: y, width: w, height: h,
    display: "flex", flexDirection: "column", justifyContent: justify,
    overflow: overflow === "visible" ? "visible" : "hidden",
    opacity: o.opacity != null ? o.opacity : 1,
    ...styleToCss(doc, o.style),
    ...rotationStyle(o.rotation, box),
  };

  const useFit = overflow === "shrink_to_fit";
  return (
    <div data-framegraph-object={o.id || ""} data-framegraph-type="text" style={wrapStyle}>
      {useFit ? (
        <FitText style={style} baseStyle={baseStyle} width={w} height={h} active={active}>
          {content}
        </FitText>
      ) : (
        <div style={{ ...baseStyle, fontSize: style.size || 16, width: "100%",
          whiteSpace: style.wrap ? "pre-wrap" : "pre" }}>
          {content}
        </div>
      )}
    </div>
  );
}

function VectorObj({ doc, o, cw, ch, reg }) {
  const fill = o.fill != null ? resolveFill(doc, o.fill) : "none";
  const hasFill = o.fill != null && o.fill !== "none" && fill !== "none" && fill !== "transparent";
  const stroke = resolveStroke(doc, o.stroke_style, o.stroke) || (hasFill ? null : { color: "#000", width: 1 });   // 2.2.0 split form
  const op = o.opacity != null ? o.opacity : 1;
  const mid = o.id ? o.id.replace(/[^a-zA-Z0-9_-]/g, "_") : Math.random().toString(36).slice(2);
  const arrow = stroke && (stroke.arrowStart || stroke.arrowEnd);
  const dash = stroke?.dash ? stroke.dash.join(" ") : undefined;
  const common = {
    "data-framegraph-vector": o.id || "",
    stroke: stroke?.color || "none", strokeWidth: stroke?.width, strokeDasharray: dash,
    strokeLinecap: stroke?.linecap, strokeLinejoin: stroke?.linejoin,
    strokeOpacity: o.stroke_opacity != null ? o.stroke_opacity : stroke?.opacity,
    fill, fillOpacity: o.fill_opacity,
    markerEnd: stroke?.arrowEnd ? `url(#${mid}-ah)` : undefined,
    markerStart: stroke?.arrowStart ? `url(#${mid}-ah)` : undefined,
  };

  let shape = null;
  if (o.type === "line") {
    const [x1, y1] = anchorPoint(o.from, reg);
    const [x2, y2] = anchorPoint(o.to, reg);
    shape = <line x1={x1} y1={y1} x2={x2} y2={y2} {...common} />;
  } else if (o.type === "polyline") {
    const pts = (o.points || []).map((p) => `${toPx(p[0])},${toPx(p[1])}`).join(" ");
    shape = o.closed
      ? <polygon points={pts} {...common} />
      : <polyline points={pts} {...common} fill={fill === "none" ? "none" : fill} />;
  } else if (o.type === "polygon") {
    const pts = (o.points || []).map((p) => `${toPx(p[0])},${toPx(p[1])}`).join(" ");
    shape = <polygon points={pts} {...common} />;
  } else if (o.type === "path") {
    shape = <path d={o.d} {...common} />;
  } else if (o.type === "ellipse") {
    const c = o.center || [0, 0];
    shape = <ellipse cx={toPx(c[0])} cy={toPx(c[1])} rx={o.rx} ry={o.ry} {...common} />;
  } else if (o.type === "circle") {
    const c = o.center || [0, 0];
    shape = <circle cx={toPx(c[0])} cy={toPx(c[1])} r={toPx(o.r || o.radius)} {...common} />;
  }

  return (
    <svg width={cw} height={ch} viewBox={`0 0 ${cw} ${ch}`}
      style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none", opacity: op }}>
      {arrow && (
        <defs>
          <marker id={`${mid}-ah`} markerWidth="10" markerHeight="10" refX="8" refY="3"
            orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L8,3 L0,6 z" fill={stroke?.color || "#000"} />
          </marker>
        </defs>
      )}
      {shape}
    </svg>
  );
}

function IconObj({ doc, o }) {
  const box = (o.box || [0, 0, 0, 0]).map(toPx);
  const [x, y, w, h] = box;
  const gmap = doc?.defs?.tokens?.glyph_map || {};
  const glyph = gmap[o.glyph] != null ? gmap[o.glyph] : o.glyph;
  const size = typeof o.size === "number" ? o.size : Math.min(w, h) || 24;
  return (
    <div style={{
      position: "absolute", left: x, top: y, width: w, height: h,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: resolveFont(doc, o.font), fontSize: size,
      color: resolveColor(doc, o.color), lineHeight: 1,
      opacity: o.opacity != null ? o.opacity : 1, ...rotationStyle(o.rotation, box),
    }}>{glyph}</div>
  );
}

function GroupObj({ doc, o, cw, ch, active }) {
  const box = o.box ? o.box.map(toPx) : null;
  const layout = o.layout;
  const st = { position: "absolute", opacity: o.opacity != null ? o.opacity : 1 };
  if (box) Object.assign(st, { left: box[0], top: box[1], width: box[2], height: box[3] });
  else Object.assign(st, { left: 0, top: 0, width: cw, height: ch });
  const isCellLayout = layout && ["row", "column", "grid"].includes(layout.kind);
  if (layout && (layout.kind === "row" || layout.kind === "column")) {
    Object.assign(st, {
      display: "flex",
      flexDirection: layout.kind === "row" ? "row" : "column",
      gap: toPx(layout.gap) || 0,
      alignItems: layout.align === "center" ? "center" : layout.align === "end" ? "flex-end"
        : layout.align === "stretch" ? "stretch" : "flex-start",
      padding: layout.padding ? layout.padding.map(toPx).join("px ") + "px" : undefined,
    });
  } else if (layout?.kind === "grid") {
    const cols = Math.max(1, Number(layout.columns || 1));
    const firstBox = (o.children?.[0]?.box || [0, 0, box?.[2] || cw, box?.[3] || ch]).map(toPx);
    Object.assign(st, {
      display: "grid",
      gridTemplateColumns: `repeat(${cols}, ${firstBox[2]}px)`,
      gridAutoRows: `${firstBox[3]}px`,
      gap: toPx(layout.gap) || 0,
      alignContent: layout.align_content || "start",
      justifyContent: layout.justify_content || "start",
      padding: layout.padding ? layout.padding.map(toPx).join("px ") + "px" : undefined,
    });
  }
  Object.assign(st, styleToCss(doc, o.style));
  Object.assign(st, rotationStyle(o.rotation, box || [0, 0, 0, 0]));
  const childCw = box ? box[2] : cw;
  const childCh = box ? box[3] : ch;
  const reg = {};
  const renderChild = (c, i) => {
    if (!isCellLayout) {
      return <RenderObject key={c.id || i} doc={doc} o={c} cw={childCw} ch={childCh} reg={reg} active={active} />;
    }
    const childBox = (c.box || [0, 0, childCw, childCh]).map(toPx);
    const cellW = childBox[2] || childCw;
    const cellH = childBox[3] || childCh;
    const localChild = { ...c, box: [0, 0, cellW, cellH] };
    return (
      <div key={c.id || i} style={{ position: "relative", width: cellW, height: cellH, flex: "0 0 auto" }}>
        <RenderObject doc={doc} o={localChild} cw={cellW} ch={cellH} reg={reg} active={active} />
      </div>
    );
  };
  return (
    <div data-framegraph-object={o.id || ""} data-framegraph-type="group" data-layout-kind={layout?.kind || "free"} style={st}>
      {(o.children || []).map(renderChild)}
    </div>
  );
}

function ImageObj({ doc, o }) {
  const box = (o.box || [0, 0, 0, 0]).map(toPx);
  const [x, y, w, h] = box;
  const fit = /slice|cover/i.test(o.preserve_aspect_ratio || "") ? "cover" : "contain";
  const clipShape = typeof o.clip === "string" ? o.clip : o.clip?.shape;
  const radius = ["ellipse", "circle"].includes(clipShape) ? "50%" : (o.radius != null ? toPx(o.radius) : 0);
  const src = o.src || o.href || o.url;
  const asset = src && doc?.defs?.assets?.[src];
  const resolvedSrc = asset?.data || asset?.url || asset?.src || src;
  const canLoad = typeof resolvedSrc === "string" && /^(data:|blob:|https?:\/\/)/i.test(resolvedSrc);
  const stroke = resolveStroke(doc, o.stroke_style, o.stroke);
  const border = stroke ? `${stroke.width}px ${stroke.dash ? "dashed" : "solid"} ${stroke.color}` : undefined;
  return (
    <div data-framegraph-object={o.id || ""} data-framegraph-type="image" style={{
      position: "absolute", left: x, top: y, width: w, height: h,
      overflow: "hidden", borderRadius: radius, border, boxSizing: "border-box",
      background: "repeating-linear-gradient(45deg,#f3f3f3 0 8px,#e8e8e8 8px 16px)",
      opacity: o.opacity != null ? o.opacity : 1, ...rotationStyle(o.rotation, box),
    }}>
      {canLoad ? <img src={resolvedSrc} alt={o.alt || o.id || ""} style={{ width: "100%", height: "100%", objectFit: fit, display: "block" }} /> : null}
      {!canLoad && <div style={{
        width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center",
        textAlign: "center", fontFamily: UI.mono, fontSize: Math.max(9, Math.min(12, h / 5)), color: UI.lo,
        padding: 8, boxSizing: "border-box",
      }}>{src || "image"}</div>}
    </div>
  );
}

function textContent(v) {
  if (v == null) return "";
  if (typeof v === "string" || typeof v === "number") return String(v);
  if (Array.isArray(v)) return v.map(textContent).join("");
  if (typeof v === "object") return textContent(v.text ?? v.content ?? v.label ?? v.tex ?? v.source ?? "");
  return "";
}

function textCss(doc, ref, fallback = {}) {
  const style = { ...fallback, ...resolveTextStyle(doc, ref) };
  return {
    fontFamily: resolveFont(doc, style.font),
    fontWeight: style.weight != null ? style.weight : 400,
    fontStyle: style.italic ? "italic" : "normal",
    fontSize: style.size || fallback.size || 16,
    lineHeight: style.line_height != null ? style.line_height : (fallback.line_height || 1.25),
    color: style.color ? resolveColor(doc, style.color) : (fallback.color || "#181211"),
    textAlign: style.align || fallback.align || "left",
    whiteSpace: style.white_space === "pre" ? "pre" : (style.wrap ? "pre-wrap" : "normal"),
    ...styleToCss(doc, ref, { text: true }),
  };
}

function BulletListObj({ doc, o }) {
  const box = (o.box || [0, 0, 0, 0]).map(toPx);
  const [x, y, w, h] = box;
  const marker = o.marker || "•";
  const items = o.items || [];
  const css = textCss(doc, o.style, { size: 16, line_height: 1.25 });
  return (
    <div style={{
      position: "absolute", left: x, top: y, width: w, height: h,
      overflow: "hidden", opacity: o.opacity != null ? o.opacity : 1,
      ...rotationStyle(o.rotation, box),
    }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "grid", gridTemplateColumns: "1.2em 1fr", gap: toPx(o.gap) || 4, ...css }}>
          <span style={{ color: resolveColor(doc, o.marker_color || css.color), textAlign: "center" }}>{marker}</span>
          <span>{textContent(item)}</span>
        </div>
      ))}
    </div>
  );
}

function TableView({ doc, o, absolute = true }) {
  const box = (o.box || [0, 0, 0, 0]).map(toPx);
  const [x, y, w, h] = box;
  const header = o.header || [];
  const rows = o.rows || [];
  const columns = o.columns || [];
  const tableStyle = resolveStyle(doc, o.style);
  const stroke = resolveStroke(doc, o.stroke_style, o.stroke);
  const strokeColor = stroke?.color || resolveColor(doc, "rule") || "#ddd";
  const strokeWidth = stroke?.width != null ? stroke.width : 1;
  const strokeCss = `${strokeWidth}px ${stroke?.dash ? "dashed" : "solid"} ${strokeColor}`;
  const colWidth = (c) => {
    const width = c?.width;
    if (width == null) return "1fr";
    if (typeof width === "number") return `${width}px`;
    return String(width);
  };
  const colTemplate = columns.length
    ? columns.map(colWidth).join(" ")
    : `repeat(${Math.max(1, header.length || rows[0]?.length || 1)}, 1fr)`;
  const pad = o.cell_padding;
  const cellPad = Array.isArray(pad)
    ? pad.map(toPx)
    : (pad != null ? [toPx(pad), toPx(pad), toPx(pad), toPx(pad)] : [5, 8, 5, 8]);
  const headerFill = tableStyle.header_fill ? resolveColor(doc, tableStyle.header_fill) : null;
  const headerTextStyle = tableStyle.header_text;
  const cellTextStyle = tableStyle.cell_text;
  const outer = absolute ? {
    position: "absolute", left: x, top: y, width: w || "auto", height: h || "auto",
    overflow: "hidden", ...styleToCss(doc, o.style), ...rotationStyle(o.rotation, box),
  } : { width: "100%", ...styleToCss(doc, o.style) };
  const cellStyle = (cell, isHead, ri, ci) => ({
    padding: cellPad.map((v) => `${v}px`).join(" "),
    minHeight: toPx(isHead ? o.header_height : o.row_height) || undefined,
    borderBottom: strokeCss,
    borderRight: ci < Math.max(header.length, rows[0]?.length || 0) - 1 ? strokeCss : undefined,
    background: isHead && headerFill ? headerFill : (!isHead && o.zebra && ri % 2 ? "rgba(0,0,0,.035)" : "transparent"),
    ...textCss(doc, cell?.style || (isHead ? headerTextStyle || "th" : cellTextStyle || "cell"), {
      size: tableStyle.size || tableStyle.font_size || 13,
      line_height: tableStyle.line_height || 1.25,
      align: columns[ci]?.align,
    }),
  });
  return (
    <div data-framegraph-table={o.id || ""} style={outer}>
      <div style={{ display: "grid", gridTemplateColumns: colTemplate, borderTop: strokeCss, borderLeft: strokeCss }}>
        {header.map((cell, i) => <div key={`h${i}`} data-table-cell={`${o.id || "table"}:h:0:${i}`} style={cellStyle(cell, true, 0, i)}>{textContent(cell)}</div>)}
        {rows.flatMap((row, ri) => (row || []).map((cell, ci) => (
          <div key={`${ri}-${ci}`} data-table-cell={`${o.id || "table"}:r:${ri}:${ci}`} style={cellStyle(cell, false, ri, ci)}>{textContent(cell)}</div>
        )))}
      </div>
      {o.caption && <div style={{ marginTop: 6, ...textCss(doc, "caption", { size: 12, color: UI.mid, align: "center" }) }}>{o.caption}</div>}
    </div>
  );
}

function FlowBlock({ doc, block }) {
  const type = block?.type;
  if (!block || type === "page_break") return null;
  if (type === "spacer") return <div style={{ height: toPx(block.size || block.height) || 16 }} />;
  if (type === "heading") {
    const tagSize = block.level === 1 ? 24 : block.level === 2 ? 18 : 15;
    return <div style={{ margin: "10px 0 6px", ...textCss(doc, block.style, { size: tagSize, weight: 700, line_height: 1.2 }) }}>{textContent(block)}</div>;
  }
  if (type === "paragraph") {
    return <p style={{ margin: "0 0 8px", ...textCss(doc, block.style, { size: 14, line_height: 1.45 }) }}>{textContent(block.text ?? block.spans)}</p>;
  }
  if (type === "list") {
    return (
      <ul style={{ margin: "0 0 10px 1.25em", padding: 0, ...textCss(doc, block.style, { size: 14, line_height: 1.35 }) }}>
        {(block.items || []).map((item, i) => <li key={i}>{textContent(item)}</li>)}
      </ul>
    );
  }
  if (type === "bullet_list") {
    return (
      <div style={{ margin: "0 0 10px" }}>
        {(block.items || []).map((item, i) => <div key={i} style={{ ...textCss(doc, block.style, { size: 14, line_height: 1.35 }) }}>• {textContent(item)}</div>)}
      </div>
    );
  }
  if (type === "table") return <div style={{ margin: "10px 0 12px" }}><TableView doc={doc} o={block} absolute={false} /></div>;
  if (type === "code") return <pre style={{ margin: "8px 0 12px", padding: 10, background: resolveColor(doc, "code_bg") || "#f4f4f4", overflow: "hidden", ...textCss(doc, block.style, { size: 12, line_height: 1.35 }) }}>{block.source || block.text || ""}</pre>;
  if (type === "math") return <div style={{ margin: "10px 0", textAlign: "center", fontFamily: "serif", fontSize: 16 }}>{block.tex || block.text}</div>;
  if (type === "toc") return <div style={{ margin: "8px 0 12px", ...textCss(doc, block.style, { size: 14, weight: 700 }) }}>{block.title || "Contents"}</div>;
  if (type === "figure") {
    const size = block.size || [320, 160];
    return (
      <figure style={{ margin: "12px auto", width: toPx(size[0]) || "80%" }}>
        <div style={{ position: "relative", width: toPx(size[0]) || 320, height: toPx(size[1]) || 160 }}>
          {block.object ? <RenderObject doc={doc} o={block.object} cw={toPx(size[0]) || 320} ch={toPx(size[1]) || 160} reg={{}} active /> : null}
        </div>
        {block.caption && <figcaption style={{ marginTop: 6, ...textCss(doc, "caption", { size: 12, color: UI.mid, align: "center" }) }}>{block.caption}</figcaption>}
      </figure>
    );
  }
  if (type === "block") return <div style={{ margin: "8px 0", padding: 10, borderLeft: `3px solid ${UI.accent}`, ...textCss(doc, block.style, { size: 14 }) }}>{(block.children || []).map((c, i) => <FlowBlock key={i} doc={doc} block={c} />)}</div>;
  if (type === "bibliography") return <div style={{ marginTop: 12, ...textCss(doc, block.style, { size: 13 }) }}>{block.title || "References"}</div>;
  return <div style={{ margin: "6px 0", ...textCss(doc, block.style, { size: 13, color: UI.mid }) }}>{textContent(block) || `[${type}]`}</div>;
}

function RenderObject({ doc, o, cw, ch, reg, active }) {
  switch (o.type) {
    case "rect": return <RectObj doc={doc} o={o} />;
    case "text": return <TextObj doc={doc} o={o} active={active} />;
    case "line":
    case "polyline":
    case "polygon":
    case "path":
    case "ellipse":
    case "circle": return <VectorObj doc={doc} o={o} cw={cw} ch={ch} reg={reg} />;
    case "icon": return <IconObj doc={doc} o={o} />;
    case "image": return <ImageObj doc={doc} o={o} />;
    case "bullet_list": return <BulletListObj doc={doc} o={o} />;
    case "table": return <TableView doc={doc} o={o} />;
    case "group": return <GroupObj doc={doc} o={o} cw={cw} ch={ch} active={active} />;
    default:
      if (o.from && o.to) return <VectorObj doc={doc} o={{ ...o, type: "line" }} cw={cw} ch={ch} reg={reg} />;
      if (o.children) return <GroupObj doc={doc} o={{ ...o, type: "group" }} cw={cw} ch={ch} active={active} />;
      if (o.box) return <TextObj doc={doc} o={{ ...o, text: textContent(o) || `[${o.type}]`, style: o.style || { size: 12, color: "muted" } }} active={active} />;
      return null;
  }
}

function masterOf(doc, page) {
  return page?.master ? (doc?.defs?.masters || {})[page.master] : null;
}

function flowRegionOf(doc, page) {
  const { w, h } = canvasOf(doc, page);
  const master = masterOf(doc, page);
  const region = master?.regions?.[0]?.box || [72, 72, Math.max(100, w - 144), Math.max(100, h - 144)];
  return region.map(toPx);
}

function estimateTextHeight(doc, styleRef, content, width, fallback = {}) {
  const st = { ...fallback, ...resolveTextStyle(doc, styleRef) };
  const size = st.size || fallback.size || 14;
  const lineHeight = typeof st.line_height === "number" ? st.line_height : parseFloat(st.line_height) || fallback.line_height || 1.35;
  const avg = /mono/i.test(resolveFont(doc, st.font || "")) ? 0.62 : 0.54;
  const charsPerLine = Math.max(12, Math.floor(width / Math.max(1, size * avg)));
  const lines = String(content || "").split(/\n/).reduce((sum, line) => sum + Math.max(1, Math.ceil(line.length / charsPerLine)), 0);
  return Math.max(size * lineHeight, lines * size * lineHeight);
}

function estimateFlowBlockHeight(doc, block, width) {
  const type = block?.type;
  if (!block || type === "page_break") return 0;
  if (type === "spacer") return toPx(block.size || block.height) || 16;
  if (type === "heading") {
    const tagSize = block.level === 1 ? 24 : block.level === 2 ? 18 : 15;
    return estimateTextHeight(doc, block.style, textContent(block), width, { size: tagSize, weight: 700, line_height: 1.2 }) + 16;
  }
  if (type === "paragraph") return estimateTextHeight(doc, block.style, textContent(block.text ?? block.spans), width, { size: 14, line_height: 1.45 }) + 12;
  if (type === "list" || type === "bullet_list") {
    return (block.items || []).reduce((sum, item) => sum + estimateTextHeight(doc, block.style, textContent(item), width - 24, { size: 14, line_height: 1.35 }) + 4, 18);
  }
  if (type === "table") {
    const head = block.header?.length ? 1 : 0;
    return Math.max(toPx(block.header_height) || 0, 34) * head
      + (block.rows || []).length * Math.max(toPx(block.row_height) || 0, 38)
      + (block.caption ? 40 : 0) + 32;
  }
  if (type === "code") {
    const lines = String(block.source || block.text || "").split("\n").length || 1;
    return Math.max(40, lines * 18 + 28);
  }
  if (type === "math") return 48;
  if (type === "toc") return 42;
  if (type === "figure") return (toPx(block.size?.[1]) || 160) + (block.caption ? 58 : 30);
  if (type === "block") {
    return (block.children || []).reduce((sum, child) => sum + estimateFlowBlockHeight(doc, child, width - 24), 42);
  }
  if (type === "bibliography") return 44;
  return estimateTextHeight(doc, block.style, textContent(block) || `[${type}]`, width, { size: 13, line_height: 1.3 }) + 12;
}

function paginateFlowPage(doc, page, sourceIndex) {
  const [, , rw, rh] = flowRegionOf(doc, page);
  const story = page.story || page.sections || [];
  const pages = [];
  let current = [];
  let used = 0;
  const pushPage = () => {
    if (!current.length && pages.length) return;
    pages.push({
      ...page,
      id: `${page.id || `flow_${sourceIndex + 1}`}__p${pages.length + 1}`,
      source_id: page.id,
      source_index: sourceIndex,
      virtual_page: pages.length + 1,
      story: current,
      sections: undefined,
      meta: { ...(page.meta || {}), virtualized_from: page.id || sourceIndex },
    });
    current = [];
    used = 0;
  };
  for (const block of story) {
    if (block?.type === "page_break") {
      pushPage();
      continue;
    }
    const h = estimateFlowBlockHeight(doc, block, rw);
    if (current.length && used + h > rh) pushPage();
    current.push(block);
    used += Math.min(h, rh);
  }
  pushPage();
  return pages.length ? pages : [{ ...page, source_index: sourceIndex, virtual_page: 1 }];
}

function expandDocumentPages(doc) {
  return (doc.pages || []).flatMap((page, i) => (
    page?.mode === "flow" || page?.story || page?.sections
      ? paginateFlowPage(doc, page, i)
      : [{ ...page, source_index: i, virtual_page: 1 }]
  ));
}

function FlowPageCanvas({ doc, page, active = true }) {
  const { w, h } = canvasOf(doc, page);
  const master = masterOf(doc, page);
  const region = flowRegionOf(doc, page);
  const [x, y, rw, rh] = region.map(toPx);
  const running = [
    ...(master?.running?.header || []),
    ...(master?.running?.footer || []),
    ...(master?.running?.page_number ? [{
      type: "text",
      text: "1",
      style: master.running.page_number,
      box: [w / 2 - 20, h - 44, 40, 16],
    }] : []),
  ];
  const story = page.story || page.sections || [];
  return (
    <div
      data-framegraph-page={active ? "active" : "thumb"}
      data-page-mode="flow"
      data-page-id={page?.id || ""}
      style={{ position: "relative", width: w, height: h, background: "#fff", overflow: "hidden" }}>
      {running.map((o, i) => <RenderObject key={o.id || i} doc={doc} o={o} cw={w} ch={h} reg={{}} active={active} />)}
      <div data-flow-region={active ? "active" : "thumb"} style={{
        position: "absolute", left: x, top: y, width: rw, height: rh,
        overflow: "hidden", fontFamily: resolveFont(doc, "serif"), color: resolveColor(doc, "ink"),
      }}>
        {story.map((block, i) => <FlowBlock key={block.id || i} doc={doc} block={block} />)}
      </div>
    </div>
  );
}

/* ============================================================ *
 *  Page canvas — renders all layers at native canvas size
 * ============================================================ */
function PageCanvas({ doc, page, active = true }) {
  if (page?.mode === "flow" || page?.story || page?.sections) {
    return <FlowPageCanvas doc={doc} page={page} active={active} />;
  }
  const { w, h } = canvasOf(doc, page);
  const reg = useMemo(() => buildRegistry(page), [page]);
  const baseBg = resolveColor(doc, "bg") || "#ffffff";
  const layers = useMemo(() => {
    const ls = (page.layers || []).map((l, i) => ({ l, i }));
    return ls.sort((a, b) => (a.l.z || 0) - (b.l.z || 0) || a.i - b.i).map((x) => x.l);
  }, [page]);

  return (
    <div
      data-framegraph-page={active ? "active" : "thumb"}
      data-page-mode={page?.mode || "page"}
      data-page-id={page?.id || ""}
      style={{ position: "relative", width: w, height: h, background: baseBg, overflow: "hidden" }}>
      {layers.map((layer, li) => {
        const objs = (layer.objects || []).map((o, i) => ({ o, i }));
        objs.sort((a, b) => (a.o.z || 0) - (b.o.z || 0) || a.i - b.i);
        return (
          <div key={layer.id || li} style={{ position: "absolute", inset: 0,
            opacity: layer.opacity != null ? layer.opacity : 1 }}>
            {objs.map(({ o }, i) => (
              <RenderObject key={o.id || i} doc={doc} o={o} cw={w} ch={h} reg={reg} active={active} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

/* ============================================================ *
 *  Rulers + registration marks (the measured-artboard signature)
 * ============================================================ */
function niceStep(span) {
  const target = span / 8;
  const steps = [25, 50, 100, 150, 200, 250, 400, 500, 1000];
  for (const s of steps) if (s >= target) return s;
  return 1000;
}
function Ruler({ length, span, scale, vertical, cursor }) {
  const step = niceStep(span);
  const ticks = [];
  for (let v = 0; v <= span + 0.5; v += step) ticks.push(v);
  const RULER = 22;
  return (
    <svg
      width={vertical ? RULER : length}
      height={vertical ? length : RULER}
      style={{ position: "absolute",
        ...(vertical ? { left: -RULER, top: 0 } : { left: 0, top: -RULER }),
        overflow: "visible", pointerEvents: "none" }}>
      {ticks.map((v) => {
        const p = v * scale;
        return vertical ? (
          <g key={v}>
            <line x1={RULER - 6} y1={p} x2={RULER} y2={p} stroke={UI.hair} strokeWidth="1" />
            <text x={RULER - 9} y={p + 3} textAnchor="end"
              fontFamily={UI.mono} fontSize="8.5" fill={UI.lo}>{v}</text>
          </g>
        ) : (
          <g key={v}>
            <line x1={p} y1={RULER - 6} x2={p} y2={RULER} stroke={UI.hair} strokeWidth="1" />
            <text x={p + 3} y={RULER - 9} fontFamily={UI.mono} fontSize="8.5" fill={UI.lo}>{v}</text>
          </g>
        );
      })}
      {cursor != null && cursor >= 0 && cursor <= span && (
        vertical
          ? <line x1={0} y1={cursor * scale} x2={RULER} y2={cursor * scale} stroke={UI.accent} strokeWidth="1" />
          : <line x1={cursor * scale} y1={0} x2={cursor * scale} y2={RULER} stroke={UI.accent} strokeWidth="1" />
      )}
    </svg>
  );
}
function Registration({ w, h }) {
  const L = 14, off = 8, c = UI.faint;
  const Bracket = ({ style, d }) => (
    <svg width={L + 2} height={L + 2} style={{ position: "absolute", overflow: "visible", pointerEvents: "none", ...style }}>
      <path d={d} stroke={c} strokeWidth="1" fill="none" />
    </svg>
  );
  return (
    <>
      <Bracket style={{ left: -off, top: -off }} d={`M0,${L} L0,0 L${L},0`} />
      <Bracket style={{ left: w - L + off, top: -off }} d={`M0,0 L${L},0 L${L},${L}`} />
      <Bracket style={{ left: -off, top: h - L + off }} d={`M0,0 L0,${L} L${L},${L}`} />
      <Bracket style={{ left: w - L + off, top: h - L + off }} d={`M${L},0 L${L},${L} L0,${L}`} />
    </>
  );
}

/* ============================================================ *
 *  Stage — fits the page, draws rulers, tracks coordinates
 * ============================================================ */
function Stage({ doc, page, zoom, onCoord, showRulers }) {
  const ref = useRef(null);
  const [avail, setAvail] = useState({ w: 800, h: 600 });
  const { w: cw, h: ch } = canvasOf(doc, page);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setAvail({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const margin = showRulers ? 46 : 28;
  const fitScale = Math.min((avail.w - margin * 2) / cw, (avail.h - margin * 2) / ch);
  const scale = zoom === "fit" ? Math.max(0.02, fitScale)
    : zoom === 0.5 ? 0.5 : zoom === 1 ? 1 : zoom === 2 ? 2 : Math.max(0.02, fitScale);
  const sw = cw * scale, sh = ch * scale;
  const [cursor, setCursor] = useState(null);

  const move = useCallback((e) => {
    const box = e.currentTarget.getBoundingClientRect();
    const x = Math.round((e.clientX - box.left) / scale);
    const y = Math.round((e.clientY - box.top) / scale);
    if (x >= 0 && y >= 0 && x <= cw && y <= ch) { setCursor({ x, y }); onCoord?.({ x, y }); }
  }, [scale, cw, ch, onCoord]);
  const leave = useCallback(() => { setCursor(null); onCoord?.(null); }, [onCoord]);

  return (
    <div ref={ref} className="flex-1 min-w-0 relative overflow-auto"
      style={{
        background: UI.bg,
        backgroundImage:
          `radial-gradient(${UI.hairSoft} 1px, transparent 1px)`,
        backgroundSize: "26px 26px",
      }}>
      <div className="min-w-full min-h-full flex items-center justify-center"
        style={{ padding: margin, boxSizing: "border-box" }}>
        <div style={{ position: "relative", width: sw, height: sh }}>
          {showRulers && scale > 0.05 && (
            <>
              <Ruler length={sw} span={cw} scale={scale} vertical={false} cursor={cursor?.x} />
              <Ruler length={sh} span={ch} scale={scale} vertical cursor={cursor?.y} />
              <div style={{ position: "absolute", left: -22, top: -22, width: 22, height: 22,
                display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ width: 5, height: 5, border: `1px solid ${UI.hair}` }} />
              </div>
            </>
          )}
          <Registration w={sw} h={sh} />
          {/* canvas badge — below artboard, clear of the top ruler */}
          <div style={{ position: "absolute", top: sh + 9, right: 0,
            fontFamily: UI.mono, fontSize: 10, color: UI.lo, letterSpacing: ".04em" }}>
            {Math.round(cw)} × {Math.round(ch)} px
          </div>
          {/* artboard */}
          <div onMouseMove={move} onMouseLeave={leave}
            style={{ width: sw, height: sh, position: "relative",
              boxShadow: "0 24px 70px -20px rgba(0,0,0,.65), 0 0 0 1px rgba(0,0,0,.4)" }}>
            <div style={{ width: cw, height: ch, transform: `scale(${scale})`, transformOrigin: "top left" }}>
              <PageCanvas doc={doc} page={page} active />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================ *
 *  Thumbnail rail
 * ============================================================ */
function Thumb({ doc, page, index, total, current, onSelect }) {
  const { w, h } = canvasOf(doc, page);
  const TW = 118;
  const scale = TW / w;
  const isCur = index === current;
  return (
    <button
      onClick={() => onSelect(index)}
      className="group relative block w-full text-left outline-none"
      style={{ marginBottom: 12 }}>
      <div className="absolute -left-2 top-0 bottom-0 flex items-center" style={{ width: 4 }}>
        <div style={{ width: 2, height: isCur ? "70%" : 0, background: UI.accent,
          borderRadius: 2, transition: "height .18s ease" }} />
      </div>
      <div style={{
        width: TW, height: h * scale, position: "relative", overflow: "hidden",
        borderRadius: 3,
        boxShadow: isCur ? `0 0 0 1.5px ${UI.accent}` : `0 0 0 1px ${UI.hair}`,
        transition: "box-shadow .15s ease",
      }} className="mx-auto">
        <div style={{ width: w, height: h, transform: `scale(${scale})`, transformOrigin: "top left" }}>
          <PageCanvas doc={doc} page={page} active={false} />
        </div>
      </div>
      <div className="flex items-center gap-1.5 mt-1.5" style={{ paddingLeft: 4 }}>
        <span style={{ fontFamily: UI.mono, fontSize: 10,
          color: isCur ? UI.accent : UI.lo }}>{String(index + 1).padStart(2, "0")}</span>
        <span className="truncate" style={{ fontFamily: UI.mono, fontSize: 9.5, color: UI.faint }}>
          {(page.id || "").replace(/^slide_\d+_/, "")}
        </span>
      </div>
    </button>
  );
}

/* ============================================================ *
 *  Inspector
 * ============================================================ */
function Row({ k, v, mono }) {
  return (
    <div className="flex gap-3 py-1.5" style={{ borderBottom: `1px solid ${UI.hairSoft}` }}>
      <div style={{ fontFamily: UI.mono, fontSize: 10, color: UI.lo, width: 78, flexShrink: 0,
        textTransform: "uppercase", letterSpacing: ".05em", paddingTop: 1 }}>{k}</div>
      <div style={{ fontFamily: mono ? UI.mono : UI.sans, fontSize: 12, color: UI.hi, lineHeight: 1.4 }}>{v}</div>
    </div>
  );
}
function SectionLabel({ children }) {
  return (
    <div style={{ fontFamily: UI.mono, fontSize: 10, color: UI.accent, letterSpacing: ".12em",
      textTransform: "uppercase", margin: "18px 0 8px" }}>{children}</div>
  );
}

function Inspector({ doc, page, tab, setTab }) {
  const colors = doc?.defs?.tokens?.colors || {};
  const fonts = doc?.defs?.tokens?.fonts || {};
  const textStyles = doc?.defs?.tokens?.text_styles || {};
  const tabs = [
    { id: "doc", icon: Info, label: "Doc" },
    { id: "tokens", icon: Palette, label: "Tokens" },
    { id: "page", icon: Layers, label: "Page" },
  ];

  const objCounts = useMemo(() => {
    const c = {};
    (page?.layers || []).forEach((l) => (l.objects || []).forEach((o) => { c[o.type] = (c[o.type] || 0) + 1; }));
    return c;
  }, [page]);

  return (
    <div className="h-full flex flex-col" style={{ background: UI.panel, borderLeft: `1px solid ${UI.hair}` }}>
      <div className="flex" style={{ borderBottom: `1px solid ${UI.hair}` }}>
        {tabs.map((t) => {
          const on = tab === t.id;
          const Icon = t.icon;
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              className="flex-1 flex items-center justify-center gap-1.5 outline-none"
              style={{ height: 40, color: on ? UI.hi : UI.mid,
                borderBottom: on ? `2px solid ${UI.accent}` : "2px solid transparent",
                background: on ? UI.panelAlt : "transparent" }}>
              <Icon size={13} />
              <span style={{ fontFamily: UI.mono, fontSize: 10.5, letterSpacing: ".04em" }}>{t.label}</span>
            </button>
          );
        })}
      </div>

      <div className="flex-1 overflow-auto" style={{ padding: "8px 16px 24px" }}>
        {tab === "doc" && (
          <div>
            <SectionLabel>Document</SectionLabel>
            <Row k="Title" v={doc.title} />
            <Row k="Profile" v={doc.profile} mono />
            <Row k="DSL" v={`${doc.dsl} ${doc.version}`} mono />
            <Row k="Lang" v={doc.lang} mono />
            <Row k="Pages" v={String((doc.pages || []).length)} mono />
            {doc.targets?.[0] && (
              <Row k="Canvas" v={`${doc.targets[0].canvas.size.join(" × ")} ${doc.targets[0].canvas.units}`} mono />
            )}
            {doc.description && (
              <>
                <SectionLabel>Description</SectionLabel>
                <p style={{ fontFamily: UI.sans, fontSize: 12, color: UI.mid, lineHeight: 1.55 }}>{doc.description}</p>
              </>
            )}
            {doc.meta?.status && (
              <>
                <SectionLabel>Status</SectionLabel>
                <p style={{ fontFamily: UI.mono, fontSize: 11, color: UI.mid, lineHeight: 1.5 }}>{doc.meta.status}</p>
              </>
            )}
          </div>
        )}

        {tab === "tokens" && (
          <div>
            <SectionLabel>Color · {Object.keys(colors).length}</SectionLabel>
            <div className="grid grid-cols-2 gap-x-3 gap-y-2">
              {Object.entries(colors).map(([name, val]) => (
                <div key={name} className="flex items-center gap-2 min-w-0">
                  <div style={{ width: 18, height: 18, borderRadius: 3, flexShrink: 0,
                    background: val, boxShadow: `inset 0 0 0 1px rgba(255,255,255,.12)` }} />
                  <div className="min-w-0">
                    <div className="truncate" style={{ fontFamily: UI.mono, fontSize: 10, color: UI.hi }}>{name}</div>
                    <div style={{ fontFamily: UI.mono, fontSize: 9, color: UI.lo }}>{String(val).toUpperCase()}</div>
                  </div>
                </div>
              ))}
            </div>

            <SectionLabel>Type · {Object.keys(fonts).length}</SectionLabel>
            {Object.entries(fonts).map(([name, def]) => (
              <Row key={name} k={name} mono
                v={typeof def === "string" ? def : `${def.family}${def.fallback ? " · " + def.fallback.join(", ") : ""}`} />
            ))}

            <SectionLabel>Text styles · {Object.keys(textStyles).length}</SectionLabel>
            <div className="flex flex-wrap gap-1.5">
              {Object.keys(textStyles).map((name) => (
                <span key={name} style={{ fontFamily: UI.mono, fontSize: 10, color: UI.mid,
                  padding: "3px 7px", borderRadius: 4, background: UI.panelAlt,
                  border: `1px solid ${UI.hair}` }}>{name}</span>
              ))}
            </div>
          </div>
        )}

        {tab === "page" && (
          <div>
            <SectionLabel>Current page</SectionLabel>
            <Row k="ID" v={page.id} mono />
            <Row k="Mode" v={page.mode} mono />
            <Row k="Layers" v={String((page.layers || []).length)} mono />
            {page.canvas && <Row k="Canvas" v={`${page.canvas.size.join(" × ")} ${page.canvas.units || "px"}`} mono />}

            <SectionLabel>Objects</SectionLabel>
            <div className="flex flex-col gap-1.5">
              {Object.entries(objCounts).map(([type, n]) => (
                <div key={type} className="flex items-center justify-between"
                  style={{ fontFamily: UI.mono, fontSize: 11 }}>
                  <span style={{ color: UI.mid }}>{type}</span>
                  <div className="flex-1 mx-3" style={{ height: 1, background: UI.hairSoft, alignSelf: "center" }} />
                  <span style={{ color: UI.hi }}>{n}</span>
                </div>
              ))}
            </div>

            <SectionLabel>Layers</SectionLabel>
            {(page.layers || []).map((l, i) => (
              <div key={l.id || i} className="flex items-center gap-2 py-1.5"
                style={{ borderBottom: `1px solid ${UI.hairSoft}` }}>
                <Layers size={12} style={{ color: UI.lo }} />
                <span style={{ fontFamily: UI.mono, fontSize: 11, color: UI.hi }}>{l.id || `layer ${i}`}</span>
                <span style={{ fontFamily: UI.mono, fontSize: 9.5, color: UI.lo, marginLeft: "auto" }}>
                  z {l.z ?? 0} · {(l.objects || []).length} obj
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ============================================================ *
 *  Top + bottom bars
 * ============================================================ */
function Chip({ children }) {
  return (
    <span style={{ fontFamily: UI.mono, fontSize: 10.5, color: UI.mid,
      padding: "3px 8px", borderRadius: 4, border: `1px solid ${UI.hair}`,
      background: UI.panelAlt, letterSpacing: ".03em", whiteSpace: "nowrap" }}>{children}</span>
  );
}
function RegMark({ size = 16, color = UI.accent }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" style={{ flexShrink: 0 }}>
      <circle cx="8" cy="8" r="6.2" fill="none" stroke={color} strokeWidth="1.2" />
      <line x1="8" y1="0.5" x2="8" y2="15.5" stroke={color} strokeWidth="1.2" />
      <line x1="0.5" y1="8" x2="15.5" y2="8" stroke={color} strokeWidth="1.2" />
    </svg>
  );
}

function App() {
  const [doc, setDoc] = useState(DEMO_DOC);
  const [idx, setIdx] = useState(0);
  const [zoom, setZoom] = useState("fit");
  const [tab, setTab] = useState("doc");
  const [showInspector, setShowInspector] = useState(true);
  const [coord, setCoord] = useState(null);
  const [err, setErr] = useState(null);
  const fileRef = useRef(null);

  const pages = useMemo(() => expandDocumentPages(doc), [doc]);
  const page = pages[Math.min(idx, pages.length - 1)];
  const total = pages.length;

  const go = useCallback((d) => setIdx((i) => Math.max(0, Math.min(total - 1, i + d))), [total]);

  useEffect(() => {
    window.__FRAMEGRAPH_VIEWER__ = {
      loadDoc(nextDoc) {
        if (!nextDoc || !Array.isArray(nextDoc.pages)) throw new Error("No pages array found.");
        setDoc(nextDoc);
        setIdx(0);
        setErr(null);
      },
      setPage(nextIdx) {
        setIdx(Math.max(0, Math.min((nextIdx || 0), Math.max(0, pages.length - 1))));
      },
      state() {
        return { title: doc.title, pageIndex: idx, pageCount: pages.length, sourcePageCount: (doc.pages || []).length };
      },
    };
    return () => { delete window.__FRAMEGRAPH_VIEWER__; };
  }, [doc, idx, pages]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.target && /input|textarea/i.test(e.target.tagName)) return;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); go(1); }
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); go(-1); }
      else if (e.key === "Home") setIdx(0);
      else if (e.key === "End") setIdx(total - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, total]);

  const openFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      try {
        const raw = String(r.result);
        const parsed = /\.ya?ml$/i.test(f.name) ? yaml.load(raw) : JSON.parse(raw);
        if (!parsed.pages || !Array.isArray(parsed.pages)) throw new Error("No pages array found.");
        setDoc(parsed); setIdx(0); setErr(null);
      } catch (e2) {
        setErr("Couldn't parse that FrameGraph document: " + e2.message);
      }
    };
    r.readAsText(f);
    e.target.value = "";
  };

  const zoomOpts = [["fit", "Fit"], [0.5, "50"], [1, "100"], [2, "200"]];

  return (
    <div className="w-full h-screen flex flex-col select-none"
      style={{ background: UI.bg, color: UI.hi, fontFamily: UI.sans }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { -webkit-font-smoothing: antialiased; }
        ::-webkit-scrollbar { width: 9px; height: 9px; }
        ::-webkit-scrollbar-thumb { background: ${UI.hair}; border-radius: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        button:focus-visible { outline: 2px solid ${UI.accent}; outline-offset: 2px; }
        @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
      `}</style>

      {/* Top bar */}
      <header className="flex items-center gap-3 px-4 flex-shrink-0"
        style={{ height: 50, background: UI.panel, borderBottom: `1px solid ${UI.hair}` }}>
        <div className="flex items-center gap-2">
          <RegMark />
          <span style={{ fontFamily: UI.sans, fontWeight: 600, fontSize: 15, letterSpacing: "-.01em" }}>
            framelight
          </span>
        </div>
        <div style={{ width: 1, height: 22, background: UI.hair }} />
        <div className="min-w-0 flex-1">
          <div className="truncate" style={{ fontSize: 12.5, color: UI.mid }}>{doc.title}</div>
        </div>
        <Chip>{doc.profile}</Chip>
        <Chip>{doc.dsl} {doc.version}</Chip>
        <button onClick={() => fileRef.current?.click()}
          className="flex items-center gap-1.5 outline-none"
          style={{ fontFamily: UI.mono, fontSize: 11, color: UI.mid, padding: "5px 10px",
            borderRadius: 5, border: `1px solid ${UI.hair}`, background: UI.panelAlt }}>
          <Upload size={12} /> Open
        </button>
        <input ref={fileRef} type="file" accept=".json,.yaml,.yml,application/json,text/yaml,application/yaml" onChange={openFile} className="hidden" />
        <button onClick={() => setShowInspector((s) => !s)}
          className="outline-none flex items-center justify-center"
          title={showInspector ? "Hide inspector" : "Show inspector"}
          style={{ width: 30, height: 30, borderRadius: 5, color: showInspector ? UI.hi : UI.mid,
            border: `1px solid ${UI.hair}`, background: showInspector ? UI.panelAlt : "transparent" }}>
          <Layers size={14} />
        </button>
      </header>

      {err && (
        <div className="flex items-center gap-2 px-4 py-2 flex-shrink-0"
          style={{ background: "#2A1714", borderBottom: `1px solid ${UI.accentDim}`,
            fontFamily: UI.mono, fontSize: 11.5, color: "#F0B5A8" }}>
          <X size={13} style={{ cursor: "pointer" }} onClick={() => setErr(null)} /> {err}
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        {/* Filmstrip */}
        <nav className="flex-shrink-0 overflow-auto hidden sm:block"
          style={{ width: 158, background: UI.rail, borderRight: `1px solid ${UI.hair}`, padding: "14px 14px 14px 16px" }}>
          <div style={{ fontFamily: UI.mono, fontSize: 9.5, color: UI.lo, letterSpacing: ".12em",
            textTransform: "uppercase", marginBottom: 12 }}>
            {total} pages
          </div>
          {pages.map((p, i) => (
            <Thumb key={p.id || i} doc={doc} page={p} index={i} total={total} current={idx} onSelect={setIdx} />
          ))}
        </nav>

        {/* Stage */}
        <Stage doc={doc} page={page} zoom={zoom} onCoord={setCoord} showRulers />

        {/* Inspector */}
        {showInspector && (
          <aside className="flex-shrink-0 hidden md:block" style={{ width: 308 }}>
            <Inspector doc={doc} page={page} tab={tab} setTab={setTab} />
          </aside>
        )}
      </div>

      {/* Bottom bar */}
      <footer className="flex items-center gap-3 px-4 flex-shrink-0"
        style={{ height: 46, background: UI.panel, borderTop: `1px solid ${UI.hair}` }}>
        <div className="flex items-center gap-1">
          <button onClick={() => go(-1)} disabled={idx === 0}
            className="outline-none flex items-center justify-center"
            style={{ width: 30, height: 30, borderRadius: 5, color: idx === 0 ? UI.faint : UI.hi,
              border: `1px solid ${UI.hair}`, background: UI.panelAlt }}>
            <ChevronLeft size={16} />
          </button>
          <button onClick={() => go(1)} disabled={idx === total - 1}
            className="outline-none flex items-center justify-center"
            style={{ width: 30, height: 30, borderRadius: 5, color: idx === total - 1 ? UI.faint : UI.hi,
              border: `1px solid ${UI.hair}`, background: UI.panelAlt }}>
            <ChevronRight size={16} />
          </button>
        </div>
        <div style={{ fontFamily: UI.mono, fontSize: 13, color: UI.hi }}>
          {String(idx + 1).padStart(2, "0")}
          <span style={{ color: UI.lo }}> / {String(total).padStart(2, "0")}</span>
        </div>
        <div className="truncate hidden sm:block" style={{ fontFamily: UI.mono, fontSize: 11, color: UI.lo }}>
          {page?.id}
        </div>

        <div className="flex-1" />

        {/* zoom segmented control */}
        <div className="flex items-center" style={{ border: `1px solid ${UI.hair}`, borderRadius: 6, overflow: "hidden" }}>
          {zoomOpts.map(([val, label], i) => {
            const on = zoom === val;
            return (
              <button key={String(val)} onClick={() => setZoom(val)}
                className="outline-none flex items-center justify-center gap-1"
                style={{ height: 28, padding: "0 10px", color: on ? UI.bg : UI.mid,
                  background: on ? UI.accent : "transparent",
                  borderLeft: i ? `1px solid ${UI.hair}` : "none",
                  fontFamily: UI.mono, fontSize: 11, fontWeight: on ? 600 : 400 }}>
                {val === "fit" && <Maximize2 size={11} />}{label}
              </button>
            );
          })}
        </div>

        {/* live coordinate readout */}
        <div className="hidden sm:flex items-center gap-1.5"
          style={{ minWidth: 138, justifyContent: "flex-end" }}>
          <Crosshair size={12} style={{ color: coord ? UI.accent : UI.faint }} />
          <span style={{ fontFamily: UI.mono, fontSize: 11.5, color: coord ? UI.hi : UI.faint }}>
            {coord ? `x ${String(coord.x).padStart(4, " ")}` : "x ····"}
          </span>
          <span style={{ fontFamily: UI.mono, fontSize: 11.5, color: coord ? UI.hi : UI.faint }}>
            {coord ? `y ${String(coord.y).padStart(4, " ")}` : "y ····"}
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
