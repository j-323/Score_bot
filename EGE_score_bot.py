from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import pymongo

class EGE_Score_Bot:
    def __init__(self, token, db_url):
        self.token = token
        self.db_url = db_url
        self.application = Application.builder().token(self.token).build()

        self.client = pymongo.MongoClient(self.db_url)
        self.db = self.client["ege_scores"]
        self.students_collection = self.get_or_create_collection("students")

        self.button_commands = {
            "Регистрация": self.register,
            "Ввод баллов": self.enter_score,
            "Просмотр баллов": self.view_scores,
            "Обновление баллов": self.update_scores,
            "Удалить аккаунт": self.delete_account,
            "Помощь": self.help
        }

        self.add_handlers()

    def get_or_create_collection(self, collection_name):
        if collection_name not in self.db.list_collection_names():
            return self.db.create_collection(collection_name)
        return self.db[collection_name]

    def add_handlers(self):
        handlers = [
            ("start", self.start),
            ("register", self.register),
            ("enter_scores", self.enter_score),
            ("view_scores", self.view_scores),
            ("delete_account", self.delete_account),
            ("update_scores", self.update_scores),
            ("help", self.help)
        ]

        for command, handler in handlers:
            self.application.add_handler(CommandHandler(command, handler))

        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message))
        self.application.add_handler(CallbackQueryHandler(self.button))

    async def start(self, update, context):
        keyboard = [
            ["Регистрация", "Ввод баллов"],
            ["Просмотр баллов", "Обновление баллов"],
            ["Удалить аккаунт", "Помощь"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "Добрый день, я - бот для  для сбора баллов ЕГЭ. Выберите команду из меню ниже или используйте команды напрямую.",
            reply_markup=reply_markup
        )

    async def register(self, update, context):
        await update.message.reply_text("Введите ваше имя и фамилию через пробел. Пример: Иван Иванов")
        context.user_data["registering"] = True

    async def enter_score(self, update, context):
        await update.message.reply_text("Введите ваши баллы ЕГЭ в формате: предмет1 балл1, предмет2 балл2, ... Пример: Информатика 60, Математика 50")
        context.user_data["entering_scores"] = True

    async def text_message(self, update, context):
        text = update.message.text.strip()
        
        if text in self.button_commands:
            await self.button_commands[text](update, context)
            return
        
        if context.user_data.get("registering"):
            name = update.message.text.strip()
            self.students_collection.insert_one({"name": name, "scores": {}})
            await update.message.reply_text(f"Регистрация завершена, {name}!")
            context.user_data["registering"] = False
        elif context.user_data.get("entering_scores"):
            scores_text = update.message.text.strip()
            try:
                scores = dict(item.split() for item in scores_text.split(","))
                scores = {subject: int(score) for subject, score in scores.items()}
                name = update.message.chat.username
                self.students_collection.update_one({"name": name}, {"$set": {"scores": scores}}, upsert=True)
                await update.message.reply_text("Баллы сохранены!")
            except ValueError:
                await update.message.reply_text("Ошибка. Введите баллы в правильном формате: предмет1 балл1, предмет2 балл2, ... Пример: Информатика 60, Математика 50")
            context.user_data["entering_scores"] = False
        elif context.user_data.get("updating_scores"):
            scores_text = update.message.text.strip()
            try:
                scores = dict(item.split() for item in scores_text.split(","))
                scores = {subject: int(score) for subject, score in scores.items()}
                name = update.message.chat.username
                self.students_collection.update_one({"name": name}, {"$set": {"scores": scores}})
                await update.message.reply_text("Баллы обновлены.")
            except ValueError:
                await update.message.reply_text("Ошибка. Введите баллы в правильном формате: предмет1 балл1, предмет2 балл2, ... Пример: Информатика 60, Математика 50")
            context.user_data["updating_scores"] = False
        else:
            await update.message.reply_text(
                "Я не поддерживаю такой тип сообщений. "
                "Для получения списка введите комманду - /help."
            )

    async def view_scores(self, update, context):
        name = update.message.chat.username
        student = self.students_collection.find_one({"name": name})
        if student and student.get("scores"):
            scores = student["scores"]
            message = "Ваши баллы ЕГЭ:\n"
            for subject, score in scores.items():
                message += f"{subject}: {score}\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Баллы не найдены или вы не зарегистрированы.")

    async def delete_account(self, update, context):
        name = update.message.chat.username
        self.students_collection.delete_one({"name": name})
        await update.message.reply_text("Ваш аккаунт и данные удалены.")

    async def update_scores(self, update, context):
        await update.message.reply_text("Введите новые баллы ЕГЭ в формате: редмет1 балл1, предмет2 балл2, ... Пример: Информатика 60, Математика 50")
        context.user_data["updating_scores"] = True

    async def help(self, update, context):
        help_message = (
            "Доступные команды:\n"
            "/start - Начать работу с ботом\n"
            "/register - Регистрация пользователя\n"
            "/enter_scores - Ввести баллы ЕГЭ\n"
            "/view_scores - Просмотр баллов ЕГЭ\n"
            "/delete_account - Удалить аккаунт и данные\n"
            "/update_scores - Обновить баллы ЕГЭ\n"
            "/help - Показать это сообщение"
        )
        await update.message.reply_text(help_message)

    async def button(self, update, context):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=f"Вы выбрали: {query.data}")

    def run(self):
        self.application.run_polling(1.0)

if __name__ == "__main__":
    bot = EGE_Score_Bot("TOKEN", "MONGODB_URL")
    bot.run()