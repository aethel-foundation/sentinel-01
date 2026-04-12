import { Composition } from 'remotion';
import { SentinelVideo } from './SentinelVideo';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="SentinelDemo"
				component={SentinelVideo}
				durationInFrames={150}
				fps={30}
				width={1920}
				height={1080}
			/>
		</>
	);
};
