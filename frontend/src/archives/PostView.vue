<script setup lang="ts">
import { onUnmounted, ref, watch } from "vue"
import { useRoute } from "vue-router"
import { ArchiveError, formatDate, getArchive, kindLabels, type PostDetail } from "./api"
const route = useRoute()
const post = ref<PostDetail | null>(null)
const loading = ref(true)
const missing = ref(false)
let controller: AbortController | undefined
async function load() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  missing.value = false
  post.value = null
  try {
    const data = await getArchive<PostDetail>(`posts/${encodeURIComponent(String(route.params.slug))}/`, request.signal)
    if (request.signal.aborted) return
    post.value = data
    document.title = `${data.title} | Organic Archives`
    document.querySelector('meta[name="description"]')?.setAttribute("content", data.excerpt)
    document.querySelector('meta[property="og:title"]')?.setAttribute("content", document.title)
    document.querySelector('meta[property="og:description"]')?.setAttribute("content", data.excerpt)
    document.querySelector('meta[property="og:type"]')?.setAttribute("content", "article")
  } catch (error) {
    if (!request.signal.aborted) missing.value = error instanceof ArchiveError && error.status === 404
  } finally { if (!request.signal.aborted) loading.value = false }
}
watch(() => route.params.slug, load, { immediate: true })
onUnmounted(() => controller?.abort())
</script>

<template>
  <div class="reader-wrap">
    <RouterLink class="back-link" to="/">← Back to the feed</RouterLink>
    <div v-if="loading" class="feed-state" role="status"><h1>Opening the story…</h1></div>
    <div v-else-if="!post" class="feed-state"><h1>{{ missing ? 'This post isn’t available.' : 'The post couldn’t be loaded.' }}</h1><p>{{ missing ? 'It may have moved or is no longer published.' : 'Please try again in a moment.' }}</p><button v-if="!missing" class="solid-button" @click="load">Try again</button><RouterLink v-else class="text-link" to="/">Browse the archives →</RouterLink></div>
    <article v-else class="reader">
      <header><div class="post-kicker"><RouterLink class="kind-badge" :class="post.kind" :to="{ name: 'feed', query: { kind: post.kind } }">{{ kindLabels[post.kind] }}</RouterLink><span v-if="post.topic" class="topic-label">{{ post.topic }}</span></div><h1>{{ post.title }}</h1><p class="reader-excerpt">{{ post.excerpt }}</p><div class="reader-byline"><span class="author-avatar" aria-hidden="true">{{ post.author_name.charAt(0) }}</span><div><strong>{{ post.author_name }}</strong><div class="post-meta"><time :datetime="post.published_at">{{ formatDate(post.published_at) }}</time><span aria-hidden="true">·</span><span>{{ post.reading_minutes }} min read</span></div></div></div></header>
      <figure v-if="post.cover_image" class="reader-cover"><img :src="post.cover_image" :alt="post.cover_alt" /></figure>
      <div class="reader-body">
        <template v-for="block in post.blocks" :key="block.id">
          <div v-if="block.kind === 'text'" class="text-block"><p v-for="(paragraph, index) in block.text.split(/\n\s*\n/)" :key="index">{{ paragraph }}</p></div>
          <h2 v-else-if="block.kind === 'heading'">{{ block.text }}</h2>
          <figure v-else-if="block.kind === 'quote'" class="quote-block"><blockquote>{{ block.text }}</blockquote><figcaption v-if="block.caption">{{ block.caption }}</figcaption></figure>
          <figure v-else-if="block.kind === 'image' && block.image"><img :src="block.image" :alt="block.alt_text" loading="lazy" /><figcaption v-if="block.caption">{{ block.caption }}</figcaption></figure>
          <figure v-else-if="block.kind === 'video' && block.video"><video :src="block.video" controls playsinline preload="metadata" :aria-label="block.caption || 'Post video'"><a :href="block.video">Download video</a></video><figcaption v-if="block.caption">{{ block.caption }}</figcaption></figure>
          <figure v-else-if="block.kind === 'embed' && block.embed_url"><iframe :src="block.embed_url" :title="block.caption || 'Post video'" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allow="encrypted-media; fullscreen; picture-in-picture" allowfullscreen sandbox="allow-scripts allow-same-origin allow-presentation" /><figcaption v-if="block.caption">{{ block.caption }}</figcaption></figure>
        </template>
      </div>
      <footer class="reader-end"><span class="archive-monogram" aria-hidden="true">OA<span>.</span></span><div><strong>More from the archives</strong><RouterLink to="/">Back to all articles, news, and updates →</RouterLink></div></footer>
    </article>
  </div>
</template>
