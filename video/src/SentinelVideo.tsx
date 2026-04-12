import { AbsoluteFill, useVideoConfig, useCurrentFrame, interpolate, spring } from 'remotion';
import { Shield, Lock, Activity, AlertTriangle } from 'lucide-react';

export const SentinelVideo: React.FC = () => {
	const frame = useCurrentFrame();
	const { fps } = useVideoConfig();

	// Animators
	const logoScale = spring({ frame, fps, from: 0, to: 1, config: { damping: 10 } });
	const textOpacity = interpolate(frame, [20, 40], [0, 1], { extrapolateRight: 'clamp' });
	
	const scene1Opacity = interpolate(frame, [0, 10, 40, 50], [0, 1, 1, 0]);
	const scene2Opacity = interpolate(frame, [50, 60, 90, 100], [0, 1, 1, 0]);
	const scene3Opacity = interpolate(frame, [100, 110, 140, 150], [0, 1, 1, 0]);

	return (
		<AbsoluteFill style={{ backgroundColor: '#020617', fontFamily: 'Inter, system-ui' }}>
			{/* Scene 1: Introduction */}
			<AbsoluteFill style={{ opacity: scene1Opacity, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
				<div style={{ transform: `scale(${logoScale})`, color: '#06b6d4' }}>
					<Shield size={200} />
				</div>
				<h1 style={{ color: 'white', fontSize: 80, marginTop: 40, opacity: textOpacity }}>SENTINEL-01</h1>
				<p style={{ color: '#94a3b8', fontSize: 30, marginTop: 20 }}>AETHEL FOUNDATION</p>
			</AbsoluteFill>

			{/* Scene 2: The Core Rule */}
			<AbsoluteFill style={{ opacity: scene2Opacity, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
				<div style={{ padding: '0 100px' }}>
					<h2 style={{ color: '#06b6d4', fontSize: 60, marginBottom: 40 }}>"Capital preservation is mandatory."</h2>
					<p style={{ color: 'white', fontSize: 40 }}>Profit is secondary.</p>
					<div style={{ display: 'flex', gap: 40, marginTop: 60, justifyContent: 'center' }}>
						<div style={{ padding: 20, border: '1px solid #1e293b', borderRadius: 20 }}>
							<p style={{ color: '#ef4444', fontSize: 40, fontWeight: 'bold' }}>Max Drawdown: 5%</p>
						</div>
						<div style={{ padding: 20, border: '1px solid #1e293b', borderRadius: 20 }}>
							<p style={{ color: '#06b6d4', fontSize: 40, fontWeight: 'bold' }}>Max Trade: 2%</p>
						</div>
					</div>
				</div>
			</AbsoluteFill>

			{/* Scene 3: Trustless Validation */}
			<AbsoluteFill style={{ opacity: scene3Opacity, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
				<Lock size={120} color="#06b6d4" />
				<h1 style={{ color: 'white', fontSize: 60, marginTop: 40 }}>ERC-8004 NATIVE</h1>
				<p style={{ color: '#94a3b8', fontSize: 30, marginTop: 20 }}>Auditable Validation Artifacts On-Chain</p>
			</AbsoluteFill>

			{/* Background Overlay */}
			<AbsoluteFill style={{ 
				background: 'radial-gradient(circle at 50% 50%, rgba(6, 182, 212, 0.05) 0%, transparent 70%)',
				pointerEvents: 'none'
			}} />
		</AbsoluteFill>
	);
};
