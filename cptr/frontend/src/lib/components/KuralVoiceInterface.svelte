<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { fetchJSON } from '$lib/apis';
	import { sendMessage, getChat } from '$lib/apis/chat';
	import { defaultModel } from '$lib/stores/chat';
	import { get } from 'svelte/store';
	import KuralOrb from './KuralOrb.svelte';
	import {
		kuralState,
		kuralTranscript,
		kuralResponseText,
		kuralAudioLevel,
		getTtsAudioElement,
		stopTtsPlayback,
		interruptKuralPlayback,
		setTtsAudioPlaybackSource,
		ttsEnabled,
		ttsVoice
	} from '$lib/stores/audio';

	let {
		workspace = null,
		activeChatId = null,
		onSendMessage = null
	} = $props<{
		workspace?: string | null;
		activeChatId?: string | null;
		onSendMessage?: ((text: string) => Promise<void>) | null;
	}>();

	let isContinuousListening = $state(false);
	let currentVoiceChatId = $state<string | null>(activeChatId ?? null);
	let recognition = $state<any>(null);
	let audioCtx = $state<AudioContext | null>(null);
	let analyser = $state<AnalyserNode | null>(null);
	let animFrame = $state<number | null>(null);
	let showTranscriptModal = $state(false);
	let conversationLog = $state<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
	let fallbackRecorder: MediaRecorder | null = null;
	let fallbackStream: MediaStream | null = null;
	let fallbackChunks: Blob[] = [];

	$effect(() => {
		const cid = activeChatId || currentVoiceChatId;
		if (cid && !cid.startsWith('new-') && !cid.startsWith('pending-')) {
			currentVoiceChatId = cid;
			getChat(cid)
				.then((detail) => {
					if (detail?.messages?.length) {
						conversationLog = detail.messages
							.filter((m) => m.content && (m.role === 'user' || m.role === 'assistant'))
							.map((m) => ({ role: m.role, text: m.content }));
						const lastMsg = detail.messages[detail.messages.length - 1];
						if (lastMsg?.role === 'assistant' && lastMsg.content) {
							kuralResponseText.set(lastMsg.content);
						}
					}
				})
				.catch(() => {});
		}
	});

	onMount(() => {
		initSpeechRecognition();
		initAudioAnalyzer();
		// Auto start continuous listening on mount
		startListening();
	});

	onDestroy(() => {
		stopListening(false);
		stopTtsPlayback();
		if (animFrame) cancelAnimationFrame(animFrame);
		if (audioCtx && audioCtx.state !== 'closed') audioCtx.close();
	});

	function initAudioAnalyzer() {
		if (typeof window === 'undefined') return;
		const audio = getTtsAudioElement();
		if (!audio) return;

		audio.addEventListener('play', () => {
			kuralState.set('SPEAKING');
			startAnalyserLoop();
		});

		audio.addEventListener('ended', () => {
			kuralState.set('IDLE');
			kuralAudioLevel.set(0);
			if (animFrame) cancelAnimationFrame(animFrame);
			// AUTOMATICALLY RETURN TO LISTENING
			if (isContinuousListening) {
				setTimeout(() => {
					startListening();
				}, 400);
			}
		});

		audio.addEventListener('pause', () => {
			if ($kuralState === 'SPEAKING') {
				kuralState.set('IDLE');
				kuralAudioLevel.set(0);
			}
		});
	}

	function startAnalyserLoop() {
		if (!analyser) {
			try {
				const audio = getTtsAudioElement();
				if (audio && !audioCtx) {
					const AudioCtxCtor =
						window.AudioContext || (window as any).webkitAudioContext;
					if (AudioCtxCtor) {
						audioCtx = new AudioCtxCtor();
						const srcNode = audioCtx.createMediaElementSource(audio);
						analyser = audioCtx.createAnalyser();
						analyser.fftSize = 64;
						srcNode.connect(analyser);
						analyser.connect(audioCtx.destination);
					}
				}
			} catch {}
		}

		const dataArray = new Uint8Array(analyser ? analyser.frequencyBinCount : 32);

		function updateLevel() {
			if ($kuralState === 'SPEAKING' && analyser) {
				analyser.getByteFrequencyData(dataArray);
				let sum = 0;
				for (let i = 0; i < dataArray.length; i++) {
					sum += dataArray[i];
				}
				const avg = sum / dataArray.length;
				kuralAudioLevel.set(Math.min(avg / 128.0, 1.0));
				animFrame = requestAnimationFrame(updateLevel);
			} else {
				kuralAudioLevel.set(0);
			}
		}

		updateLevel();
	}

	function initSpeechRecognition() {
		if (typeof window === 'undefined') return;
		const SpeechRecognitionCtor =
			(window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

		if (!SpeechRecognitionCtor) return;

		recognition = new SpeechRecognitionCtor();
		recognition.continuous = false;
		recognition.interimResults = true;
		recognition.lang = 'en-US';

		recognition.onstart = () => {
			if ($kuralState !== 'SPEAKING') {
				kuralState.set('LISTENING');
			}
		};

		recognition.onspeechstart = () => {
			// AUTOMATIC VOICE BARGE-IN / HANDS-FREE INTERRUPTION
			if ($kuralState === 'SPEAKING') {
				interruptKuralPlayback();
				if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
					window.speechSynthesis.cancel();
				}
			}
			kuralState.set('SPEECH_DETECTED');
		};

		recognition.onresult = (event: any) => {
			let interim = '';
			let finalTranscript = '';

			for (let i = event.resultIndex; i < event.results.length; ++i) {
				if (event.results[i].isFinal) {
					finalTranscript += event.results[i][0].transcript;
				} else {
					interim += event.results[i][0].transcript;
				}
			}

			const currentText = finalTranscript || interim;
			if (currentText) {
				kuralTranscript.set(currentText);
			}

			if (finalTranscript.trim()) {
				handleUserUtterance(finalTranscript.trim());
			}
		};

		recognition.onerror = (event: any) => {
			if (event.error !== 'no-speech') {
				console.warn('[KuralSpeech] Recognition error:', event.error);
			}
			if (isContinuousListening) {
				setTimeout(() => startListening(), 1000);
			}
		};

		recognition.onend = () => {
			if (
				isContinuousListening &&
				$kuralState !== 'THINKING' &&
				$kuralState !== 'EXECUTING'
			) {
				setTimeout(() => startListening(), 300);
			}
		};
	}

	function startListening() {
		isContinuousListening = true;
		if (recognition) {
			try {
				recognition.start();
			} catch (e) {
				// Already started
			}
			return;
		}

		// Firefox/Electron and some embedded browsers do not expose
		// SpeechRecognition. Use the server STT path instead of silently
		// leaving the Start Voice Turn button inert.
		void startFallbackCapture();
	}

	async function startFallbackCapture() {
		if (fallbackRecorder) return;
		try {
			fallbackStream = await navigator.mediaDevices.getUserMedia({ audio: true });
			fallbackChunks = [];
			fallbackRecorder = new MediaRecorder(fallbackStream);
			fallbackRecorder.ondataavailable = (event) => {
				if (event.data.size > 0) fallbackChunks.push(event.data);
			};
			fallbackRecorder.onstop = () => {
				const blob = new Blob(fallbackChunks, { type: fallbackRecorder?.mimeType || 'audio/webm' });
				fallbackRecorder = null;
				fallbackStream?.getTracks().forEach((track) => track.stop());
				fallbackStream = null;
				void transcribeFallbackCapture(blob);
			};
			fallbackRecorder.start();
			kuralState.set('LISTENING');
		} catch (error) {
			console.error('[KuralVoice] Microphone fallback failed:', error);
			isContinuousListening = false;
			kuralState.set('ERROR');
			kuralResponseText.set('Microphone access is unavailable. Please allow microphone access and try again.');
		}
	}

	async function transcribeFallbackCapture(blob: Blob) {
		if (!blob.size) return;
		try {
			const form = new FormData();
			form.append('file', blob, 'voice-turn.webm');
			if (workspace) form.append('workspace', workspace);
			form.append('source', 'voice_mode_fallback');
			form.append('language', navigator.language || 'en-US');
			const response = await fetch('/api/audio/transcribe', { method: 'POST', body: form });
			if (!response.ok) throw new Error(await response.text());
			const result = await response.json();
			const transcript = String(result?.text || '').trim();
			if (transcript) {
				kuralTranscript.set(transcript);
				await handleUserUtterance(transcript);
			} else {
				kuralState.set('IDLE');
			}
		} catch (error) {
			console.error('[KuralVoice] Fallback transcription failed:', error);
			kuralState.set('ERROR');
			kuralResponseText.set('I could not understand that voice turn. Please try again.');
		}
	}

	function stopListening(transcribeFallback = true) {
		isContinuousListening = false;
		if (recognition) {
			try {
				recognition.stop();
			} catch (e) {}
		}
		if (transcribeFallback && fallbackRecorder) fallbackRecorder.stop();
	}

	function formatCasualShortVoiceReply(fullText: string): string {
		if (!fullText) return 'Done!';
		let clean = fullText
			.replace(/```[\s\S]*?```/g, '')
			.replace(/`([^`]+)`/g, '$1')
			.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
			.replace(/[*_#~[\]()]/g, '')
			.replace(/^\s*[-*+]\s+/gm, '')
			.replace(/\n+/g, ' ')
			.trim();

		if (!clean) return 'Done!';

		const sentences = clean.split(/(?<=[.!?])\s+/).filter(Boolean);
		if (sentences.length <= 2) {
			return clean;
		}

		return sentences.slice(0, 2).join(' ');
	}

	async function handleUserUtterance(userText: string) {
		stopListening(false);
		stopTtsPlayback();

		kuralState.set('THINKING');
		conversationLog = [...conversationLog, { role: 'user', text: userText }];

		try {
			let responseText = '';

			if (onSendMessage) {
				// Use parent handler if provided
				await onSendMessage(userText);
				responseText = $kuralResponseText || 'Done.';
			} else {
				const model = get(defaultModel) || 'sofie-code';
				const effectiveChatId = currentVoiceChatId || activeChatId || undefined;
				const sendResult = await sendMessage(
					userText,
					model,
					workspace ?? undefined,
					effectiveChatId,
					null,
					{ tool_approval_mode: 'auto', voice_mode: true }
				);

				if (sendResult?.chat_id) {
					currentVoiceChatId = sendResult.chat_id;
				}

				const targetChatId = sendResult?.chat_id || effectiveChatId;

				// Wait for agent execution (which runs Excel tool & generates response)
				let attempts = 0;
				while (attempts < 30) {
					await new Promise((r) => setTimeout(r, 1000));
					attempts++;
					if (targetChatId) {
						const detail = await getChat(targetChatId).catch(() => null);
						if (detail?.messages?.length) {
							const lastMsg = detail.messages[detail.messages.length - 1];
							if (lastMsg?.role === 'assistant' && lastMsg.done && lastMsg.content) {
								responseText = lastMsg.content;
								break;
							}
						}
					}
				}
				if (!responseText) {
					responseText = sendResult.assistant_message?.content || 'Done. I processed your request.';
				}
			}

			const shortReply = formatCasualShortVoiceReply(responseText);
			kuralResponseText.set(shortReply);
			conversationLog = [...conversationLog, { role: 'assistant', text: shortReply }];

			// Synthesize speech via Sarvam AI TTS or Web Speech API
			await synthesizeAndSpeak(shortReply);
		} catch (err: any) {
			console.error('[KuralVoice] Error processing request:', err);
			kuralState.set('ERROR');
			kuralResponseText.set("I'm having trouble processing that right now.");
			setTimeout(() => {
				if (isContinuousListening) startListening();
			}, 3000);
		}
	}

	async function synthesizeAndSpeak(text: string) {
		const isTamil = /[\u0B80-\u0BFF]/.test(text) || /\b(pannu|irukken|aachu|pannunga|kural|vanakkam)\b/i.test(text);
		const targetLang = isTamil ? 'ta-IN' : 'en-IN';

		try {
			const res = await fetch('/api/audio/speech', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					text: text,
					voice: $ttsVoice || 'meera',
					language: targetLang,
					workspace: workspace
				})
			});

			if (!res.ok) {
				console.warn(`[KuralVoice] Server TTS status ${res.status}, using native Web Speech API.`);
				fallbackWebSpeechSynthesize(text);
				return;
			}

			kuralState.set('SPEAKING');
			const blob = await res.blob();
			const audioUrl = URL.createObjectURL(blob);
			const audioEl = setTtsAudioPlaybackSource(audioUrl, 'Kural AI');

			if (audioEl) {
				await audioEl.play();
			} else {
				fallbackWebSpeechSynthesize(text);
			}
		} catch (err) {
			console.warn('[KuralVoice] Server TTS playback error, using native Web Speech API:', err);
			fallbackWebSpeechSynthesize(text);
		}
	}

	function fallbackWebSpeechSynthesize(text: string) {
		if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
			kuralState.set('IDLE');
			if (isContinuousListening) startListening();
			return;
		}

		window.speechSynthesis.cancel();
		kuralState.set('SPEAKING');

		const cleanText = text
			.replace(/[*_#`~[\]()]/g, '')
			.replace(/https?:\/\/\S+/g, '')
			.trim();

		const isTamil = /[\u0B80-\u0BFF]/.test(cleanText) || /\b(pannu|irukken|aachu|pannunga|kural|vanakkam)\b/i.test(cleanText);
		const utterance = new SpeechSynthesisUtterance(cleanText);
		utterance.rate = 1.0;
		utterance.pitch = 1.0;

		// Select Tamil (ta-IN) voice or Indian voice if available in browser
		if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
			const voices = window.speechSynthesis.getVoices();
			let matchedVoice = null;
			if (isTamil) {
				matchedVoice = voices.find(
					(v) => v.lang.toLowerCase().includes('ta') || v.name.toLowerCase().includes('tamil')
				);
			}
			if (!matchedVoice) {
				matchedVoice = voices.find((v) => v.lang.includes('en-IN') || v.lang.includes('hi-IN'));
			}
			if (matchedVoice) {
				utterance.voice = matchedVoice;
				utterance.lang = matchedVoice.lang;
			} else {
				utterance.lang = isTamil ? 'ta-IN' : 'en-IN';
			}
		}

		utterance.onend = () => {
			kuralState.set('IDLE');
			kuralAudioLevel.set(0);
			if (isContinuousListening) {
				setTimeout(() => startListening(), 400);
			}
		};

		utterance.onerror = (e) => {
			console.warn('[KuralVoice] WebSpeech error:', e);
			kuralState.set('IDLE');
			kuralAudioLevel.set(0);
			if (isContinuousListening) {
				setTimeout(() => startListening(), 400);
			}
		};

		window.speechSynthesis.speak(utterance);
	}
</script>

<div class="kural-voice-interface">
	<!-- Top Bar / Identity Header -->
	<header class="kural-header">
		<div class="identity">
			<span class="sparkle">✦</span>
			<h1 class="title">Kural AI</h1>
		</div>

		<div class="actions">
			<button
				class="icon-btn"
				onclick={() => (showTranscriptModal = !showTranscriptModal)}
				title="Toggle Transcript History"
			>
				💬 History
			</button>
		</div>
	</header>

	<!-- Main Central Voice Orb -->
	<main class="kural-center">
		<KuralOrb orbState={$kuralState} audioLevel={$kuralAudioLevel} />

		<!-- Live Spoken Utterance or Response Preview -->
		<div class="transcript-display">
			{#if $kuralResponseText}
				<p class="spoken-response">{$kuralResponseText}</p>
			{:else if $kuralTranscript}
				<p class="user-transcript">"{$kuralTranscript}"</p>
			{/if}
		</div>
	</main>

	<!-- Bottom Controls -->
	<footer class="kural-footer">
		{#if $kuralState === 'LISTENING' || $kuralState === 'SPEECH_DETECTED' || $kuralState === 'SPEAKING'}
			<button class="mic-btn active" onclick={() => stopListening()} title="Pause Listening">
				🎙️ Kural is listening...
			</button>
		{:else}
			<button class="mic-btn" onclick={startListening} title="Start Listening">
				🎙️ Start Voice Turn
			</button>
		{/if}
	</footer>

	<!-- Optional Transcript History Modal for Accessibility -->
	{#if showTranscriptModal}
		<div class="transcript-drawer">
			<div class="drawer-header">
				<h3>Conversation Transcript</h3>
				<button class="close-btn" onclick={() => (showTranscriptModal = false)}>✕</button>
			</div>
			<div class="drawer-body">
				{#each conversationLog as item}
					<div class="log-item {item.role}">
						<span class="role-badge">{item.role === 'user' ? 'You' : 'Kural'}</span>
						<p class="log-text">{item.text}</p>
					</div>
				{/each}
				{#if conversationLog.length === 0}
					<p class="empty-log">No voice turns yet. Speak to Kural AI to start.</p>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.kural-voice-interface {
		display: flex;
		flex-direction: column;
		height: 100%;
		width: 100%;
		background: radial-gradient(circle at 50% 35%, #fff1f2 0%, #fdf2f8 45%, #f8fafc 100%);
		color: #0f172a;
		position: relative;
		overflow: hidden;
		transition: background 0.3s ease;
	}

	:global(.dark) .kural-voice-interface {
		background: radial-gradient(circle at 50% 35%, #1e1b4b 0%, #0f172a 60%, #020617 100%);
		color: #f8fafc;
	}

	.kural-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.5rem 2.5rem;
		z-index: 10;
	}

	.identity {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}

	.sparkle {
		color: #f472b6;
		font-size: 1.35rem;
	}

	.title {
		font-size: 1.5rem;
		font-weight: 700;
		background: linear-gradient(135deg, #db2777 0%, #ec4899 50%, #d946ef 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		margin: 0;
		letter-spacing: -0.01em;
	}

	.icon-btn {
		background: rgba(255, 255, 255, 0.7);
		backdrop-filter: blur(10px);
		border: 1px solid rgba(244, 114, 182, 0.3);
		color: #475569;
		padding: 0.5rem 1.1rem;
		border-radius: 9999px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease;
		box-shadow: 0 2px 10px rgba(244, 114, 182, 0.08);
	}

	:global(.dark) .icon-btn {
		background: rgba(255, 255, 255, 0.06);
		border-color: rgba(244, 114, 182, 0.2);
		color: #cbd5e1;
	}

	.icon-btn:hover {
		background: rgba(244, 114, 182, 0.15);
		color: #db2777;
	}

	.kural-center {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		position: relative;
		z-index: 5;
	}

	.transcript-display {
		margin-top: 1rem;
		max-width: 620px;
		text-align: center;
		padding: 0 1.5rem;
		min-height: 3.5rem;
	}

	.user-transcript {
		font-size: 1.2rem;
		color: #64748b;
		font-style: italic;
	}

	:global(.dark) .user-transcript {
		color: #94a3b8;
	}

	.spoken-response {
		font-size: 1.15rem;
		color: #1e293b;
		line-height: 1.6;
		font-weight: 500;
	}

	:global(.dark) .spoken-response {
		color: #f1f5f9;
	}

	.kural-footer {
		padding: 2.25rem;
		display: flex;
		justify-content: center;
		z-index: 10;
	}

	.mic-btn,
	.bargein-btn {
		padding: 0.9rem 2.25rem;
		border-radius: 9999px;
		font-size: 0.975rem;
		font-weight: 600;
		border: none;
		cursor: pointer;
		transition: all 0.25s ease;
		box-shadow: 0 8px 25px rgba(236, 72, 153, 0.25);
	}

	.mic-btn {
		background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
		color: #ffffff;
	}

	.mic-btn.active {
		background: linear-gradient(135deg, #db2777 0%, #be185d 100%);
		box-shadow: 0 0 25px rgba(219, 39, 119, 0.4);
	}

	.bargein-btn {
		background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
		color: #ffffff;
		animation: pulse-btn 1.5s infinite;
	}

	@keyframes pulse-btn {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.04);
		}
	}

	/* Transcript Drawer */
	.transcript-drawer {
		position: absolute;
		right: 0;
		top: 0;
		bottom: 0;
		width: 380px;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(20px);
		border-left: 1px solid rgba(244, 114, 182, 0.2);
		z-index: 20;
		display: flex;
		flex-direction: column;
		box-shadow: -10px 0 35px rgba(0, 0, 0, 0.1);
	}

	:global(.dark) .transcript-drawer {
		background: #0f172a;
		border-color: rgba(255, 255, 255, 0.1);
		box-shadow: -10px 0 35px rgba(0, 0, 0, 0.5);
	}

	.drawer-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid rgba(244, 114, 182, 0.2);
	}

	.drawer-header h3 {
		margin: 0;
		font-size: 1.1rem;
		color: #0f172a;
	}

	:global(.dark) .drawer-header h3 {
		color: #f8fafc;
	}

	.close-btn {
		background: none;
		border: none;
		color: #64748b;
		font-size: 1.25rem;
		cursor: pointer;
	}

	.drawer-body {
		flex: 1;
		padding: 1.5rem;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.log-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.role-badge {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		color: #64748b;
	}

	.log-item.user .role-badge {
		color: #ec4899;
	}

	.log-item.assistant .role-badge {
		color: #a855f7;
	}

	.log-text {
		margin: 0;
		font-size: 0.95rem;
		line-height: 1.5;
		color: #334155;
	}

	:global(.dark) .log-text {
		color: #cbd5e1;
	}

	.empty-log {
		color: #64748b;
		text-align: center;
		margin-top: 3rem;
		font-size: 0.9rem;
	}
</style>
