export default function HomePage() {
  return (
    <section className="hero">
      <h1>VPN, который просто работает</h1>
      <p>
        Три тапа в Telegram — и готов. Платите Stars или криптой,
        а мы сами держим серверы, сертификаты и резервные IP.
      </p>
      <a className="btn" href="https://t.me/NeoVPN_bot">
        Открыть бота
      </a>
      <div className="cards">
        <div className="card">
          <h3>Marzban + AmneziaWG</h3>
          <p>Надёжные протоколы. VLESS Reality и обфусцированный WireGuard.</p>
        </div>
        <div className="card">
          <h3>Оплата в звёздах</h3>
          <p>Telegram Stars или USDT/TON/BTC через CryptoBot.</p>
        </div>
        <div className="card">
          <h3>Авто-ротация IP</h3>
          <p>Серверы переключаются автоматически при блокировках.</p>
        </div>
      </div>
    </section>
  );
}
