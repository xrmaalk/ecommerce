# Purrcilla hero illustration

The storefront hero uses `frontend/public/purrcilla-hero-mascot.png`, a 1024 × 1536 transparent PNG extracted with the built-in imagegen tool. The original reference is `frontend/public/organicemperor-purrcilla-preview.png`.

The halo, original leaf-and-crown emblem, and BODIGLO wording are rendered by `HeroSection.vue` and the storefront CSS. This keeps the live headline and page copy from repeating inside the illustration. The social-preview image remains the source of the storefront sharing card.

## Exact generation prompt

> Use case: background-extraction. Asset type: a transparent mascot illustration for the OrganicEmperor storefront hero. Image 1 is the edit target. Extract ONLY the full-body Purrcilla cat from this artwork onto a genuinely transparent alpha background, in a portrait composition with a small clear margin around the whole character. Preserve her identity, exact pose, face, big green eyes, brown tabby fur, cream muzzle and chest, purple and magenta lightning-pattern tracksuit, dark boots with gold accents, raised paw beneath her chin, and curled fluffy tail. Keep the original polished cartoon illustration style and subtle golden rim lighting. Both ears, every part of her tail, and both boots must remain visible. Remove all background, the large halo circle, ground glow, logos, emblems, lettering, site title, slogans, and other text. Do not add text, objects, characters, a floor, a new pose, or a background. The halo, original emblem, and brand wording will be rendered separately as HTML/CSS in the website; this asset must contain the character alone.

The PNG alpha channel was verified before integration. The generated output was copied into the repository without modifying its pixels.
