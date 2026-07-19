<template>
  <div class="flex flex-col h-screen w-full bg-surface-base font-sans overflow-hidden text-ink-gray-9">
    <!-- Top Header Bar -->
    <header class="flex items-center justify-between px-6 py-3 border-b bg-surface-modal shrink-0">
      <div class="flex items-center gap-3">
        <h1 class="text-xl font-bold text-ink-gray-9">{{ __('Emails') }}</h1>
      </div>

      <div class="flex items-center gap-3 w-1/3">
        <TextInput
          v-model="searchQuery"
          type="text"
          class="w-full"
          :placeholder="__('Search emails...')"
        />
      </div>

      <div class="flex items-center gap-2">
        <Button
          :label="__('Refresh')"
          variant="outline"
          :loading="emailResource.loading"
          @click="emailResource.reload()"
        />
        <Button
          :label="__('+ Compose Email')"
          variant="solid"
          @click="showComposeModal = true"
        />
      </div>
    </header>

    <!-- Main Content Layout -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Left Folder Navigation -->
      <aside class="w-56 p-4 border-r bg-surface-gray-1 flex flex-col gap-1 shrink-0">
        <button
          v-for="folder in folders"
          :key="folder.id"
          class="flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeFolder === folder.id ? 'bg-surface-gray-3 text-ink-gray-9 font-semibold' : 'text-ink-gray-7 hover:bg-surface-gray-2'"
          @click="selectFolder(folder.id)"
        >
          <span>{{ __(folder.label) }}</span>
          <span v-if="folder.id === 'inbox' && inboxCount > 0" class="text-xs px-2 py-0.5 rounded-full bg-surface-gray-4 text-ink-gray-8">
            {{ inboxCount }}
          </span>
          <span v-else-if="folder.id === 'sent' && sentCount > 0" class="text-xs px-2 py-0.5 rounded-full bg-surface-gray-4 text-ink-gray-8">
            {{ sentCount }}
          </span>
          <span v-else-if="folder.id === 'drafts' && draftCount > 0" class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold">
            {{ draftCount }}
          </span>
          <span v-else-if="folder.id === 'failed' && failedCount > 0" class="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-bold">
            {{ failedCount }}
          </span>
        </button>
      </aside>

      <!-- Center Email Content -->
      <main class="flex-1 bg-surface-modal flex flex-col overflow-hidden">
        <!-- Email Detail View -->
        <div v-if="activeEmail" class="flex flex-col h-full overflow-hidden">
          <div class="flex items-center justify-between px-6 py-3 border-b bg-surface-gray-1">
            <div class="flex items-center gap-3">
              <Button
                variant="ghost"
                :label="__('← Back')"
                @click="activeEmail = null"
              />
              <h2 class="text-base font-bold text-ink-gray-9">{{ activeEmail.subject || __('(No Subject)') }}</h2>
            </div>
            <span v-if="activeEmail.sent_or_received === 'Failed'" class="px-2.5 py-1 text-xs font-bold rounded-full bg-red-100 text-red-700">
              Failed Delivery Error
            </span>
          </div>

          <div class="flex-1 p-6 overflow-y-auto">
            <div class="flex items-start gap-4 mb-4 border-b pb-4">
              <div class="w-10 h-10 rounded-full bg-surface-gray-4 text-ink-gray-9 flex items-center justify-center font-bold text-base">
                {{ (activeEmail.sender || 'U').charAt(0).toUpperCase() }}
              </div>
              <div class="flex-1">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-sm text-ink-gray-9">{{ activeEmail.sender }}</span>
                  <span class="text-xs text-ink-gray-5">{{ formatDate(activeEmail.communication_date || activeEmail.creation) }}</span>
                </div>
                <div class="text-xs text-ink-gray-6 mt-1">To: {{ activeEmail.recipients }}</div>
              </div>
            </div>

            <!-- Error Stack Trace if Failed -->
            <div v-if="activeEmail.error" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
              <h4 class="text-xs font-bold text-red-800 uppercase tracking-wider mb-2">SMTP Error Trace</h4>
              <pre class="text-xs text-red-700 font-mono whitespace-pre-wrap overflow-x-auto">{{ activeEmail.error }}</pre>
            </div>

            <div class="text-sm text-ink-gray-8 leading-relaxed pt-2" v-html="activeEmail.content || activeEmail.message"></div>
          </div>
        </div>

        <!-- Email List View -->
        <div v-else class="flex flex-col h-full">
          <!-- Loading State -->
          <div v-if="emailResource.loading" class="flex-1 flex flex-col items-center justify-center p-8 text-ink-gray-5">
            <span>{{ __('Loading emails...') }}</span>
          </div>

          <!-- Empty State -->
          <div v-else-if="filteredEmails.length === 0" class="flex-1 flex flex-col items-center justify-center p-12 text-center">
            <h3 class="text-base font-semibold text-ink-gray-9 mb-1">{{ __('No emails found') }}</h3>
            <p class="text-xs text-ink-gray-6 max-w-sm mb-4">
              {{ __('There are no emails in this folder.') }}
            </p>
            <Button
              :label="__('+ Compose Email')"
              variant="solid"
              @click="showComposeModal = true"
            />
          </div>

          <!-- Email Rows -->
          <div v-else class="flex-1 overflow-y-auto divide-y">
            <div
              v-for="email in filteredEmails"
              :key="email.name"
              class="flex items-center gap-4 px-6 py-3.5 hover:bg-surface-gray-1 cursor-pointer transition-colors select-none"
              @click="activeEmail = email"
            >
              <div class="w-48 truncate text-sm font-semibold text-ink-gray-9 flex items-center gap-2">
                <span v-if="email.sent_or_received === 'Failed'" class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>
                <span>{{ email.sender || email.recipients }}</span>
              </div>
              <div class="flex-1 flex items-center gap-2 truncate text-sm">
                <span class="font-medium" :class="email.sent_or_received === 'Failed' ? 'text-red-700 font-bold' : 'text-ink-gray-9'">
                  {{ email.subject || __('(No Subject)') }}
                </span>
                <span class="text-ink-gray-5 truncate">- {{ stripHtml(email.content || email.message) }}</span>
              </div>
              <div class="text-xs text-ink-gray-5 shrink-0">
                {{ formatDate(email.communication_date || email.creation) }}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- Official Compose Modal -->
    <SendEmailModal v-model="showComposeModal" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createResource, Button, TextInput } from 'frappe-ui'
import SendEmailModal from '@custom/components/Modals/SendEmailModal.vue'

const searchQuery = ref('')
const activeFolder = ref('inbox')
const showComposeModal = ref(false)
const activeEmail = ref(null)

const folders = ref([
  { id: 'inbox', label: 'Inbox' },
  { id: 'sent', label: 'Sent' },
  { id: 'drafts', label: 'Drafts' },
  { id: 'failed', label: 'Failed / Errors' },
  { id: 'all', label: 'All Emails' },
])

const emailResource = createResource({
  url: 'aionion_custom.api.get_email_hub_data',
  auto: true,
})

const communications = computed(() => {
  return emailResource.data?.communications || []
})

const failedEmails = computed(() => {
  return emailResource.data?.failed_emails || []
})

const allItems = computed(() => {
  return [...communications.value, ...failedEmails.value]
})

const inboxCount = computed(() => {
  return communications.value.filter((e) => e.sent_or_received === 'Received').length
})

const sentCount = computed(() => {
  return communications.value.filter((e) => e.sent_or_received === 'Sent').length
})

const draftCount = computed(() => {
  return communications.value.filter((e) => e.status === 'Draft' || e.sent_or_received === 'Draft').length
})

const failedCount = computed(() => {
  return failedEmails.value.length
})

const filteredEmails = computed(() => {
  return allItems.value.filter((email) => {
    let matchesFolder = true
    if (activeFolder.value === 'sent') matchesFolder = email.sent_or_received === 'Sent'
    else if (activeFolder.value === 'inbox') matchesFolder = email.sent_or_received === 'Received'
    else if (activeFolder.value === 'drafts') matchesFolder = email.status === 'Draft' || email.sent_or_received === 'Draft'
    else if (activeFolder.value === 'failed') matchesFolder = email.sent_or_received === 'Failed'

    const query = searchQuery.value.toLowerCase()
    const matchesSearch =
      !query ||
      (email.sender && email.sender.toLowerCase().includes(query)) ||
      (email.subject && email.subject.toLowerCase().includes(query)) ||
      (email.content && email.content.toLowerCase().includes(query)) ||
      (email.error && email.error.toLowerCase().includes(query))
    return matchesFolder && matchesSearch
  })
})

function selectFolder(id) {
  activeFolder.value = id
  activeEmail.value = null
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function stripHtml(html) {
  if (!html) return ''
  return html.replace(/<[^>]*>?/gm, '').slice(0, 120)
}
</script>
