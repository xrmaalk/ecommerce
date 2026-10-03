<template>
  <section class="hero-section" aria-labelledby="hero-title">
    <div class="hero-copy">
      <p class="eyebrow">Daily Routine; Refined.</p>
      <h1 id="hero-title">
        <span class="hero-title__word hero-title__word--forever">Forever</span>
        <span class="hero-title__word hero-title__word--wellness"
          >Wellness</span
        >
      </h1>
      <p class="hero-lede">
        Quality body care, must have shave essentials, comforting organic teas,
        soap, de-odorant and wellness products.
      </p>
      <RouterLink
        class="button button--primary"
        :to="{ name: 'home', hash: '#catalog' }"
        >Shop essentials <span aria-hidden="true">→</span></RouterLink
      >
      <ul class="hero-promises" aria-label="Shopping benefits">
        <li>Curated Quality</li>
        <li>Globally Sourced Ingredience</li>
        <li>Worldclass Service</li>
      </ul>
    </div>
    <div class="hero-art">
      <div class="hero-art__stage">
        <span class="hero-art__halo" aria-hidden="true"></span>
        <img
          class="hero-art__mascot"
          src="/purrcilla-hero-mascot.png"
          alt="Purrcilla, the green-eyed tabby mascot, wearing her purple lightning tracksuit."
          width="1024"
          height="1536"
          fetchpriority="high"
          decoding="async" />
        <div class="hero-art__brand">
          <img
            class="hero-art__emblem"
            src="/organic-emperor-emblem.png"
            alt="Leaf and crown emblem"
            width="444"
            height="512" />
          <p class="hero-art__label">BODIGLO</p>
          <p class="hero-art__daily">DAILY</p>
          <p class="hero-art__wellness">Dose of Wellness</p>
          <p class="hero-art__tagline">Get the Glow.</p>
        </div>
      </div>
    </div>
  </section>
</template>
