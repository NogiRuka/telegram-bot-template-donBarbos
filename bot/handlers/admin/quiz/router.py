from aiogram import Router
from bot.filters.admin import AdminFilter

router = Router(name="admin_quiz")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())
