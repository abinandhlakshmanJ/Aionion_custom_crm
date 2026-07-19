<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 font-sans"
  >
    <div class="relative w-full max-w-3xl bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col max-h-[85vh]">
      <!-- Header Bar -->
      <div class="flex items-center justify-between px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-blue-600" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
          </svg>
          <h3 class="text-base font-bold text-gray-900">{{ __('Send Email') }}</h3>
        </div>
        <button
          class="p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-200 rounded-lg transition-colors font-bold text-sm"
          @click="close"
        >
          ✕
        </button>
      </div>

      <!-- Official Frappe CRM Email Editor -->
      <div class="flex-1 overflow-y-auto p-4 bg-white">
        <EmailEditor
          ref="emailEditorRef"
          v-model="documentModel"
          v-model:content="emailContent"
          v-model:attachments="attachments"
          doctype="CRM Lead"
          :placeholder="__('Write your email message here...')"
          :submit-button-props="{
            loading: sending,
            onClick: handleSendEmail,
          }"
          :discard-button-props="{
            onClick: close,
          }"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { toast, call } from 'frappe-ui'
import EmailEditor from '@crm/components/EmailEditor.vue'

const open = defineModel({ type: Boolean, default: false })
const emailEditorRef = ref(null)
const sending = ref(false)
const emailContent = ref('')
const attachments = ref([])
const documentModel = ref({
  name: '',
  email: '',
})

async function handleSendEmail() {
  const ed = emailEditorRef.value
  if (!ed || !ed.toEmails?.length) {
    toast.error(__('Please specify at least one recipient email address.'))
    return
  }

  sending.value = true
  try {
    await call('aionion_custom.api.send_custom_email', {
      recipients: ed.toEmails,
      cc: ed.ccEmails || [],
      bcc: ed.bccEmails || [],
      subject: ed.subject || 'No Subject',
      content: emailContent.value,
      attachments: attachments.value.map((x) => x.name),
      sender: ed.fromEmail || undefined,
    })
    toast.success(__('Email sent and recorded successfully!'))
    close()
  } catch (error) {
    toast.error(__('Failed to send email: {0}', [error.message || error]))
  } finally {
    sending.value = false
  }
}

function close() {
  emailContent.value = ''
  attachments.value = []
  open.value = false
}
</script>
