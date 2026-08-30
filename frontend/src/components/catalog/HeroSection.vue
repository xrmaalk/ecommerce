<template>
  <section class="hero-section" aria-labelledby="hero-title">
    <div class="hero-copy">
      <p class="eyebrow">Daily Routine; Refined.</p>
      <h1 id="hero-title">Forever Selfcare</h1>
      <p class="hero-lede">
        Quality body care, must have shave essentials and comforting organic
        teas.
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
      aria-label="Organic Emperor Daily Moisture collection">
      <span class="hero-art__halo" aria-hidden="true"></span>
      <div class="hero-bottle">
        <img src="/organic-emperor-emblem.png" alt="" />
        <b>BODIGLO</b><strong>DAILY<br />MOISTURIZER</strong
        ><small>Get theGlow. </small>
      </div>
    </div>
  </section>
</template>
