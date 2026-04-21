"""Payment provider adapters."""

from neovpn.payments.cryptobot import CryptoBotAdapter
from neovpn.payments.stars import TelegramStarsAdapter

__all__ = ["CryptoBotAdapter", "TelegramStarsAdapter"]
