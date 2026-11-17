const ENABLED_KEY = "chess-openings-sound-enabled";
const VOLUME_KEY = "chess-openings-sound-volume";
const DEFAULT_VOLUME = 0.25;

type SoundKind = "move" | "capture" | "brilliant";

interface SoundSettings {
  enabled: boolean;
  volume: number;
}

type WebkitWindow = Window & {
  webkitAudioContext?: typeof AudioContext;
};

let audioContext: AudioContext | null = null;

function clampVolume(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export function readSoundSettings(): SoundSettings {
  if (typeof window === "undefined") {
    return { enabled: true, volume: DEFAULT_VOLUME };
  }

  try {
    const enabledRaw = window.localStorage.getItem(ENABLED_KEY);
    const volumeRaw = window.localStorage.getItem(VOLUME_KEY);
    const parsedVolume = volumeRaw === null ? NaN : Number(volumeRaw);
    return {
      enabled: enabledRaw !== "false",
      volume: Number.isFinite(parsedVolume)
        ? clampVolume(parsedVolume)
        : DEFAULT_VOLUME,
    };
  } catch {
    return { enabled: true, volume: DEFAULT_VOLUME };
  }
}

export function writeSoundSettings(settings: Partial<SoundSettings>): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (settings.enabled !== undefined) {
      window.localStorage.setItem(
        ENABLED_KEY,
        String(settings.enabled),
      );
    }
    if (settings.volume !== undefined) {
      window.localStorage.setItem(
        VOLUME_KEY,
        String(clampVolume(settings.volume)),
      );
    }
  } catch {
    // La app sigue funcionando aunque localStorage no esté disponible.
  }
}

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") {
    return null;
  }
  if (!audioContext) {
    const Context =
      window.AudioContext ??
      (window as WebkitWindow).webkitAudioContext;
    if (!Context) {
      return null;
    }
    audioContext = new Context();
  }
  return audioContext;
}

function scheduleTone(
  context: AudioContext,
  destination: AudioNode,
  frequency: number,
  start: number,
  duration: number,
  peak: number,
  type: OscillatorType = "sine",
): void {
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(peak, start + 0.008);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain);
  gain.connect(destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.02);
}

function scheduleSound(
  context: AudioContext,
  kind: SoundKind,
  volume: number,
): void {
  const master = context.createGain();
  master.gain.value = volume;
  master.connect(context.destination);
  const now = context.currentTime;

  if (kind === "brilliant") {
    const notes = [1046.5, 1318.5, 1568.0, 2093.0];
    notes.forEach((frequency, index) => {
      scheduleTone(
        context,
        master,
        frequency,
        now + index * 0.055,
        0.28,
        0.26,
        index === 3 ? "sine" : "triangle",
      );
    });
    return;
  }

  if (kind === "capture") {
    scheduleTone(context, master, 170, now, 0.11, 0.5, "triangle");
    scheduleTone(context, master, 95, now + 0.012, 0.12, 0.35, "sine");
    return;
  }

  scheduleTone(context, master, 260, now, 0.055, 0.42, "triangle");
  scheduleTone(context, master, 820, now, 0.025, 0.12, "sine");
}

export function playPieceSound(kind: SoundKind): void {
  const settings = readSoundSettings();
  if (!settings.enabled || settings.volume <= 0) {
    return;
  }

  const context = getAudioContext();
  if (!context) {
    return;
  }

  if (context.state === "suspended") {
    void context.resume().then(() => {
      scheduleSound(context, kind, settings.volume);
    });
    return;
  }

  scheduleSound(context, kind, settings.volume);
}
