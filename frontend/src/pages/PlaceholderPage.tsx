interface PlaceholderPageProps {
  title: string;
}

function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <section className="page">
      <div className="page-heading">
        <p className="eyebrow">Sección</p>
        <h2>{title}</h2>
        <p>Esta sección estará disponible próximamente.</p>
      </div>
    </section>
  );
}

export default PlaceholderPage;