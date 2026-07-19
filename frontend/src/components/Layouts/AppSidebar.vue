<template>
  <div
    class="relative flex h-full flex-col justify-between transition-all duration-300 ease-in-out"
    :class="isSidebarCollapsed ? 'w-12' : 'w-[220px]'"
  >
    <div class="p-2">
      <UserDropdown :isCollapsed="isSidebarCollapsed" />
    </div>
    <div class="flex-1 overflow-y-auto">
      <div class="flex flex-col">
        <SidebarLink
          id="notifications-btn"
          :label="__('Notifications')"
          :icon="NotificationsIcon"
          :isCollapsed="isSidebarCollapsed"
          class="relative mx-2 my-[1.5px]"
          @click="() => toggleNotificationPanel()"
        >
          <template #right>
            <Badge
              v-if="!isSidebarCollapsed && unreadNotificationsCount"
              :label="unreadNotificationsCount"
              variant="subtle"
            />
            <div
              v-else-if="unreadNotificationsCount"
              class="absolute -left-1.5 top-1 z-20 h-[5px] w-[5px] translate-x-6 translate-y-1 rounded-full bg-surface-gray-9 ring-1 ring-white"
            />
          </template>
        </SidebarLink>
      </div>
      <div v-for="view in allViews" :key="view.label">
        <div class="mx-2 my-1.5" />
        <Section
          :label="view.name"
          :hideLabel="view.hideLabel"
          :opened="view.opened"
        >
          <template #header="{ opened, hide, toggle }">
            <div
              v-if="!hide"
              class="flex items-center cursor-pointer gap-1.5 text-base text-ink-gray-5 transition-all duration-300 ease-in-out"
              :class="
                isSidebarCollapsed
                  ? 'h-0 overflow-hidden opacity-0'
                  : 'px-4 pt-[11px] pb-2.5 w-auto opacity-100'
              "
              @click="toggle()"
            >
              <span
                class="lucide-chevron-right h-4 text-ink-gray-9 transition-all duration-300 ease-in-out"
                :class="{ 'rotate-90': opened }"
                aria-hidden="true"
              />
              <span>{{ __(view.name) }}</span>
            </div>
          </template>
          <nav class="flex flex-col">
            <SidebarLink
              v-for="link in view.views"
              :key="link.label"
              :icon="link.icon"
              :label="__(link.label)"
              :to="link.to"
              :isCollapsed="isSidebarCollapsed"
              class="mx-2 my-[1.5px]"
              @click="link.onClick && link.onClick()"
            />
          </nav>
        </Section>
      </div>
    </div>
    <div class="m-2 flex flex-col gap-1">
      <div class="flex flex-col gap-2 mb-1">
        <SalesHierarchyBanner
          v-if="showSalesHierarchyBanner"
          :isSidebarCollapsed="isSidebarCollapsed"
        />
        <SignupBanner
          v-if="isDemoSite"
          :isSidebarCollapsed="isSidebarCollapsed"
          :afterSignup="() => capture('signup_from_demo_site')"
        />
        <TrialBanner
          v-if="isFCSite"
          :isSidebarCollapsed="isSidebarCollapsed"
          :afterUpgrade="() => capture('upgrade_plan_from_trial_banner')"
        />
        <GettingStartedBanner
          v-if="!isOnboardingStepsCompleted"
          :isSidebarCollapsed="isSidebarCollapsed"
        />
      </div>
      <SidebarLink
        v-if="isManager() && isDemoDataCreated"
        class="text-ink-red-6 hover:bg-surface-red-2 focus:bg-surface-red-2"
        :label="__('Clear Demo Data')"
        :isCollapsed="isSidebarCollapsed"
        @click="() => clearDemoData()"
      >
        <template #icon>
          <BrushCleaningIcon class="size-4" />
        </template>
      </SidebarLink>
      <SidebarLink
        :label="__('Settings')"
        :icon="LucideSettings"
        :isCollapsed="isSidebarCollapsed"
        @click="
          () => {
            showSettings = true
            activeSettingsPage = 'General'
          }
        "
      />
      <SidebarLink
        :label="__('Help')"
        :icon="HelpIcon"
        :isCollapsed="isSidebarCollapsed"
        @click="() => (showHelpModal = true)"
      />
      <SidebarLink
        :label="__('Collapse')"
        :icon="CollapseSidebar"
        :isCollapsed="isSidebarCollapsed"
        class="hidden sm:flex"
        :class="{ '[&_svg]:rotate-180': isSidebarCollapsed }"
        @click="isSidebarCollapsed = !isSidebarCollapsed"
      />
    </div>
    <Notifications />
    <Settings />
    <HelpModal
      v-if="showHelpModal"
      v-model="showHelpModal"
      v-model:articles="articles"
      :logo="CRMLogo"
      :afterSkip="(step) => capture('onboarding_step_skipped_' + step)"
      :afterSkipAll="() => capture('onboarding_steps_skipped')"
      :afterReset="(step) => capture('onboarding_step_reset_' + step)"
      :afterResetAll="() => capture('onboarding_steps_reset')"
      docsLink="https://docs.frappe.io/crm"
    />
    <IntermediateStepModal
      v-model="showIntermediateModal"
      :currentStep="currentStep"
    />
    <SendEmailModal v-model="showSendEmailModal" />
  </div>
</template>

<script setup>
import SendEmailModal from '@custom/components/Modals/SendEmailModal.vue'
import BrushCleaningIcon from '~icons/lucide/brush-cleaning'
import LucideLayoutDashboard from '~icons/lucide/layout-dashboard'
import LucideSettings from '~icons/lucide/settings'
import CRMLogo from '@crm/components/Icons/CRMLogo.vue'
import InviteIcon from '@crm/components/Icons/InviteIcon.vue'
import ConvertIcon from '@crm/components/Icons/ConvertIcon.vue'
import CommentIcon from '@crm/components/Icons/CommentIcon.vue'
import EmailIcon from '@crm/components/Icons/EmailIcon.vue'
import WhatsAppIcon from '@crm/components/Icons/WhatsAppIcon.vue'
import StepsIcon from '@crm/components/Icons/StepsIcon.vue'
import Section from '@crm/components/CollapsibleSection.vue'
import PinIcon from '@crm/components/Icons/PinIcon.vue'
import UserDropdown from '@crm/components/UserDropdown.vue'
import SquareAsterisk from '@crm/components/Icons/SquareAsterisk.vue'
import LeadsIcon from '@crm/components/Icons/LeadsIcon.vue'
import DealsIcon from '@crm/components/Icons/DealsIcon.vue'
import ContactsIcon from '@crm/components/Icons/ContactsIcon.vue'
import OrganizationsIcon from '@crm/components/Icons/OrganizationsIcon.vue'
import NoteIcon from '@crm/components/Icons/NoteIcon.vue'
import TaskIcon from '@crm/components/Icons/TaskIcon.vue'
import PhoneIcon from '@crm/components/Icons/PhoneIcon.vue'
import CollapseSidebar from '@crm/components/Icons/CollapseSidebar.vue'
import NotificationsIcon from '@crm/components/Icons/NotificationsIcon.vue'
import HelpIcon from '@crm/components/Icons/HelpIcon.vue'
import SidebarLink from '@crm/components/SidebarLink.vue'
import Notifications from '@crm/components/Notifications.vue'
import Settings from '@crm/components/Settings/Settings.vue'
import SalesHierarchyBanner from '@crm/components/SalesHierarchyBanner.vue'
import { viewsStore } from '@crm/stores/views'
import {
  unreadNotificationsCount,
  notificationsStore,
} from '@crm/stores/notifications'
import { usersStore } from '@crm/stores/users'
import { sessionStore } from '@crm/stores/session'
import { showSettings, activeSettingsPage } from '@crm/composables/settings'
import { showChangePasswordModal } from '@crm/composables/modals'
import { useBroadcast } from '@crm/composables/useBroadcast.js'
import { call, toast } from 'frappe-ui'
import {
  SignupBanner,
  TrialBanner,
  HelpModal,
  GettingStartedBanner,
  useOnboarding,
  showHelpModal,
  minimize,
  IntermediateStepModal,
  useTelemetry,
} from 'frappe-ui/frappe'
import router from '@/router'
import { useStorage } from '@vueuse/core'
import { useDemoData } from '@crm/composables/demoData'
import { ref, reactive, computed, markRaw, onMounted } from 'vue'

const { getPinnedViews, getPublicViews } = viewsStore()
const { toggle: toggleNotificationPanel } = notificationsStore()
const { capture } = useTelemetry()
const { clearDemoData, isDemoDataCreated } = useDemoData()
const { send } = useBroadcast()

const isSidebarCollapsed = useStorage('isSidebarCollapsed', false)

const isFCSite = ref(window.is_fc_site)
const isDemoSite = ref(window.is_demo_site)
const showSalesHierarchyBanner = ref(!!window.show_sales_hierarchy_banner)

const showSendEmailModal = ref(false)

const links = [
  {
    label: 'Dashboard',
    icon: LucideLayoutDashboard,
    to: 'Dashboard',
  },
  {
    label: 'Leads',
    icon: LeadsIcon,
    to: 'Leads',
  },
  {
    label: 'Notes',
    icon: NoteIcon,
    to: 'Notes',
  },
  {
    label: 'Tasks',
    icon: TaskIcon,
    to: 'Tasks',
  },
  {
    label: 'Call Logs',
    icon: PhoneIcon,
    to: 'Call Logs',
  },
  {
    label: 'Send Email',
    icon: EmailIcon,
    to: 'Email',
  },
  {
    label: 'WhatsApp',
    icon: WhatsAppIcon,
    onClick: () => {
      toast.info(__('WhatsApp option clicked'))
    },
  },
]

const allViews = computed(() => {
  let _views = [
    {
      name: 'All Views',
      hideLabel: true,
      opened: true,
      views: links.filter((link) => {
        if (link.condition) {
          return link.condition()
        }
        return true
      }),
    },
  ]
  if (getPublicViews().length) {
    _views.push({
      name: 'Public Views',
      opened: true,
      views: parseView(getPublicViews()),
    })
  }

  if (getPinnedViews().length) {
    _views.push({
      name: 'Pinned Views',
      opened: true,
      views: parseView(getPinnedViews()),
    })
  }
  return _views
})

function parseView(views) {
  return views.map((view) => {
    return {
      label: view.label,
      icon: getIcon(view.route_name, view.icon),
      to: {
        name: view.route_name,
        params: { viewType: view.type || 'list' },
        query: { view: view.name },
      },
    }
  })
}

function getIcon(routeName, icon) {
  if (icon) return icon

  switch (routeName) {
    case 'Leads':
      return LeadsIcon
    case 'Deals':
      return DealsIcon
    case 'Contacts':
      return ContactsIcon
    case 'Organizations':
      return OrganizationsIcon
    case 'Notes':
      return NoteIcon
    case 'Call Logs':
      return PhoneIcon
    default:
      return PinIcon
  }
}

// onboarding
const { user } = sessionStore()
const { users, isManager } = usersStore()
const { isOnboardingStepsCompleted, setUp } = useOnboarding('frappecrm')

async function getFirstLead() {
  let firstLead = localStorage.getItem('firstLead' + user)
  if (firstLead) return firstLead
  return await call('crm.api.onboarding.get_first_lead')
}

async function getFirstDeal() {
  let firstDeal = localStorage.getItem('firstDeal' + user)
  if (firstDeal) return firstDeal
  return await call('crm.api.onboarding.get_first_deal')
}

const showIntermediateModal = ref(false)
const currentStep = ref({})

const steps = reactive([
  {
    name: 'setup_your_password',
    title: __('Setup your password'),
    icon: markRaw(SquareAsterisk),
    completed: false,
    onClick: () => {
      minimize.value = true
      showChangePasswordModal.value = true
      capture('onboarding_step_clicked_setup_password')
    },
  },
  {
    name: 'create_first_lead',
    title: __('Create your first lead'),
    icon: markRaw(LeadsIcon),
    completed: false,
    onClick: () => {
      minimize.value = true
      router.push({ name: 'Leads' })
      capture('onboarding_step_clicked_create_lead')
    },
  },
  {
    name: 'create_first_deal',
    title: __('Create your first deal'),
    icon: markRaw(DealsIcon),
    completed: false,
    onClick: async () => {
      let firstLead = await getFirstLead()
      if (!firstLead) {
        toast.error(__('Please create a lead first'))
        return
      }

      minimize.value = true
      router.push({ name: 'Lead', params: { leadId: firstLead } })
      capture('onboarding_step_clicked_create_deal')
    },
  },
  {
    name: 'add_an_organization',
    title: __('Add an organization'),
    icon: markRaw(OrganizationsIcon),
    completed: false,
    onClick: () => {
      minimize.value = true
      router.push({ name: 'Organizations' })
      capture('onboarding_step_clicked_add_organization')
    },
  },
  {
    name: 'add_a_contact',
    title: __('Add a contact'),
    icon: markRaw(ContactsIcon),
    completed: false,
    onClick: () => {
      minimize.value = true
      router.push({ name: 'Contacts' })
      capture('onboarding_step_clicked_add_contact')
    },
  },
  {
    name: 'convert_a_lead',
    title: __('Convert a lead into deal'),
    icon: markRaw(ConvertIcon),
    completed: false,
    onClick: async () => {
      let firstLead = await getFirstLead()
      if (!firstLead) {
        toast.error(__('Please create a lead first'))
        return
      }

      minimize.value = true
      router.push({ name: 'Lead', params: { leadId: firstLead } })
      capture('onboarding_step_clicked_convert_lead')
    },
  },
  {
    name: 'log_a_call',
    title: __('Log a call'),
    icon: markRaw(PhoneIcon),
    completed: false,
    onClick: async () => {
      let firstLead = await getFirstLead()
      if (!firstLead) {
        toast.error(__('Please create a lead first'))
        return
      }

      minimize.value = true
      router.push({ name: 'Lead', params: { leadId: firstLead } })
      capture('onboarding_step_clicked_log_call')
    },
  },
  {
    name: 'add_a_note',
    title: __('Add a note'),
    icon: markRaw(NoteIcon),
    completed: false,
    onClick: async () => {
      let firstLead = await getFirstLead()
      if (!firstLead) {
        toast.error(__('Please create a lead first'))
        return
      }

      minimize.value = true
      router.push({ name: 'Lead', params: { leadId: firstLead } })
      capture('onboarding_step_clicked_add_note')
    },
  },
  {
    name: 'send_an_email',
    title: __('Send an email'),
    icon: markRaw(EmailIcon),
    completed: false,
    onClick: async () => {
      let firstLead = await getFirstLead()
      if (!firstLead) {
        toast.error(__('Please create a lead first'))
        return
      }

      minimize.value = true
      router.push({ name: 'Lead', params: { leadId: firstLead } })
      capture('onboarding_step_clicked_send_email')
    },
  },
  {
    name: 'add_a_comment',
    title: __('Add a comment'),
    icon: markRaw(CommentIcon),
    completed: false,
    onClick: async () => {
      let firstLead = await getFirstLead()
      if (!firstLead) {
        toast.error(__('Please create a lead first'))
        return
      }

      minimize.value = true
      router.push({ name: 'Lead', params: { leadId: firstLead } })
      capture('onboarding_step_clicked_add_comment')
    },
  },
  {
    name: 'invite_your_team',
    title: __('Invite your team'),
    icon: markRaw(InviteIcon),
    completed: false,
    onClick: () => {
      if (!isManager()) {
        toast.error(__('Only managers can invite team members'))
        return
      }
      showSettings.value = true
      activeSettingsPage.value = 'Users'
      capture('onboarding_step_clicked_invite_team')
    },
  },
])

const articles = ref([
  {
    title: __('Overview of CRM'),
    description: __('Learn how to use CRM to manage your sales pipeline'),
    link: 'https://docs.frappe.io/crm/user/manual/overview',
  },
  {
    title: __('Views in CRM'),
    description: __(
      'Views are used to display data in CRM like List, Kanban, Group By, etc.',
    ),
    link: 'https://docs.frappe.io/crm/user/manual/views',
  },

  {
    title: __('Customizations in CRM'),
    description: __(
      'CRM provides options to add custom fields, forms, and views.',
    ),
    link: 'https://docs.frappe.io/crm/user/manual/customizations',
  },
])

setUp({
  steps,
  onComplete: () => {
    capture('onboarding_steps_completed')
  },
})

send('test', { message: 'hello' })
</script>
