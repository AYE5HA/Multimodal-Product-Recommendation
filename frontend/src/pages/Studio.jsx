import { useState } from 'react';
import { Link } from 'react-router-dom';
import { recommendOutfits } from '../api';
import OutfitCard from '../components/OutfitCard';

const GENDERS = [
  { value: '', label: 'Any' },
  { value: 'women', label: 'Women' },
  { value: 'men', label: 'Men' },
  { value: 'unisex', label: 'Unisex' },
];

const OCCASIONS = [
  { value: '', label: 'Any' },
  { value: 'casual', label: 'Casual' },
  { value: 'work', label: 'Work' },
  { value: 'evening', label: 'Evening' },
  { value: 'formal', label: 'Formal' },
  { value: 'travel', label: 'Travel' },
];

const BUDGETS = [
  { value: '', label: 'Any' },
  { value: '1500', label: 'Under ₹1,500' },
  { value: '3000', label: 'Under ₹3,000' },
  { value: '6000', label: 'Under ₹6,000' },
];

export default function Studio() {
  const [query, setQuery] = useState('');
  const [gender, setGender] = useState('');
  const [occasion, setOccasion] = useState('');
  const [budget, setBudget] = useState('');
  const [outfits, setOutfits] = useState(null);
  const [explanation, setExplanation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      setError('Enter a query describing the look you want.');
      return;
    }

    setLoading(true);
    setError(null);
    setOutfits(null);
    setExplanation('');

    try {
      const payload = { query: trimmed };
      if (gender) payload.gender = gender;
      if (occasion) payload.occasion = occasion;
      if (budget) payload.budget = budget;

      const data = await recommendOutfits(payload);
      const list = data?.outfits || data?.results || data?.recommendations || [];
      setOutfits(Array.isArray(list) ? list : []);
      setExplanation(data?.explanation || data?.summary || '');
      if (!list?.length) {
        setError(null);
      }
    } catch (err) {
      setOutfits(null);
      setError(err?.message || 'Recommendation request failed.');
    } finally {
      setLoading(false);
    }
  }

  const showEmpty = outfits !== null && outfits.length === 0 && !loading && !error;

  return (
    <div className="studio">
      <header className="site-nav site-nav--solid">
        <Link to="/" className="site-nav__brand">
          Atelier
        </Link>
        <span className="site-nav__crumb">Studio</span>
      </header>

      <main className="studio__main">
        <section className="studio__intro">
          <h1 className="studio__title">Studio</h1>
          <p className="studio__lede">
            Describe an occasion, silhouette, or palette. Optional filters refine
            retrieval before GraphRAG ranks complete outfits.
          </p>
        </section>

        <form className="studio__form" onSubmit={handleSubmit}>
          <label className="field field--query">
            <span className="field__label">Query</span>
            <textarea
              className="field__input field__input--textarea"
              rows={3}
              placeholder="e.g. tailored navy blazer look for a client dinner, soft neutrals"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
            />
          </label>

          <div className="studio__filters">
            <label className="field">
              <span className="field__label">Gender</span>
              <select
                className="field__input"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                disabled={loading}
              >
                {GENDERS.map((o) => (
                  <option key={o.value || 'any'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field__label">Occasion</span>
              <select
                className="field__input"
                value={occasion}
                onChange={(e) => setOccasion(e.target.value)}
                disabled={loading}
              >
                {OCCASIONS.map((o) => (
                  <option key={o.value || 'any'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field__label">Budget</span>
              <select
                className="field__input"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                disabled={loading}
              >
                {BUDGETS.map((o) => (
                  <option key={o.value || 'any'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="studio__actions">
            <button type="submit" className="btn btn--primary" disabled={loading}>
              {loading ? 'Recommending…' : 'Recommend'}
            </button>
          </div>
        </form>

        <section className="studio__results" aria-live="polite">
          {loading && (
            <div className="state state--loading">
              <div className="spinner" aria-hidden="true" />
              <p>Retrieving candidates and scoring via GraphRAG…</p>
            </div>
          )}

          {error && !loading && (
            <div className="state state--error" role="alert">
              <p className="state__title">Unable to recommend</p>
              <p>{error}</p>
            </div>
          )}

          {showEmpty && (
            <div className="state state--empty">
              <p className="state__title">No outfits matched</p>
              <p>Try a broader query or clear one of the filters.</p>
            </div>
          )}

          {!loading && outfits && outfits.length > 0 && (
            <>
              {explanation && (
                <div className="studio__summary">
                  <h2 className="studio__section-title">Summary</h2>
                  <p>{explanation}</p>
                </div>
              )}
              <div className="outfit-grid">
                {outfits.map((outfit, i) => (
                  <OutfitCard
                    key={outfit?.id || outfit?.outfit_id || i}
                    outfit={outfit}
                    rank={i + 1}
                  />
                ))}
              </div>
            </>
          )}

          {outfits === null && !loading && !error && (
            <div className="state state--idle">
              <p>Submit a query to see ranked outfits with score breakdowns and graph evidence.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
