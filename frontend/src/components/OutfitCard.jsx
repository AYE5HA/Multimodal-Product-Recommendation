import ScoreBar from './ScoreBar';
import { API_BASE } from '../api';

const SCORE_KEYS = [
  { key: 'retrieval', label: 'Retrieval' },
  { key: 'graph', label: 'Graph' },
  { key: 'color', label: 'Color' },
  { key: 'structure', label: 'Structure' },
];

function itemColor(item) {
  if (item?.color) return item.color;
  if (item?.hex) return item.hex;
  if (item?.dominant_color) return item.dominant_color;
  const palette = ['#2c3e3a', '#5c4a3a', '#1a2a3a', '#4a3a4a', '#3a4a3a', '#6b5344'];
  const id = String(item?.id || item?.name || 'x');
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h + id.charCodeAt(i) * (i + 1)) % palette.length;
  return palette[h];
}

function ItemThumb({ item }) {
  const name = item?.name || item?.title || item?.category || 'Item';
  const rawImg = item?.image_url || item?.image || item?.img;
  const img = rawImg?.startsWith('/data/') ? `${API_BASE}${rawImg}` : rawImg;
  const bg = itemColor(item);

  return (
    <figure className="outfit-item">
      <div className="outfit-item__media" style={{ background: bg }}>
        {img ? (
          <img src={img} alt={name} loading="lazy" />
        ) : (
          <span className="outfit-item__placeholder" aria-hidden="true">
            {name.slice(0, 1).toUpperCase()}
          </span>
        )}
      </div>
      <figcaption className="outfit-item__caption">
        <span className="outfit-item__name">{name}</span>
        {item?.category && <span className="outfit-item__cat">{item.category}</span>}
      </figcaption>
    </figure>
  );
}

export default function OutfitCard({ outfit, rank }) {
  const items = outfit?.items || outfit?.products || [];
  const scores = outfit?.scores || {};
  const explanation = outfit?.explanation || outfit?.graph_explanation || '';
  const evidence = outfit?.evidence || outfit?.graph_evidence || outfit?.snippets || [];
  const title = outfit?.title || outfit?.name || `Look ${rank}`;
  const total =
    outfit?.score ??
    outfit?.total_score ??
    (SCORE_KEYS.reduce((s, { key }) => s + (Number(scores[key]) || 0), 0) /
      Math.max(1, SCORE_KEYS.filter(({ key }) => scores[key] != null).length));

  return (
    <article className="outfit-card">
      <header className="outfit-card__header">
        <div>
          <p className="outfit-card__rank">Look {String(rank).padStart(2, '0')}</p>
          <h3 className="outfit-card__title">{title}</h3>
        </div>
        <div className="outfit-card__total" title="Composite score">
          <span className="outfit-card__total-label">Score</span>
          <span className="outfit-card__total-value">
            {Math.round(clamp01(total) * 100)}
          </span>
        </div>
      </header>

      <div className="outfit-card__items">
        {items.length === 0 ? (
          <p className="muted">No items returned for this look.</p>
        ) : (
          items.map((item, i) => (
            <ItemThumb key={item?.id || item?.sku || `${rank}-${i}`} item={item} />
          ))
        )}
      </div>

      <div className="outfit-card__scores">
        <h4 className="outfit-card__section-label">Score breakdown</h4>
        {SCORE_KEYS.map(({ key, label }) => (
          <ScoreBar key={key} label={label} value={scores[key] ?? scores[`${key}_score`]} />
        ))}
      </div>

      {explanation && (
        <div className="outfit-card__explain">
          <h4 className="outfit-card__section-label">GraphRAG</h4>
          <p>{explanation}</p>
        </div>
      )}

      {Array.isArray(evidence) && evidence.length > 0 && (
        <div className="outfit-card__evidence">
          <h4 className="outfit-card__section-label">Graph evidence</h4>
          <ul>
            {evidence.map((snip, i) => (
              <li key={i}>
                {typeof snip === 'string' ? snip : snip?.text || snip?.snippet || JSON.stringify(snip)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

function clamp01(n) {
  const v = Number(n);
  if (Number.isNaN(v)) return 0;
  return Math.max(0, Math.min(1, v > 1 ? v / 100 : v));
}
