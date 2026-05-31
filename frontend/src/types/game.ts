// frontend/src/types/game.ts

export interface Player {
  seat_id: number;
  player_name: string;
  model_name: string;
  role: string;
  is_alive: boolean;
}

export interface Speech {
  seat_id: number;
  player_name: string;
  content: string;
  thinking: string;
  timestamp: number;
}

export interface PublicGameState {
  phase: GamePhase;
  day: number;
  players: Player[];
  speaker_order: number[];
  speech_history: Speech[];
  full_history: Speech[];
  votes: Record<string, number | null>;
  killed_last_night: number[];
  winner: string | null;
  current_speaker: number | null;
  current_thinking: string | null;
  current_speech?: string;
  night_info?: string;
  phase_info?: string;
  vote_progress?: string;
  waiting?: boolean;
}

export type GamePhase =
  | 'game_init'
  | 'night'
  | 'day'
  | 'vote'
  | 'revote'
  | 'game_over';

export interface PlayerConfig {
  seat_id: number;
  player_name: string;
  model_name: string;
  provider: string;
  api_key: string;
  base_url?: string;
}

export interface ModelPreset {
  provider: string;
  name: string;
  model: string;
  description: string;
}

export interface CreateGameResponse {
  game_id: string;
  players: Player[];
}
