<script lang="ts">
	import { currentWorkspace } from '$lib/stores';
	import FileBrowser from './FileBrowser.svelte';
	import WorkspacePicker from './WorkspacePicker.svelte';
	import { workspaceList } from '$lib/stores';
	import { goto } from '$app/navigation';
</script>

<div class="h-full w-full flex flex-col bg-white dark:bg-black">
	{#if $currentWorkspace}
		<div class="flex-1 min-h-0 overflow-hidden relative">
			<FileBrowser />
		</div>
	{:else}
		<div class="h-full w-full flex flex-col items-center justify-center p-6">
			<div class="w-full max-w-md text-center">
				<h2 class="text-xl font-semibold mb-2">No Workspace Selected</h2>
				<p class="text-gray-500 mb-6">Select a workspace to view files.</p>
				<WorkspacePicker 
					workspaces={$workspaceList}
					onchoose={(path) => {
						window.location.href = `/?workspace=${encodeURIComponent(path)}`;
					}}
					oncancel={() => {}}
				/>
			</div>
		</div>
	{/if}
</div>
