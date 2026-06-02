import type { PublicGameState } from '../types/game';
import CurrentAction from './CurrentAction';
import DialogStream from './DialogStream';
import ActionBar from './ActionBar';

interface Props {
    gameState: PublicGameState;
    onContinue: () => void;
    onSkip: () => void;
}

export default function MainStage({ gameState, onContinue, onSkip }: Props) {
    const { phase, current_speaker, current_thinking, current_speech, night_info, phase_info, speech_history, players, waiting } = gameState;

    return (
        <section className="flex-1 flex flex-col p-3.5 overflow-hidden">
            <CurrentAction
                phase={phase}
                currentSpeaker={current_speaker}
                currentThinking={current_thinking}
                currentSpeech={current_speech}
                nightInfo={night_info}
                phaseInfo={phase_info}
                players={players}
            />
            <DialogStream messages={speech_history} />
            <ActionBar
                waiting={!!waiting}
                phase={phase}
                onContinue={onContinue}
                onSkip={onSkip}
            />
        </section>
    );
}
