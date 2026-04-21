import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "NeoVPN — умный VPN с оплатой в звёздах и крипте",
  description: "Подключение за 30 секунд. Marzban + AmneziaWG. Оплата Stars и CryptoBot.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <header className="site-header">
          <a className="brand" href="/">
            NeoVPN
          </a>
          <nav>
            <a href="/pricing">Тарифы</a>
            <a href="/cabinet">Кабинет</a>
          </nav>
        </header>
        <main>{children}</main>
        <footer>
          <small>© {new Date().getFullYear()} NeoVPN</small>
        </footer>
      </body>
    </html>
  );
}
