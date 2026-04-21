type Tariff = {
  slug: string;
  name: string;
  duration_days: number;
  traffic_gb: number | null;
  price_rub: string | null;
  price_stars: number | null;
  price_usdt: string | null;
};

async function fetchTariffs(): Promise<Tariff[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/tariffs`, { cache: "no-store" });
    if (!res.ok) return [];
    return (await res.json()) as Tariff[];
  } catch {
    return [];
  }
}

export default async function PricingPage() {
  const tariffs = await fetchTariffs();
  return (
    <section>
      <h1>Тарифы</h1>
      {tariffs.length === 0 ? (
        <p>Скоро появятся тарифы. Заходите через Telegram-бот.</p>
      ) : (
        <div className="cards">
          {tariffs.map((t) => (
            <div key={t.slug} className="card">
              <h3>{t.name}</h3>
              <p>{t.duration_days} дней · {t.traffic_gb ?? "∞"} ГБ</p>
              <p>
                {t.price_rub && <span>{t.price_rub} ₽ · </span>}
                {t.price_stars && <span>{t.price_stars} ⭐ · </span>}
                {t.price_usdt && <span>{t.price_usdt} USDT</span>}
              </p>
              <a className="btn" href={`https://t.me/NeoVPN_bot?start=buy_${t.slug}`}>
                Купить
              </a>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
