<template>
  <section class="hero-section" aria-labelledby="hero-title">
    <div class="hero-copy">
      <p class="eyebrow">Daily Routine; Refined.</p>
      <h1 id="hero-title">
        <span class="hero-title__word hero-title__word--forever">Forever</span>
        <span class="hero-title__word hero-title__word--wellness">Wellness</span>
      </h1>
      <p class="hero-lede">
        Quality body care, must have shave essentials and comforting organic
        teas and soaps.
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
    <div
      class="hero-art"
      aria-label="OrganicEmperor.com Daily Moisture collection">
      <span class="hero-art__halo" aria-hidden="true"></span>
      <div class="hero-bottle">
        <img src="/organic-emperor-emblem.png" alt="OrganicEmperor Emblem" />
        <b>BODIGLO</b><strong>DAILY<br />Dose of Wellness</strong
        ><small>Get theGlow. </small>
      </div>
    </div>
  </section>
</template>
