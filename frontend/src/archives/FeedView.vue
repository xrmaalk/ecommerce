<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { formatDate, getArchive, kindLabels, type Page, type Post, type PostKind } from "./api"

const route = useRoute()
const router = useRouter()
const categories = [{ value: "", label: "All posts" }, { value: "article", label: "Articles" }, { value: "release", label: "News releases" }, { value: "update", label: "Updates" }]
const kind = computed(() => categories.some(item => item.value === route.query.kind) ? String(route.query.kind) : "")
const query = computed(() => typeof route.query.search === "string" ? route.query.search : "")
const page = computed(() => { const value = Number(route.query.page); return Number.isSafeInteger(value) && value > 0 ? value : 1 })
const search = ref(query.value)
const posts = ref<Post[]>([])
const total = ref(0)
const hasNext = ref(false)
const loading = ref(true)
const error = ref(false)
let controller: AbortController | undefined

async function load() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  error.value = false
  search.value = query.value
  try {
    const params = new URLSearchParams({ page: String(page.value) })
    if (kind.value) params.set("kind", kind.value)
    if (query.value) params.set("search", query.value)
    const data = await getArchive<Page>(`posts/?${params}`, request.signal)
    if (request.signal.aborted) return
    posts.value = data.results
    total.value = data.count
    hasNext.value = Boolean(data.next)
  } catch {
    if (!request.signal.aborted) error.value = true
  } finally {
    if (!request.signal.aborted) loading.value = false
  }
}
function filter(value: string) {
  void router.push({ name: "feed", query: { ...(query.value ? { search: query.value } : {}), ...(value ? { kind: value } : {}) } })
}
function submitSearch() {
  void router.push({ name: "feed", query: { ...(kind.value ? { kind: kind.value } : {}), ...(search.value.trim() ? { search: search.value.trim() } : {}) } })
}
watch(() => route.fullPath, load, { immediate: true })
onUnmounted(() => controller?.abort())
</script>

<template>
  <section class="feed-intro">
    <div><p class="eyebrow"><span class="live-dot" /> THE JOURNAL</p><h1>Good things,<br class="mobile-break" /> worth knowing<span>.</span></h1><p>Articles, news, and notes from the world of Organic Emperor.</p></div>
    <span class="issue-label">THE ORGANIC ARCHIVES<br /><strong>Ideas. Ingredients. Everyday rituals.</strong></span>
  </section>
  <div class="feed-layout">
    <section class="feed-main" aria-label="Posts">
      <div class="feed-toolbar">
        <nav class="feed-tabs" aria-label="Post categories"><button v-for="category in categories" :key="category.value" :class="{ selected: kind === category.value }" :aria-pressed="kind === category.value" @click="filter(category.value)">{{ category.label }}</button></nav>
        <span class="sort-label">Newest first <span aria-hidden="true">↓</span></span>
      </div>
      <form class="feed-search" role="search" @submit.prevent="submitSearch">
        <label class="sr-only" for="archive-search">Search the archives</label><span aria-hidden="true">⌕</span>
        <input id="archive-search" v-model="search" type="search" maxlength="160" placeholder="Search the archives…" /><button type="submit">Search <span aria-hidden="true">↵</span></button>
      </form>
      <div aria-live="polite" :aria-busy="loading">
        <div v-if="loading" class="feed-state"><span class="eyebrow">ONE MOMENT</span><h2>Opening the archives…</h2></div>
        <div v-else-if="error" class="feed-state"><h2>The feed couldn’t be loaded.</h2><p>Please try again in a moment.</p><button class="solid-button" @click="load">Try again</button></div>
        <template v-else>
          <div v-if="query" class="search-summary">{{ total }} {{ total === 1 ? 'result' : 'results' }} for “{{ query }}” <RouterLink :to="{ name: 'feed', query: kind ? { kind } : {} }">Clear search</RouterLink></div>
          <ol v-if="posts.length" class="post-list" :start="(page - 1) * 15 + 1">
            <li v-for="(post, index) in posts" :key="post.id" class="post-row">
              <span class="post-number" aria-hidden="true">{{ String((page - 1) * 15 + index + 1).padStart(2, '0') }}</span>
              <article class="post-summary">
                <div class="post-kicker"><span class="kind-badge" :class="post.kind">{{ kindLabels[post.kind as PostKind] }}</span><span v-if="post.topic" class="topic-label">{{ post.topic }}</span><span v-if="post.has_video" class="video-label"><span aria-hidden="true">▷</span> Video</span></div>
                <h2><RouterLink :to="{ name: 'post', params: { slug: post.slug } }">{{ post.title }}</RouterLink></h2>
                <p>{{ post.excerpt }}</p>
                <div class="post-meta"><span>{{ post.author_name }}</span><span aria-hidden="true">·</span><time :datetime="post.published_at">{{ formatDate(post.published_at) }}</time><span aria-hidden="true">·</span><span>{{ post.reading_minutes }} min read</span></div>
              </article>
              <RouterLink v-if="post.cover_image" class="post-thumbnail" :to="{ name: 'post', params: { slug: post.slug } }" tabindex="-1" aria-hidden="true"><img :src="post.cover_image" alt="" loading="lazy" /></RouterLink>
              <RouterLink v-else class="post-arrow" :to="{ name: 'post', params: { slug: post.slug } }" :aria-label="`Read ${post.title}`"><span aria-hidden="true">↗</span></RouterLink>
            </li>
          </ol>
          <div v-else class="feed-state"><span class="eyebrow">{{ query || kind ? 'NOTHING HERE YET' : 'A NEW CHAPTER' }}</span><h2>{{ query ? 'No posts match your search.' : kind ? 'No posts in this category yet.' : 'The first entry is on its way.' }}</h2><p>{{ query ? 'Try a different word or browse all posts.' : 'Come back for stories, news, and updates from Organic Emperor.' }}</p><RouterLink v-if="query || kind" class="text-link" to="/">Browse all posts →</RouterLink></div>
          <div v-if="total" class="feed-pagination"><span>{{ (page - 1) * 15 + 1 }}–{{ (page - 1) * 15 + posts.length }} of {{ total }} posts</span><div><RouterLink v-if="page > 1" :to="{ query: { ...route.query, page: page - 1 } }">← Newer</RouterLink><RouterLink v-if="hasNext" :to="{ query: { ...route.query, page: page + 1 } }">Older posts →</RouterLink></div></div>
        </template>
      </div>
    </section>
    <aside class="feed-sidebar">
      <section class="about-card"><span class="eyebrow">A NOTE FROM THE EDITORS</span><h2>A little closer<br />to the source.</h2><p>The stories behind the products. The ingredients we’re curious about. The things we’re working on.</p><p>This is our space to share them.</p><RouterLink :to="{ name: 'feed', query: { kind: 'update' } }">From Organic Emperor <span aria-hidden="true">↗</span></RouterLink></section>
      <section class="inside-archives"><h2>Inside the archives</h2><button @click="filter('article')"><span><strong>01 / Articles</strong><small>Ideas, ingredients, and everyday rituals</small></span><span aria-hidden="true">↗</span></button><button @click="filter('release')"><span><strong>02 / News releases</strong><small>Official announcements, in one place</small></span><span aria-hidden="true">↗</span></button><button @click="filter('update')"><span><strong>03 / Updates</strong><small>The latest from behind the scenes</small></span><span aria-hidden="true">↗</span></button></section>
      <a class="store-note" href="https://organicemperor.com"><span>FROM THE JOURNAL TO YOUR ROUTINE</span><strong>Explore Organic Emperor <span aria-hidden="true">↗</span></strong></a>
    </aside>
  </div>
</template>
