<script lang="ts">
	import { onMount } from 'svelte';
	import { currentWorkspace } from '$lib/stores';
	import Icon from './Icon.svelte';
	import DictateButton from './chat/DictateButton.svelte';
	import ChatPanel from './chat/ChatPanel.svelte';
	import { getDirectory } from '$lib/apis/files';
	import Spinner from './common/Spinner.svelte';

	let selectedFile = $state<string | null>(null);
	let excelFiles = $state<{ name: string; path: string }[]>([]);
	let loadingFiles = $state(false);
	let commandText = $state('');
	let activeChatId = $state<string | undefined>(undefined);

	async function loadExcelFiles() {
		if (!$currentWorkspace) return;
		loadingFiles = true;
		try {
			const res = await getDirectory($currentWorkspace.path);
			const files: { name: string; path: string }[] = [];
			const collectFiles = (entries: any[]) => {
				for (const item of entries) {
					if (item.type === 'file' && /\.(xlsx|xls|csv|xlsm)$/i.test(item.name)) {
						files.push({ name: item.name, path: item.path });
					}
				}
			};
			if (res.entries) collectFiles(res.entries);
			excelFiles = files;
			if (files.length > 0 && !selectedFile) {
				selectedFile = files[0].path;
			}
		} catch (e) {
			console.error('Failed to load excel files:', e);
		} finally {
			loadingFiles = false;
		}
	}

	onMount(() => {
		loadExcelFiles();
	});

	$effect(() => {
		if ($currentWorkspace) {
			loadExcelFiles();
		}
	});

	function handleExecuteCommand() {
		if (!commandText.trim()) return;
		const fullPrompt = selectedFile
			? `[Target Excel File: ${selectedFile}]\n${commandText.trim()}`
			: commandText.trim();

		if ($currentWorkspace) {
			const key = `cptr:intent:chatDraft:${$currentWorkspace.path}`;
			sessionStorage.setItem(key, fullPrompt);
		}

		window.dispatchEvent(
			new CustomEvent('cptr:excel-command', {
				detail: { prompt: fullPrompt, file: selectedFile }
			})
		);
		commandText = '';
	}

	function handleDictate(text: string) {
		commandText = commandText ? `${commandText} ${text}` : text;
	}
</script>

<div class="h-full w-full flex flex-col bg-white dark:bg-black text-gray-900 dark:text-gray-100 overflow-hidden">
	<!-- Top Bar / Controls for Excel -->
	<div class="p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 flex flex-col gap-3">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400">
					<Icon name="file-spreadsheet" size={20} />
				</div>
				<div>
					<h2 class="text-base font-semibold text-gray-900 dark:text-white">Excel Assistant</h2>
					<p class="text-xs text-gray-500 dark:text-gray-400">Perform natural language commands & automated edits on your spreadsheets</p>
				</div>
			</div>

			<!-- File Selector -->
			<div class="flex items-center gap-2">
				<label for="excel-file-select" class="text-xs font-medium text-gray-600 dark:text-gray-400">Target File:</label>
				{#if loadingFiles}
					<Spinner size={16} />
				{:else if excelFiles.length > 0}
					<select
						id="excel-file-select"
						class="text-xs rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
						bind:value={selectedFile}
					>
						{#each excelFiles as file}
							<option value={file.path}>{file.name}</option>
						{/each}
					</select>
				{:else}
					<span class="text-xs text-gray-400 italic">No .xlsx / .csv files found in workspace</span>
				{/if}
			</div>
		</div>

		<!-- Command Bar -->
		<div class="flex items-center gap-2 mt-1">
			<div class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
				<DictateButton ontext={handleDictate} />
			</div>
			<input 
				type="text"
				placeholder="e.g. Calculate total revenue in column D and add a summary row..."
				class="flex-1 text-xs rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-gray-900 dark:text-white"
				bind:value={commandText}
				onkeydown={(e) => {
					if (e.key === 'Enter') handleExecuteCommand();
				}}
			/>
			<button
				type="button"
				class="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium transition-colors shrink-0"
				onclick={handleExecuteCommand}
			>
				Run Command
			</button>
		</div>
	</div>

	<!-- Main Chat / Execution Panel -->
	<div class="flex-1 min-h-0 relative">
		{#if $currentWorkspace}
			<ChatPanel workspace={$currentWorkspace.path} chatId={activeChatId} />
		{:else}
			<div class="h-full flex items-center justify-center p-6 text-gray-400 text-sm">
				Please select a workspace to run Excel commands.
			</div>
		{/if}
	</div>
</div>

