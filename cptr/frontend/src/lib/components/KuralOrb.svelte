<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { KuralOrbState } from '$lib/stores/audio';

	let { orbState = 'IDLE', audioLevel = 0 } = $props<{
		orbState?: KuralOrbState;
		audioLevel?: number;
	}>();

	let canvas = $state<HTMLCanvasElement>();
	let animFrame: number;

	// Eased level for smooth organic motion without jitter
	let smoothedAudioLevel = 0;
	let time = 0;

	const stateLabel = $derived(
		orbState === 'IDLE'
			? 'Listening for you...'
			: orbState === 'LISTENING'
				? 'Listening...'
				: orbState === 'SPEECH_DETECTED'
					? 'Hearing you...'
					: orbState === 'TRANSCRIBING'
						? 'Processing speech...'
						: orbState === 'THINKING'
							? 'Thinking...'
							: orbState === 'EXECUTING'
								? 'Working in Excel...'
								: orbState === 'VERIFYING'
									? 'Verifying result...'
									: orbState === 'SPEAKING'
										? 'Kural is speaking...'
										: orbState === 'INTERRUPTED'
											? 'Interrupted'
											: 'Notice'
	);

	onMount(() => {
		const ctx = canvas.getContext('2d');
		if (!ctx) return;

		function resize() {
			if (!canvas) return;
			const dpr = window.devicePixelRatio || 1;
			const rect = canvas.getBoundingClientRect();
			canvas.width = rect.width * dpr;
			canvas.height = rect.height * dpr;
			ctx!.scale(dpr, dpr);
		}

		resize();
		window.addEventListener('resize', resize);

		// 3D Orbital Surface Definitions
		const orbitals = [
			{ rx: 90, ry: 45, tiltX: 0.35, tiltZ: 0.2, speed: 0.012, phase: 0 },
			{ rx: 110, ry: 50, tiltX: -0.45, tiltZ: -0.3, speed: 0.009, phase: 1.2 },
			{ rx: 125, ry: 55, tiltX: 0.65, tiltZ: 0.45, speed: -0.014, phase: 2.4 },
			{ rx: 100, ry: 40, tiltX: -0.2, tiltZ: 0.6, speed: -0.011, phase: 3.6 },
			{ rx: 135, ry: 60, tiltX: 0.4, tiltZ: -0.5, speed: 0.008, phase: 4.8 }
		];

		function render() {
			if (!canvas || !ctx) return;

			const rect = canvas.getBoundingClientRect();
			const width = rect.width;
			const height = rect.height;
			const cx = width / 2;
			const cy = height / 2;

			ctx.clearRect(0, 0, width, height);

			// Smooth audio reactivity
			const targetAudio = Math.min(Math.max(audioLevel, 0), 1);
			smoothedAudioLevel += (targetAudio - smoothedAudioLevel) * 0.15;

			// Speed & Amplitude Modulation based on State
			let stateSpeedMult = 1.0;
			let statePulseMult = 1.0;

			if (orbState === 'LISTENING' || orbState === 'SPEECH_DETECTED') {
				stateSpeedMult = 1.2 + smoothedAudioLevel * 1.5;
				statePulseMult = 1.05 + smoothedAudioLevel * 0.25;
			} else if (orbState === 'THINKING' || orbState === 'EXECUTING' || orbState === 'TRANSCRIBING') {
				stateSpeedMult = 2.2;
				statePulseMult = 1.12;
			} else if (orbState === 'SPEAKING') {
				stateSpeedMult = 1.6 + smoothedAudioLevel * 2.2;
				statePulseMult = 1.0 + smoothedAudioLevel * 0.45;
			} else if (orbState === 'VERIFYING') {
				stateSpeedMult = 1.4;
				statePulseMult = 1.08;
			} else if (orbState === 'INTERRUPTED') {
				stateSpeedMult = 0.5;
				statePulseMult = 0.95;
			} else {
				// IDLE
				stateSpeedMult = 0.7;
				statePulseMult = 1.0 + Math.sin(time * 0.002) * 0.03;
			}

			time += 16.6 * stateSpeedMult;

			// 1. Draw Outer Soft Pink Glow Aura
			const auraRadius = 140 * statePulseMult;
			const auraGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, auraRadius);

			if (orbState === 'ERROR') {
				auraGrad.addColorStop(0, 'rgba(239, 68, 68, 0.45)');
				auraGrad.addColorStop(0.5, 'rgba(244, 114, 182, 0.2)');
				auraGrad.addColorStop(1, 'rgba(244, 114, 182, 0)');
			} else {
				auraGrad.addColorStop(0, 'rgba(244, 114, 182, 0.45)');
				auraGrad.addColorStop(0.4, 'rgba(236, 72, 153, 0.25)');
				auraGrad.addColorStop(0.8, 'rgba(240, 171, 252, 0.1)');
				auraGrad.addColorStop(1, 'rgba(250, 232, 255, 0)');
			}

			ctx.fillStyle = auraGrad;
			ctx.beginPath();
			ctx.arc(cx, cy, auraRadius, 0, Math.PI * 2);
			ctx.fill();

			// 2. Render 3D Layered Orbital Ribbon Surfaces
			orbitals.forEach((orb, idx) => {
				const currentAngle = time * orb.speed + orb.phase;
				const points: { x: number; y: number; z: number }[] = [];

				const steps = 72;
				for (let i = 0; i <= steps; i++) {
					const theta = (i / steps) * Math.PI * 2;

					// Base Ellipse
					let x0 = Math.cos(theta) * orb.rx * statePulseMult;
					let y0 = Math.sin(theta) * orb.ry * statePulseMult;
					let z0 = Math.sin(theta * 2 + currentAngle) * 18 * statePulseMult;

					// Sinusoidal Organic Deformation
					const wave = Math.sin(theta * 3 + currentAngle * 1.5) * (8 + smoothedAudioLevel * 16);
					x0 += Math.cos(theta) * wave;
					y0 += Math.sin(theta) * wave;

					// 3D Euler Rotations (tiltX, tiltZ, rotation)
					const cosTX = Math.cos(orb.tiltX);
					const sinTX = Math.sin(orb.tiltX);
					const y1 = y0 * cosTX - z0 * sinTX;
					const z1 = y0 * sinTX + z0 * cosTX;

					const cosTZ = Math.cos(orb.tiltZ + currentAngle * 0.2);
					const sinTZ = Math.sin(orb.tiltZ + currentAngle * 0.2);
					const x2 = x0 * cosTZ - y1 * sinTZ;
					const y2 = x0 * sinTZ + y1 * cosTZ;
					const z2 = z1;

					// Perspective projection
					const perspective = 400 / (400 + z2);
					const px = cx + x2 * perspective;
					const py = cy + y2 * perspective;

					points.push({ x: px, y: py, z: z2 });
				}

				// Draw Organic Translucent Orbital Surface Ribbon
				ctx.beginPath();
				ctx.moveTo(points[0].x, points[0].y);
				for (let i = 1; i < points.length; i++) {
					const p0 = points[i - 1];
					const p1 = points[i];
					const xc = (p0.x + p1.x) / 2;
					const yc = (p0.y + p1.y) / 2;
					ctx.quadraticCurveTo(p0.x, p0.y, xc, yc);
				}
				ctx.closePath();

				// Soft Pink/Magenta Translucent Gradient Fill & Stroke
				const alpha = 0.25 + (idx % 3) * 0.08;
				const strokeWidth = (2.2 + (idx % 2) * 1.2) * statePulseMult;

				ctx.strokeStyle = `rgba(244, 114, 182, ${alpha + smoothedAudioLevel * 0.3})`;
				ctx.lineWidth = strokeWidth;
				ctx.stroke();

				// Inner Translucent Fill Shader
				const ribbonGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, 120);
				ribbonGrad.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
				ribbonGrad.addColorStop(0.5, 'rgba(244, 114, 182, 0.08)');
				ribbonGrad.addColorStop(1, 'rgba(236, 72, 153, 0)');
				ctx.fillStyle = ribbonGrad;
				ctx.fill();
			});

			// 3. Render Center Glowing Core Sphere
			const coreRadius = (45 + smoothedAudioLevel * 22) * statePulseMult;
			const coreGrad = ctx.createRadialGradient(
				cx - coreRadius * 0.25,
				cy - coreRadius * 0.25,
				2,
				cx,
				cy,
				coreRadius
			);

			if (orbState === 'ERROR') {
				coreGrad.addColorStop(0, '#ffffff');
				coreGrad.addColorStop(0.3, '#fca5a5');
				coreGrad.addColorStop(0.7, '#ef4444');
				coreGrad.addColorStop(1, '#b91c1c');
			} else {
				coreGrad.addColorStop(0, '#ffffff');
				coreGrad.addColorStop(0.35, '#fbcfe8');
				coreGrad.addColorStop(0.7, '#f472b6');
				coreGrad.addColorStop(1, '#ec4899');
			}

			ctx.fillStyle = coreGrad;
			ctx.shadowColor = 'rgba(244, 114, 182, 0.75)';
			ctx.shadowBlur = 30 + smoothedAudioLevel * 20;

			ctx.beginPath();
			ctx.arc(cx, cy, coreRadius, 0, Math.PI * 2);
			ctx.fill();

			ctx.shadowBlur = 0; // Reset shadow

			// Highlight Specular Spot
			const specGrad = ctx.createRadialGradient(
				cx - coreRadius * 0.35,
				cy - coreRadius * 0.35,
				1,
				cx - coreRadius * 0.35,
				cy - coreRadius * 0.35,
				coreRadius * 0.5
			);
			specGrad.addColorStop(0, 'rgba(255, 255, 255, 0.85)');
			specGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
			ctx.fillStyle = specGrad;
			ctx.beginPath();
			ctx.arc(cx - coreRadius * 0.35, cy - coreRadius * 0.35, coreRadius * 0.4, 0, Math.PI * 2);
			ctx.fill();

			animFrame = requestAnimationFrame(render);
		}

		render();

		return () => {
			window.removeEventListener('resize', resize);
			if (animFrame) cancelAnimationFrame(animFrame);
		};
	});
</script>

<div class="kural-orb-canvas-container">
	<!-- High-Performance GPU-Accelerated 3D Organic Canvas -->
	<canvas bind:this={canvas} class="orb-canvas"></canvas>

	<!-- Status Caption -->
	<div class="status-caption">
		<span class="status-dot {orbState.toLowerCase()}"></span>
		<span class="status-text">{stateLabel}</span>
	</div>
</div>

<style>
	.kural-orb-canvas-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		position: relative;
		user-select: none;
	}

	.orb-canvas {
		width: 380px;
		height: 380px;
		max-width: 90vw;
		max-height: 90vw;
		display: block;
	}

	.status-caption {
		margin-top: 1.5rem;
		display: flex;
		align-items: center;
		gap: 0.6rem;
		background: rgba(255, 255, 255, 0.85);
		backdrop-filter: blur(16px);
		padding: 0.5rem 1.25rem;
		border-radius: 9999px;
		border: 1px solid rgba(244, 114, 182, 0.25);
		box-shadow: 0 4px 20px rgba(244, 114, 182, 0.12);
	}

	:global(.dark) .status-caption {
		background: rgba(15, 23, 42, 0.75);
		border-color: rgba(244, 114, 182, 0.2);
	}

	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #f472b6;
		box-shadow: 0 0 8px #f472b6;
	}

	.status-dot.listening,
	.status-dot.speech_detected {
		background: #ec4899;
		box-shadow: 0 0 10px #ec4899;
	}

	.status-dot.thinking,
	.status-dot.executing,
	.status-dot.verifying,
	.status-dot.transcribing {
		background: #d946ef;
		box-shadow: 0 0 10px #d946ef;
	}

	.status-dot.speaking {
		background: #f472b6;
		box-shadow: 0 0 12px #f472b6;
	}

	.status-dot.error {
		background: #ef4444;
		box-shadow: 0 0 10px #ef4444;
	}

	.status-text {
		font-size: 0.95rem;
		font-weight: 500;
		color: #334155;
		letter-spacing: 0.01em;
	}

	:global(.dark) .status-text {
		color: #f1f5f9;
	}
</style>
