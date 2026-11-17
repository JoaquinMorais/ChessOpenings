import { useState } from "react";

import {
  readSoundSettings,
  writeSoundSettings,
} from "../utils/sound";

function SoundControl() {
  const initial = readSoundSettings();
  const [enabled, setEnabled] = useState(initial.enabled);
  const [volume, setVolume] = useState(
    Math.round(initial.volume * 100),
  );

  const handleEnabledChange = (checked: boolean) => {
    setEnabled(checked);
    writeSoundSettings({ enabled: checked });
  };

  const handleVolumeChange = (nextVolume: number) => {
    setVolume(nextVolume);
    writeSoundSettings({ volume: nextVolume / 100 });
  };

  return (
    <details className="sound-control">
      <summary>Sonido</summary>
      <div className="sound-control__panel">
        <label className="checkbox-field sound-control__toggle">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) =>
              handleEnabledChange(event.target.checked)
            }
          />
          Activar sonido
        </label>
        <label className="sound-control__volume">
          <span>Volumen</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={volume}
            onChange={(event) =>
              handleVolumeChange(Number(event.target.value))
            }
            disabled={!enabled}
          />
        </label>
      </div>
    </details>
  );
}

export default SoundControl;
