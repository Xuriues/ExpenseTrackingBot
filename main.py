#Bot token should be stored in environment variables for security
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
)
from typing import Final
import pytz
import sqlite3
import helperFunc
import db

db.init_db()

#Fixed Variables
token: Final = 'fill with your bot token'
username: Final = 'bot username without @'
allowedUsers = [INSERT YOUR OWN USERS THAT YOU ALLOW TO USE THIS APP]
categoryAllowed = [
    "spending", "insurance", "savings", "bills", "investment", "loan"
]
CATEGORY_INPUT = 1
budgetCategoryAllowed = [
    "spending", "insurance", "savings", "bills", "investment"
]
subSpendingCategoryAllowed = [
    "fnb",
    "shopping",
    "transit",
    "entertainment",
    "lifestyle",
    "misc",
    "gifts",
    "others",
]


#Menu text and keyboard
async def show_main_menu(update: Update,
                         context: CallbackContext,
                         text: str = None):
  reply_markup = helperFunc.get_main_menu_keyboard()
  if text is None:
    text = "🏠 Main Menu - Choose an option:"
  if update.callback_query:
    await update.callback_query.edit_message_text(text,
                                                  reply_markup=reply_markup)
  else:
    await update.message.reply_text(text, reply_markup=reply_markup)


#Basic Commands
async def start_cmd(update: Update, context: CallbackContext):
  user_id = update.effective_user.id
  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    await update.message.reply_text("🚫 You are not authorized to use this bot."
                                    )
    return
  keyboard = [
      [InlineKeyboardButton("📝Register", callback_data='1')],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  await update.message.reply_text(
      "👋 Hello! Welcome to Shaun's Expense Tracker Bot.\n"
      "\n"
      "If you are a new user please click on register below\n"
      "Otherwise, use /help to see the available features.\n",
      reply_markup=reply_markup)


#Help Command func
async def help_cmd(update: Update, context: CallbackContext):
  print("in commmand")
  help_text = ""
  user_id = update.effective_user.id
  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    await update.message.reply_text("🚫 You are not authorized to use this bot."
                                    )
    return
  print("after check if user allowed")
  help_text = ("📚 **Help Menu**\n\n"
               "Welcoem to the Help Menu!\n"
               "Please click on the menus below to see what you can do!\n"
               "🏠 Main Menu - Choose an option:")
  await show_main_menu(update, context, help_text)


#Handle button pressing in main menu
async def button_callback(update: Update, context: CallbackContext):
  query = update.callback_query
  user_id = update.effective_user.id

  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    await query.answer("🚫 You are not authorized to use this bot.")
    return

  await query.answer()  # Acknowledge the callback

  if query.data == '1':  # Register button pressed
    await register_user(update, context)
  elif query.data == '3':  # Add new spending
    await add_item(update, context)
  elif query.data == '5':  # Help
    await help_cmd(update, context)
  elif query.data == 'updateBudget':
    await updateBudget(update, context)
  elif query.data == 'viewCommand':
    await viewListHelp(update, context)


#Register new user
async def register_user(update: Update, context: CallbackContext):
  query = update.callback_query
  user_id = update.effective_user.id
  user_name = update.effective_user.first_name or "Unknown"
  try:
    conn = sqlite3.connect('expense.db')
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?",
                   (str(user_id), ))
    existing_user = cursor.fetchone()

    if existing_user:
      await show_main_menu(
          update, context,
          "✅ You are already registered!\n\n🏠 Main Menu - Choose an option:")
    else:
      # Insert new user
      cursor.execute("INSERT INTO users (telegram_id, name) VALUES (?, ?)",
                     (str(user_id), user_name))
      conn.commit()
      await show_main_menu(
          update, context,
          "✅ Registration successful!\n\n Do not forget to update your budget by clicking the button below! \n\n🏠 Main Menu - Choose an option:"
      )
    conn.close()

  except Exception as e:
    print(f"❌ Registration error: {e}")
    await query.edit_message_text("❌ Registration failed. Please try again.")


#View certain categories or entries
async def viewListHelp(update: Update, context: CallbackContext):
  user_id = update.effective_user.id
  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    if update.callback_query:
      await update.callback_query.answer(
          "🚫 You are not authorized to use this bot.")
    else:
      await update.message.reply_text(
          "🚫 You are not authorized to use this bot.")
    return

  response_text = (
      "🆕 How to view your expense?\n\n"
      "Type /view\n"
      "It will then prompt you to enter what category you'd like to view!\n\n\n"
  )
  if update.callback_query:
    await update.callback_query.message.reply_text(
        response_text, reply_markup=helperFunc.get_main_menu_keyboard())
  else:
    await update.message.reply_text(
        response_text, reply_markup=helperFunc.get_main_menu_keyboard())


async def viewList(update: Update, context: CallbackContext):
  user_id = update.effective_user.id
  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    if update.callback_query:
      await update.callback_query.answer(
          "🚫 You are not authorized to use this bot.")
    else:
      await update.message.reply_text(
          "🚫 You are not authorized to use this bot.")
    return ConversationHandler.END

  response_text = (
      "🔍 Please type the category you want to view.\n\n"
      "Spending | Insurance (This contains bills, investments etc,.) | Savings"
  )
  if update.callback_query:
    await update.callback_query.message.reply_text(response_text)
  elif update.message:
    await update.message.reply_text(response_text)

  return CATEGORY_INPUT


async def category_chosen(update: Update, context: CallbackContext) -> int:
  category = update.message.text.lower()
  user_id = update.effective_user.id
  if category not in categoryAllowed:
    await update.message.reply_text(
        "❌ Invalid category. Please choose from: spending, insurance, savings."
    )
    return CATEGORY_INPUT
  try:
    userInfo = helperFunc.getUserIdFromDB(user_id)
    if not userInfo:
      await update.message.reply_text(
          "❌ User not found. Please register first.")
      return ConversationHandler.END
    responseText = helperFunc.viewSpendingFunc(userInfo, category)
    reply_markup = helperFunc.get_main_menu_keyboard()
    await update.message.reply_text(responseText, reply_markup=reply_markup)
    return ConversationHandler.END
  except Exception as e:
    print(f"\u274C Database error: {e}")
    await update.message.reply_text("❌ Failed to connect to database.")
    return ConversationHandler.END


async def cancel_view(update: Update, context: CallbackContext) -> int:
  await update.message.reply_text("❌ Cancelled view operation.")
  return ConversationHandler.END


#Entering entries
async def add_item(update: Update, context: CallbackContext):
  user_id = update.effective_user.id

  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    if update.callback_query:
      await update.callback_query.answer(
          "🚫 You are not authorized to use this bot.")
    else:
      await update.message.reply_text(
          "🚫 You are not authorized to use this bot.")
    return

  response_text = (
      "🆕 Add New Expense\n\n"
      "Type /add followed by the amount, category, subcategory, and description.\n"
      "Please note, do only use the subcategory if you are adding a spending.\n\n\n"
      "*Do note that they are not case sensitive so don't worry! ☺️*\n"
      "Syntax: /add {price} {Main Category} {subcategory} {Description} \n\n"
      "Main Category Consist of ➡️ Spending | Insurance | Savings | Bill | Investment | Loan \n"
      "SubCategory Consist of ➡️ FnB | Shopping | Transit | Entertainment | Lifestyle | Gifts | Misc | Others \n\n"
      "You can also use /add -10.50 if you've received money.\n")
  if update.callback_query:
    await update.callback_query.message.reply_text(
        response_text, reply_markup=helperFunc.get_main_menu_keyboard())
  else:
    await update.message.reply_text(
        response_text, reply_markup=helperFunc.get_main_menu_keyboard())


#Handle add in parameters
async def handle_add_item(update: Update, context: CallbackContext):
  user_id = update.effective_user.id
  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    await update.message.reply_text("🚫 You are not authorized to use this bot."
                                    )
    return
  try:
    args = context.args
    if len(args) < 4:
      raise ValueError(
          "Invalid format. Use: /add {Price} {Spending|Insurance|Savings} {Description}"
      )
    amount = float(args[0])
    category = args[1]
    subcategory = args[2]
    description = " ".join(args[3:])
    if category.lower() not in categoryAllowed:
      await update.message.reply_text(
          "❌ Invalid category. Please choose from: spending, insurance, savings."
      )
      return
    elif subcategory.lower() not in subSpendingCategoryAllowed:
      await update.message.reply_text(
          "❌ Invalid subcategory. Please choose from: FnB | Shopping | Transit | Entertainment | Lifestyle | Gifts | Misc | Others"
      )
      return
    if category.lower() != "spending":
      subcategory = category
    else:
      subcategory = "None"
    responseText = helperFunc.handleAddItemFunc(
        helperFunc.getUserIdFromDB(user_id), amount, category, description,
        subcategory)
    reply_markup = helperFunc.get_main_menu_keyboard()
    if update.callback_query:
      await update.callback_query.edit_message_text(responseText,
                                                    reply_markup=reply_markup)
    else:
      await update.message.reply_text(responseText, reply_markup=reply_markup)
  except ValueError as ve:
    await update.message.reply_text(f"❌ Error: {str(ve)}\n\n"
                                    "Use: /add 10.50 food lunch at McDonalds")
  except Exception as e:
    await update.message.reply_text("❌ Unexpected error occurred.")
    print(e)


async def updateBudget(update: Update, context: CallbackContext):
  user_id = update.effective_user.id
  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    await update.message.reply_text("🚫 You are not authorized to use this bot."
                                    )
    return
  response_text = (
      "🆕 Update Budget\n\n"
      "Type /updatebudget followed by the category, amount, and month.\n"
      "Syntax: /updatebudget {Spending|Insurance|Savings|Bills|Investment} {Amount} {YYYY-MM}\n"
  )
  if update.callback_query:
    await update.callback_query.message.reply_text(
        response_text, reply_markup=helperFunc.get_main_menu_keyboard())
  else:
    await update.message.reply_text(
        response_text, reply_markup=helperFunc.get_main_menu_keyboard())


async def handle_update_budget(update: Update, context: CallbackContext):
  user_id = update.effective_user.id
  if not helperFunc.checkIfUserAllowed(user_id, allowedUsers):
    await update.message.reply_text("🚫 You are not authorized to use this bot."
                                    )
    return
  try:
    args = context.args
    if len(args) < 3:
      raise ValueError(
          "Invalid format. Use: /update {Spending|Insurance|Savings|Bills|Investment} {Amount} {YYYY-MM}"
      )
    budgetCategory = args[0]
    if budgetCategory.lower() not in budgetCategoryAllowed:
      await update.message.reply_text(
          "❌ Invalid category. Please choose from: spending, insurance, savings, bills, investment."
      )
      return
    else:
      amount = float(args[1])
      month_key = args[2]
      if (helperFunc.checkIfBudgetExists(helperFunc.getUserIdFromDB(user_id),
                                         budgetCategory, month_key)):
        responseText = helperFunc.updateBudgetFunc(
            helperFunc.getUserIdFromDB(user_id), budgetCategory, amount,
            month_key)
      else:
        responseText = helperFunc.insertBudgetFunc(
            helperFunc.getUserIdFromDB(user_id), budgetCategory, amount,
            month_key)
      reply_markup = helperFunc.get_main_menu_keyboard()
      if update.callback_query:
        await update.callback_query.edit_message_text(
            responseText, reply_markup=reply_markup)
      else:
        await update.message.reply_text(responseText,
                                        reply_markup=reply_markup)
  except ValueError as ve:
    await update.message.reply_text(f"❌ Error: {str(ve)}\n\n")
  except Exception as e:
    await update.message.reply_text("❌ Unexpected error occurred.")
    print(e)


if __name__ == '__main__':
  view_conversation = ConversationHandler(
      entry_points=[
          CommandHandler("view", viewList),
          CallbackQueryHandler(viewList, pattern="^view$")
      ],
      states={
          CATEGORY_INPUT:
          [MessageHandler(filters.TEXT & ~filters.COMMAND, category_chosen)]
      },
      fallbacks=[CommandHandler("cancel", cancel_view)],
      per_chat=True)

  singapore_tz = pytz.timezone('Asia/Singapore')
  app = ApplicationBuilder().token(token).build()

  app.add_handler(view_conversation)
  app.add_handler(CommandHandler("start", start_cmd))
  app.add_handler(CommandHandler("help", help_cmd))
  app.add_handler(CommandHandler("viewhelp", viewListHelp))
  app.add_handler(CommandHandler("addentry", handle_add_item))
  app.add_handler(CommandHandler("addButton", add_item))
  app.add_handler(CommandHandler("add", add_item))

  app.add_handler(CommandHandler("updatebudget", handle_update_budget))
  app.add_handler(CommandHandler("updateButton", updateBudget))
  app.add_handler(CommandHandler("update", updateBudget))

  app.add_handler(CallbackQueryHandler(button_callback))

  print("Bot is running...")
  app.run_polling()
