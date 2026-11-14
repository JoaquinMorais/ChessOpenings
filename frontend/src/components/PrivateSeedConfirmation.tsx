interface PrivateSeedConfirmationProps {
  openingName: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}

function PrivateSeedConfirmation({
  openingName,
  value,
  onChange,
  disabled,
}: PrivateSeedConfirmationProps) {
  return (
    <div className="form-field">
      <p className="seed-danger-warning">
        <strong>Archivo privado sin copia.</strong> No está en git y no hay
        forma de recuperarlo si lo borrás.
      </p>
      <label>
        <span>Escribí “{openingName}” para confirmar</span>
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={openingName}
          autoComplete="off"
          disabled={disabled}
        />
      </label>
    </div>
  );
}

export default PrivateSeedConfirmation;
