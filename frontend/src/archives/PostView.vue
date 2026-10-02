<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue"
import { useRoute } from "vue-router"
import {
  ArchiveError,
  formatDate,
  getArchive,
  getArchivePreview,
  kindLabels,
  publisherUrl,
  type PostDetail,
  type PostPreview,
} from "./api"
import {
  addPostComment,
  getPostEngagement,
  likePost,
  ReaderApiError,
  unlikePost,
  type PostEngagement,
} from "./readerApi"
import { useArchiveReaderStore } from "./readerStore"
import { renderMarkdown } from "./markdown"
import { articleMetadata, beginMetadata, siteMetadata } from "../seo"

const route = useRoute()
const reader = useArchiveReaderStore()
const preview = computed(() => route.name === "preview")
const post = ref<PostDetail | PostPreview | null>(null)
const editUrl = computed(() => post.value && "edit_url" in post.value ? post.value.edit_url : publisherUrl)
const previewLabel = computed(() => post.value && "status" in post.value && post.value.status === "draft"
  ? "Draft preview" : "Editorial preview")
const denied = ref(false)
const loading = ref(true)
const missing = ref(false)
const engagement = ref<PostEngagement>({
  like_count: 0,
  liked: false,
  comment_count: 0,
  comments: [],
})
const engagementLoading = ref(true)
const likeBusy = ref(false)
const commentBusy = ref(false)
const commentBody = ref("")
const interactionError = ref("")
const readerLink = computed(() => ({
  name: "reader",
  query: { returnTo: route.fullPath },
}))
let controller: AbortController | undefined

function showInteractionError(error: unknown) {
  interactionError.value =
    error instanceof ReaderApiError
      ? error.message
      : "That could not be saved. Please try again."
}

async function loadEngagement(slug: string) {
  engagementLoading.value = true
  try {
    const data = await getPostEngagement(slug)
    if (String(route.params.slug) === slug) engagement.value = data
  } catch (error) {
    showInteractionError(error)
  } finally {
    if (String(route.params.slug) === slug) engagementLoading.value = false
  }
}

async function load() {
  controller?.abort()
  const request = new AbortController()
  controller = request
  loading.value = true
  missing.value = false
  denied.value = false
  post.value = null
  interactionError.value = ""
  commentBody.value = ""
  if (!preview.value) void reader.initialize()
  const isPreview = preview.value
  const path = isPreview ? `/preview/${encodeURIComponent(String(route.params.id))}` : `/posts/${encodeURIComponent(String(route.params.slug))}`
  const updateMetadata = beginMetadata("archives", isPreview ? "/" : path)
  try {
    const slug = String(route.params.slug)
    const data = preview.value ? await getArchivePreview(String(route.params.id), request.signal) : await getArchive<PostDetail>(
      `posts/${encodeURIComponent(slug)}/`,
      request.signal,
    )
    if (request.signal.aborted) return
    post.value = data
    if (isPreview) {
      const metadata = siteMetadata("archives", "/", `Preview: ${data.title} | OrganicArchives`)
      metadata.description = "Private editorial preview."
      updateMetadata(metadata)
    } else updateMetadata(articleMetadata(data as PostDetail))
    if (!preview.value) void loadEngagement(slug)
  } catch (error) {
    if (!request.signal.aborted) {
      missing.value = error instanceof ArchiveError && error.status === 404
      denied.value = preview.value && error instanceof ArchiveError && [401, 403].includes(error.status)
    }
  } finally {
    if (!request.signal.aborted) loading.value = false
  }
}

async function toggleLike() {
  if (!post.value || !reader.isAuthenticated) return
  likeBusy.value = true
  interactionError.value = ""
  try {
    const result = engagement.value.liked
      ? await unlikePost(post.value.slug)
      : await likePost(post.value.slug)
    engagement.value.liked = result.liked
    engagement.value.like_count = result.like_count
  } catch (error) {
    showInteractionError(error)
  } finally {
    likeBusy.value = false
  }
}

async function submitComment() {
  if (!post.value || !reader.isAuthenticated || !commentBody.value.trim()) return
  commentBusy.value = true
  interactionError.value = ""
  try {
    const comment = await addPostComment(post.value.slug, commentBody.value)
    engagement.value.comments.push(comment)
    engagement.value.comment_count += 1
    commentBody.value = ""
  } catch (error) {
    showInteractionError(error)
  } finally {
    commentBusy.value = false
  }
}

async function toggleSubscription() {
  interactionError.value = ""
  try {
    await reader.toggleSubscription()
  } catch (error) {
    showInteractionError(error)
  }
}

watch(() => [route.name, route.params.slug, route.params.id], load, { immediate: true })
onUnmounted(() => controller?.abort())
</script>

<template>
  <div class="reader-wrap">
    <a v-if="preview" class="back-link" :href="editUrl">← Back to editing</a>
    <RouterLink v-else class="back-link" to="/">← Back to the feed</RouterLink>
    <aside v-if="preview" class="draft-preview-notice" role="status">
      <strong>{{ post ? previewLabel : "Editorial preview" }}</strong>
      <p>Review the saved post before release. Only authorised publishers can open this preview.</p>
    </aside>
    <div v-if="loading" class="feed-state" role="status">
      <h1>Opening the story…</h1>
    </div>
    <div v-else-if="!post" class="feed-state">
      <h1>
        {{
          denied ? "Publisher access is required." : missing
            ? "This post isn’t available."
            : "The post couldn’t be loaded."
        }}
      </h1>
      <p>
        {{
          preview && !missing
            ? "Sign in through Publisher login, then try again. Your account needs Archives post permission."
            : missing
            ? "It may have moved or is no longer published."
            : "Please try again in a moment."
        }}
      </p>
      <a v-if="preview && !missing" class="text-link" :href="publisherUrl">Publisher login →</a>
      <button v-if="!missing" class="solid-button" @click="load">
        Try again</button
      ><RouterLink v-else class="text-link" to="/"
        >Browse the archives →</RouterLink
      >
    </div>
    <article v-else class="reader">
      <header>
        <div class="post-kicker">
          <RouterLink
            class="kind-badge"
            :class="post.kind"
            :to="{ name: 'feed', query: { kind: post.kind } }"
            >{{ kindLabels[post.kind] }}</RouterLink
          ><span v-if="post.topic" class="topic-label">{{ post.topic }}</span>
        </div>
        <h1>{{ post.title }}</h1>
        <p class="reader-excerpt">{{ post.excerpt }}</p>
        <div class="reader-byline">
          <span class="author-avatar" aria-hidden="true">{{
            post.author_name.charAt(0)
          }}</span>
          <div>
            <strong>{{ post.author_name }}</strong>
            <div class="post-meta">
              <time v-if="post.published_at" :datetime="post.published_at">{{
                formatDate(post.published_at)
              }}</time
              ><span v-else>Not published</span><span aria-hidden="true">·</span
              ><span>{{ post.reading_minutes }} min read</span>
            </div>
          </div>
        </div>
      </header>
      <figure v-if="post.cover_image" class="reader-cover">
        <img :src="post.cover_image" :alt="post.cover_alt" />
      </figure>
      <div class="reader-body">
        <template v-for="block in post.blocks" :key="block.id">
          <div
            v-if="block.kind === 'text'"
            class="text-block markdown-block"
            v-html="renderMarkdown(block.text)" />
          <h2 v-else-if="block.kind === 'heading'">{{ block.text }}</h2>
          <figure v-else-if="block.kind === 'quote'" class="quote-block">
            <blockquote>{{ block.text }}</blockquote>
            <figcaption v-if="block.caption">{{ block.caption }}</figcaption>
          </figure>
          <figure v-else-if="block.kind === 'image' && block.image">
            <img :src="block.image" :alt="block.alt_text" loading="lazy" />
            <figcaption v-if="block.caption">{{ block.caption }}</figcaption>
          </figure>
          <figure v-else-if="block.kind === 'video' && block.video">
            <video
              :src="block.video"
              controls
              playsinline
              preload="metadata"
              :aria-label="block.caption || 'Post video'">
              <a :href="block.video">Download video</a>
            </video>
            <figcaption v-if="block.caption">{{ block.caption }}</figcaption>
          </figure>
          <figure v-else-if="block.kind === 'embed' && block.embed_url">
            <iframe
              :src="block.embed_url"
              :title="block.caption || 'Post video'"
              loading="lazy"
              referrerpolicy="strict-origin-when-cross-origin"
              allow="encrypted-media; fullscreen; picture-in-picture"
              allowfullscreen
              sandbox="allow-scripts allow-same-origin allow-presentation" />
            <figcaption v-if="block.caption">{{ block.caption }}</figcaption>
          </figure>
        </template>
      </div>
      <section v-if="!preview" class="reader-community" aria-labelledby="community-title">
        <header>
          <div>
            <span class="eyebrow">THE READER CIRCLE</span>
            <h2 id="community-title">A place to respond.</h2>
          </div>
          <div class="reader-actions">
            <button
              v-if="reader.isAuthenticated"
              type="button"
              class="interaction-button"
              :class="{ selected: engagement.liked }"
              :aria-pressed="engagement.liked"
              :disabled="likeBusy || engagementLoading"
              @click="toggleLike">
              <span aria-hidden="true">{{ engagement.liked ? "♥" : "♡" }}</span>
              {{ engagement.like_count }}
              {{ engagement.like_count === 1 ? "like" : "likes" }}
            </button>
            <RouterLink v-else class="interaction-button" :to="readerLink">
              ♡ {{ engagement.like_count }}
              {{ engagement.like_count === 1 ? "like" : "likes" }}
            </RouterLink>
            <button
              v-if="reader.isAuthenticated"
              type="button"
              class="interaction-button"
              :class="{ selected: reader.subscribed }"
              :aria-pressed="reader.subscribed"
              :disabled="reader.busy"
              @click="toggleSubscription">
              {{ reader.subscribed ? "Subscribed" : "Subscribe" }}
            </button>
          </div>
        </header>

        <p v-if="interactionError" class="reader-feedback reader-feedback--error" role="alert">
          {{ interactionError }}
        </p>

        <div class="comment-heading">
          <h3>
            {{ engagement.comment_count }}
            {{ engagement.comment_count === 1 ? "comment" : "comments" }}
          </h3>
        </div>
        <ol v-if="engagement.comments.length" class="comment-list">
          <li v-for="comment in engagement.comments" :key="comment.id">
            <div class="comment-meta">
              <strong>{{ comment.author_name }}</strong>
              <span v-if="comment.is_mine">You</span>
              <time :datetime="comment.created_at">{{ formatDate(comment.created_at) }}</time>
            </div>
            <p>{{ comment.body }}</p>
          </li>
        </ol>
        <p v-else-if="!engagementLoading" class="empty-comments">
          No comments yet. You can start the conversation.
        </p>

        <form v-if="reader.isAuthenticated" class="comment-form" @submit.prevent="submitComment">
          <label for="reader-comment">Leave a comment as {{ reader.displayName }}</label>
          <textarea
            id="reader-comment"
            v-model="commentBody"
            maxlength="1200"
            rows="4"
            placeholder="Share something thoughtful…"
            required />
          <div>
            <small>{{ commentBody.length }}/1200</small>
            <button class="solid-button" type="submit" :disabled="commentBusy || !commentBody.trim()">
              {{ commentBusy ? "Posting…" : "Post comment" }}
            </button>
          </div>
        </form>
        <div v-else class="reader-sign-in-note">
          <p>Sign in with a reader account to subscribe, like, or comment.</p>
          <RouterLink class="solid-button" :to="readerLink">Reader sign in</RouterLink>
        </div>
      </section>
      <footer class="reader-end">
        <span class="archive-monogram" aria-hidden="true"
          >OA<span>.</span></span
        >
        <div>
          <strong>More from the archives</strong
          ><RouterLink to="/"
            >Back to all articles, news, and updates →</RouterLink
          >
        </div>
      </footer>
    </article>
  </div>
</template>
