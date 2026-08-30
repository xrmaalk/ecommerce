<template>
  <section class="hero-section" aria-labelledby="hero-title">
    <div class="hero-copy">
      <p class="eyebrow">Daily routines, refined</p>
      <h1 id="hero-title">Forever selfcare</h1>
      <p class="hero-lede">
        Purposeful body care, thoughtful shave essentials and comforting organic
        teas.
      </p>
      <RouterLink
        class="button button--primary"
        :to="{ name: 'home', hash: '#catalog' }"
        >Shop essentials <span aria-hidden="true">→</span></RouterLink
      >
      <ul class="hero-promises" aria-label="Shopping benefits">
        <li>Curated quality</li>
        <li>Canadian shop</li>
        <li>Thoughtful service</li>
      </ul>
    </div>
    <div
      class="hero-art"
      aria-label="Organic Emperor Daily Moisture collection">
      <span class="hero-art__halo" aria-hidden="true"></span>
      <div class="hero-bottle">
        <img src="/organic-emperor-emblem.png" alt="" />
        <b>BODIGLO</b><strong>DAILY<br />MOISTURE</strong
        ><small>Thoughtful care, naturally.</small>
      </div>
    </div>
  </section>
</template>
