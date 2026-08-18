<script lang="ts">
	import General from './Settings/General.svelte';
	import Appearance from './Settings/Appearance.svelte';
	import AudioSettings from './Admin/AudioSettings.svelte';
	import Account from './Settings/Account.svelte';
	import Icon from './Icon.svelte';

	let activeSubTab = $state<'general' | 'appearance' | 'audio' | 'account'>('general');
</script>

<div class="h-full w-full flex flex-col bg-white dark:bg-black text-gray-900 dark:text-gray-100 overflow-hidden">
	<div class="p-6 border-b border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
		<h1 class="text-xl font-semibold">Settings</h1>
		<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Manage your assistant preferences and settings</p>
	</div>

	<div class="flex-1 flex min-h-0 overflow-hidden">
		<!-- Sub-tab navigation -->
		<div class="w-48 border-r border-gray-200 dark:border-gray-800 p-3 flex flex-col gap-1 bg-gray-50/30 dark:bg-gray-900/30">
			<button
				class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors {activeSubTab === 'general' ? 'bg-gray-200/70 dark:bg-white/10 text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5'}"
				onclick={() => activeSubTab = 'general'}
			>
				<Icon name="sliders" size={16} />
				<span>General</span>
			</button>

			<button
				class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors {activeSubTab === 'appearance' ? 'bg-gray-200/70 dark:bg-white/10 text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5'}"
				onclick={() => activeSubTab = 'appearance'}
			>
				<Icon name="sun" size={16} />
				<span>Appearance</span>
			</button>

			<button
				class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors {activeSubTab === 'audio' ? 'bg-gray-200/70 dark:bg-white/10 text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5'}"
				onclick={() => activeSubTab = 'audio'}
			>
				<Icon name="mic" size={16} />
				<span>Audio & Speech</span>
			</button>

			<button
				class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors {activeSubTab === 'account' ? 'bg-gray-200/70 dark:bg-white/10 text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5'}"
				onclick={() => activeSubTab = 'account'}
			>
				<Icon name="user" size={16} />
				<span>Account</span>
			</button>
		</div>

		<!-- Sub-tab panel -->
		<div class="flex-1 p-6 overflow-y-auto">
			{#if activeSubTab === 'general'}
				<General />
			{:else if activeSubTab === 'appearance'}
				<Appearance />
			{:else if activeSubTab === 'audio'}
				<AudioSettings />
			{:else if activeSubTab === 'account'}
				<Account />
			{/if}
		</div>
	</div>
</div>
