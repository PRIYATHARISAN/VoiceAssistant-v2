<script lang="ts">
	import { t } from '$lib/i18n';
	import { session } from '$lib/session';
	import { activeView, currentWorkspace, appVersion, showChangelog } from '$lib/stores';
	import Icon from './Icon.svelte';
	import DictateButton from './chat/DictateButton.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { getWelcome } from '$lib/apis/state';

	const welcomeName = $derived($session?.display_name || $session?.username);
	const greetingTime = $derived.by(() => {
		const hour = new Date().getHours();
		if (hour < 5) return 'lateNight';
		if (hour < 7) return 'superEarly';
		if (hour < 11) return 'morning';
		if (hour < 13) return 'noon';
		if (hour < 17) return 'afternoon';
		if (hour < 21) return 'evening';
		return 'night';
	});
	const greetingVariant = $derived(new Date().getDate() % 3);
	const greetingNameMarker = '\uE000';

	let welcomeData = $state<{
		recent: { name: string; path: string }[];
	} | null>(null);

	let inputText = $state('');

	onMount(() => {
		getWelcome().then((data) => {
			welcomeData = data as any;
		}).catch(() => {});
	});

	function handleSubmit() {
		const trimmed = inputText.trim();
		if (!trimmed) return;
		window.dispatchEvent(new CustomEvent('cptr:new-chat-from-home', { detail: { text: trimmed, files: [] } }));
		inputText = '';
	}

	function handleDictate(text: string) {
		inputText = inputText ? `${inputText} ${text}` : text;
	}
</script>

<div class="h-full w-full flex flex-col items-center justify-center p-6 overflow-y-auto bg-white dark:bg-black">
	<div class="w-full max-w-2xl flex flex-col gap-8">
		<!-- Greeting -->
		<div class="text-center">
			<h1 class="text-3xl font-semibold tracking-tight text-gray-900 dark:text-white mb-2">
				{#if welcomeName}
					{@const greeting = $t(`home.greeting.${greetingTime}.${greetingVariant}`, {
						name: greetingNameMarker
					})}
					{@const [beforeName, afterName] = greeting.split(greetingNameMarker)}
					{beforeName}<span class="capitalize">{welcomeName}</span>{afterName}
				{:else}
					What can I help you with today?
				{/if}
			</h1>
			<p class="text-gray-500 dark:text-gray-400">
				Ask questions, analyze spreadsheets, manage files, or dictate voice commands.
			</p>
		</div>

		<!-- Main Input Shell -->
		<div class="w-full relative shadow-sm rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
			<div class="flex items-center gap-2 p-3">
				<div class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
					<DictateButton ontext={handleDictate} />
				</div>
				<input 
					type="text" 
					placeholder="Ask Sofie anything or use voice dictation..." 
					class="flex-1 bg-transparent border-none focus:outline-none text-gray-900 dark:text-white placeholder-gray-400 text-sm"
					bind:value={inputText}
					onkeydown={(e) => {
						if (e.key === 'Enter') {
							handleSubmit();
						}
					}}
				/>
				<button 
					type="button"
					class="p-2 text-white bg-blue-600 hover:bg-blue-700 transition-colors rounded-full shrink-0"
					onclick={handleSubmit}
					aria-label="Send query"
				>
					<Icon name="arrow-up" size={16} />
				</button>
			</div>
		</div>

		<!-- Recent Activity / Workspaces -->
		{#if welcomeData?.recent?.length}
			<div class="mt-4">
				<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">Recent Workspaces</h2>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					{#each welcomeData.recent.slice(0, 4) as item}
						<button 
							class="flex items-center gap-3 p-3 rounded-xl border border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 hover:bg-gray-50 dark:hover:bg-white/5 transition-all text-left"
							onclick={() => {
								window.location.href = `/?workspace=${encodeURIComponent(item.path)}`;
							}}
						>
							<div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
								<Icon name="folder" size={18} />
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-gray-900 dark:text-white truncate">{item.name}</p>
								<p class="text-xs text-gray-500 dark:text-gray-400 truncate">{item.path}</p>
							</div>
						</button>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>

