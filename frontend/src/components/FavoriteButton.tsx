interface FavoriteButtonProps {
  isFavorite: boolean;
  busy: boolean;
  onToggle: () => void;
  className?: string;
}

function FavoriteButton({
  isFavorite,
  busy,
  onToggle,
  className,
}: FavoriteButtonProps) {
  const label = isFavorite ? "Quitar de favoritos" : "Agregar a favoritos";
  const classes = [
    "favorite-button",
    isFavorite ? "favorite-button--active" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type="button"
      className={classes}
      onClick={onToggle}
      disabled={busy}
      title={label}
      aria-label={label}
      aria-pressed={isFavorite}
    >
      <span aria-hidden="true">{isFavorite ? "★" : "☆"}</span>
    </button>
  );
}

export default FavoriteButton;
