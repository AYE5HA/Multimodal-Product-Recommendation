import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="home">
      <header className="site-nav">
        <Link to="/" className="site-nav__brand" aria-current="page">
          Atelier
        </Link>
        <Link to="/studio" className="site-nav__link">
          Studio
        </Link>
      </header>

      <main className="hero">
        <div className="hero__atmosphere" aria-hidden="true" />
        <div className="hero__content">
          <p className="hero__brand">Atelier</p>
          <h1 className="hero__headline">Outfit intelligence, grounded in the graph.</h1>
          <p className="hero__lede">
            Multimodal retrieval meets GraphRAG — recommend complete looks with
            explainable scores for color, structure, and catalog evidence.
          </p>
          <div className="hero__cta">
            <Link to="/studio" className="btn btn--primary">
              Open Studio
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
