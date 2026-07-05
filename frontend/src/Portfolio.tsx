import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from './api';

interface ApiHolding {
  consultant_id: number;
  display_name: string;
  shares: number;
  buy_price: number;
  sell_price: number;
  movement_pct: number;
}

interface ApiDividend {
  consultant_id: number;
  game_date: string;
  reason: string;
  shares: number;
  per_share: number;
  total: number;
}

interface ApiMover {
  consultant_id: number;
  display_name: string;
  movement_pct: number;
  recent_team_wins: number;
  recent_missed_projections: number;
}

interface ApiPortfolio {
  wallet_balance: number;
  holdings: ApiHolding[];
  dividends: ApiDividend[];
  market_movers: ApiMover[];
}

interface ApiExchangeListing {
  consultant_id: number;
  display_name: string;
  buy_price: number;
  sell_price: number;
}

function pct(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(0)}%`;
}

function Portfolio() {
  const [portfolio, setPortfolio] = useState<ApiPortfolio | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showExchange, setShowExchange] = useState(false);
  const [exchange, setExchange] = useState<ApiExchangeListing[] | null>(null);

  const load = useCallback(() => {
    apiFetch('/me/portfolio')
      .then((response) => (response.ok ? response.json() : null))
      .then(setPortfolio);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!showExchange) {
      return;
    }
    apiFetch('/exchange')
      .then((response) => (response.ok ? response.json() : []))
      .then(setExchange);
  }, [showExchange]);

  const trade = async (path: '/trade/buy' | '/trade/sell', consultantId: number) => {
    setError(null);
    const response = await apiFetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consultant_id: consultantId, shares: 1 }),
    });
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? 'Trade failed');
      return;
    }
    load();
  };

  if (!portfolio) {
    return null;
  }

  return (
    <section>
      <h2>Your portfolio</h2>
      <p>Wallet: {portfolio.wallet_balance.toFixed(0)} pts</p>
      {error && <p role="alert">{error}</p>}

      <table>
        <thead>
          <tr>
            <th>Consultant</th>
            <th>Shares</th>
            <th>Buy price</th>
            <th>Sell price</th>
            <th>7-day</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {portfolio.holdings.map((h) => (
            <tr key={h.consultant_id}>
              <td>{h.display_name}</td>
              <td>{h.shares}</td>
              <td>{h.buy_price.toFixed(1)}</td>
              <td>{h.sell_price.toFixed(1)}</td>
              <td>{pct(h.movement_pct)}</td>
              <td>
                <button type="button" onClick={() => trade('/trade/buy', h.consultant_id)}>
                  Buy
                </button>
                <button
                  type="button"
                  onClick={() => trade('/trade/sell', h.consultant_id)}
                >
                  Sell
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ display: 'flex', gap: '2rem' }}>
        <div>
          <h3>Yesterday&apos;s dividends</h3>
          <ul>
            {portfolio.dividends.map((d, i) => (
              <li key={i}>
                {d.reason} — {d.shares} sh × {d.per_share} = {d.total.toFixed(0)}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3>Market movers</h3>
          <ul>
            {portfolio.market_movers.map((m) => (
              <li key={m.consultant_id}>
                {m.display_name} {pct(m.movement_pct)}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <button type="button" onClick={() => setShowExchange((prev) => !prev)}>
        Browse the exchange
      </button>

      {showExchange && exchange && (
        <table>
          <thead>
            <tr>
              <th>Consultant</th>
              <th>Buy price</th>
              <th>Sell price</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {exchange.map((listing) => (
              <tr key={listing.consultant_id}>
                <td>{listing.display_name}</td>
                <td>{listing.buy_price.toFixed(1)}</td>
                <td>{listing.sell_price.toFixed(1)}</td>
                <td>
                  <button
                    type="button"
                    onClick={() => trade('/trade/buy', listing.consultant_id)}
                  >
                    Buy
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export default Portfolio;
