"""Admin-only commands: stats, node list, broadcast."""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import func, select

from neovpn.bot.container import BotDeps
from neovpn.db import SqlAlchemyUnitOfWork
from neovpn.db.models import (
    NodeRow,
    PaymentRow,
    SubscriptionRow,
    UserRow,
)
from neovpn.logging import get_logger

router = Router(name="admin")
log = get_logger(__name__)


def _is_admin(user_id: int | None, deps: BotDeps) -> bool:
    return user_id is not None and user_id in deps.settings.bot_admin_ids


@router.message(Command("admin"))
async def admin_stats(message: Message, deps: BotDeps) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, deps):
        return
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        users = await uow.session.scalar(select(func.count(UserRow.id)))
        subs_active = await uow.session.scalar(
            select(func.count(SubscriptionRow.id)).where(
                SubscriptionRow.status == "active"
            )
        )
        payments_paid = await uow.session.scalar(
            select(func.count(PaymentRow.id)).where(PaymentRow.status == "paid")
        )

    await message.answer(
        "📊 <b>NeoVPN admin</b>\n\n"
        f"👤 Пользователи: <b>{users}</b>\n"
        f"📑 Активные подписки: <b>{subs_active}</b>\n"
        f"💰 Оплачено: <b>{payments_paid}</b>"
    )


@router.message(Command("nodes"))
async def admin_nodes(message: Message, deps: BotDeps) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, deps):
        return
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        rows = (await uow.session.scalars(select(NodeRow).order_by(NodeRow.slug))).all()
    if not rows:
        await message.answer("Серверов ещё нет. Добавь через /addnode <slug> <region> <host>.")
        return
    lines = [f"• <code>{r.slug}</code> — {r.region} ({r.status}) — {r.host}" for r in rows]
    await message.answer("🖥 <b>Серверы</b>\n\n" + "\n".join(lines))


@router.message(Command("addnode"))
async def admin_addnode(message: Message, deps: BotDeps) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, deps):
        return
    args = (message.text or "").split(maxsplit=3)
    if len(args) < 4:
        await message.answer("Использование: /addnode &lt;slug&gt; &lt;region&gt; &lt;host&gt;")
        return
    _, slug, region, host = args
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        uow.session.add(NodeRow(slug=slug, region=region, host=host))
    await message.answer(f"✅ Сервер <code>{slug}</code> добавлен.")


class BroadcastStates(StatesGroup):
    waiting_for_text = State()


@router.message(Command("broadcast"))
async def broadcast_start(message: Message, state: FSMContext, deps: BotDeps) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, deps):
        return
    await state.set_state(BroadcastStates.waiting_for_text)
    await message.answer("✍️ Пришли текст рассылки одним сообщением (HTML поддерживается).")


@router.message(BroadcastStates.waiting_for_text, F.text)
async def broadcast_send(message: Message, state: FSMContext, deps: BotDeps) -> None:
    await state.clear()
    if message.from_user is None or not _is_admin(message.from_user.id, deps):
        return
    text = message.text or ""
    bot = message.bot
    assert bot is not None

    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        rows = (
            await uow.session.scalars(
                select(UserRow.tg_id).where(UserRow.is_banned.is_(False))
            )
        ).all()

    sent = 0
    failed = 0
    for tg_id in rows:
        try:
            await bot.send_message(tg_id, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # 20 msg/s — well below Telegram's 30 msg/s cap
    await message.answer(f"📣 Отправлено: {sent}, не доставлено: {failed}")
