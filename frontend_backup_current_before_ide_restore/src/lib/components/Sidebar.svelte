<script lang="ts">
	import { sidebarOpen, sidebarWidth, activeView, type MainView } from '$lib/stores';
	import { t } from '$lib/i18n';
	import Icon from './Icon.svelte';
	import SettingsModal from './SettingsModal.svelte';

	interface Props {
		gitSettingsAvailable?: boolean;
	}

	let { gitSettingsAvailable = false }: Props = $props();
	let showSettings = $state(false);
	
	function closeSidebar() {
		sidebarOpen.set(false);
	}

	function setView(view: MainView) {
		activeView.set(view);
		if (typeof window !== 'undefined' && window.innerWidth < 768) {
			closeSidebar();
		}
	}
</script>

{#if $sidebarOpen}
	<button
		class="fixed inset-0 bg-black/50 z-40 cursor-default md:hidden"
		onclick={closeSidebar}
		aria-label={$t('sidebar.closeSidebar')}
	></button>

	<aside class="sidebar">
		<div class="px-3 py-4 flex flex-col gap-1">
			<button
				class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors {$activeView === 'home' ? 'bg-gray-100 dark:bg-white/10 text-gray-900 dark:text-white font-medium' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white'}"
				onclick={() => setView('home')}
			>
				<Icon name="message-square" size={18} />
				<span>Home</span>
			</button>

			<button
				class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors {$activeView === 'files' ? 'bg-gray-100 dark:bg-white/10 text-gray-900 dark:text-white font-medium' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white'}"
				onclick={() => setView('files')}
			>
				<Icon name="folder" size={18} />
				<span>Files</span>
			</button>

			<button
				class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors {$activeView === 'excel' ? 'bg-gray-100 dark:bg-white/10 text-gray-900 dark:text-white font-medium' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white'}"
				onclick={() => setView('excel')}
			>
				<Icon name="file-spreadsheet" size={18} />
				<span>Excel</span>
			</button>
		</div>

		<div class="mt-auto p-3">
			<button
				class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors {$activeView === 'settings' ? 'bg-gray-100 dark:bg-white/10 text-gray-900 dark:text-white font-medium' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-white'}"
				onclick={() => setView('settings')}
			>
				<Icon name="settings" size={18} />
				<span>Settings</span>
			</button>
		</div>
	</aside>
{/if}

<style>
	@reference "../../app.css";

	.sidebar {
		position: fixed;
		left: 0;
		top: 0;
		bottom: 0;
		width: 16rem; /* 256px */
		z-index: 50;
		display: flex;
		flex-direction: column;
		background: var(--app-bg);
		color: var(--app-fg);
		border-right: 1px solid var(--app-border);
		padding-top: env(safe-area-inset-top, 0);
	}

	:global(.dark) .sidebar {
		border-right-color: var(--app-border);
	}

	@media (min-width: 768px) {
		.sidebar {
			position: relative;
			z-index: auto;
		}
	}
</style>
