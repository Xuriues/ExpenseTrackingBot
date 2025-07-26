from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import pytz
from datetime import datetime
import sqlite3
from typing import Optional, Tuple, List, Any
from collections import defaultdict

subcategory_emojis = {
    "fnb": "🍽️",
    "shopping": "🛍️",
    "transit": "🚌",
    "entertainment": "🎮",
    "lifestyle": "💅",
    "misc": "🔧",
    "gifts": "🎁",
    "insurance": "🛡️",
    "investment": "📈",
    "bills": "📄",
    "loans": "💰",
    "savings": "🏦",
    "others": "❓"
}


def get_current_month_key():
  sg_tz = pytz.timezone("Asia/Singapore")
  now = datetime.now(sg_tz)
  return now.strftime("%Y-%m")


def checkIfUserAllowed(userId: int, allowedUsers) -> bool:
  return userId in allowedUsers


def get_main_menu_keyboard():
  """Returns the main menu keyboard markup"""
  keyboard = [
      [
          InlineKeyboardButton("😫 View Your Spending",
                               callback_data="viewCommand")
      ],
      [InlineKeyboardButton("🆕 Add a new spending!", callback_data='3')],
      [InlineKeyboardButton("🆕 Update Budget!", callback_data='updateBudget')],
      [InlineKeyboardButton("📊 Help", callback_data='5')],
  ]
  return InlineKeyboardMarkup(keyboard)


def getUserIdFromDB(user_id: int) -> Optional[Tuple]:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?",
                   (str(user_id), ))
    return cursor.fetchone()


def viewSpendingFunc(userInfo: Any, category) -> str:
  month_key = get_current_month_key()
  expense_functions = {
      "spending": returnSpendingList,
      "insurance": returnInsuranceList,
      "savings": returnSavingsList
  }

  expenses = expense_functions.get(category,
                                   returnSavingsList)(userInfo, category,
                                                      month_key)

  if not expenses:
    return f"💰 No expenses found for {month_key}"

  total = 0.0
  message_parts = [f"💰 Your expenses for {month_key} under {category}:\n\n"]

  # Group expenses by subcategory
  expenses_by_subcat = defaultdict(list)
  for expense in expenses:
    amount, description, _, _, subcategory = expense  # adjust indices as needed
    subcat_key = subcategory.lower() if subcategory else "others"
    expenses_by_subcat[subcat_key].append((amount, description))

  # Sort subcategories alphabetically and print
  for subcat in sorted(expenses_by_subcat.keys()):
    emoji = subcategory_emojis.get(subcat, "❓")
    message_parts.append(f"{emoji} {subcat.capitalize()}\n")
    for i, (amount, description) in enumerate(expenses_by_subcat[subcat], 1):
      message_parts.append(f"{i}: ${amount:.2f} ➣ {description}\n")
      total += amount
    message_parts.append("\n")

  result_text = {
      "spending": "Spent",
      "insurance": "Spent",
      "savings": "Saved"
  }.get(category, "Amount")
  message_parts.append(f"💸 Total {result_text}: ${total:.2f}")

  if category != "savings":
    balance_func = getSpendingBudgetBalance if category == "spending" else getInsuranceBudgetBalance
    balance = balance_func(userInfo, category, month_key, total)
    message_parts.append(f"\n💸 Balance: ${balance:.2f}")

  return "".join(message_parts)


def returnSpendingList(userInfo, category, month_key) -> List[Tuple]:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT amount, description, category, created_at, subcategory
        FROM expenses
        WHERE user_id = ? AND LOWER(category) = ? AND month_key = ?
        ORDER BY subcategory ASC, created_at DESC
        ''', (str(userInfo[0]), category, month_key))
    return cursor.fetchall()


def returnInsuranceList(userInfo, category, month_key) -> List[Tuple]:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
      SELECT amount, description, category, created_at, subcategory
      FROM expenses
      WHERE user_id = ? AND (LOWER(category) = ? OR LOWER(category) = ?)
      AND month_key = ?
      ORDER BY created_at DESC
    ''', (str(userInfo[0]), category.lower(), "savings", month_key))
    return cursor.fetchall()


def returnSavingsList(userInfo, category, month_key) -> List[Tuple]:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT amount, description, category, created_at, subcategory
        FROM expenses
        WHERE user_id = ? AND LOWER(category) = ? AND month_key = ?
        ORDER BY created_at DESC
        ''', (str(userInfo[0]), category, month_key))
    return cursor.fetchall()


def getSpendingBudgetBalance(userInfo, category, month_key,
                             spentAmnt) -> float:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT budget_amount
        FROM budgets
        WHERE user_id = ? AND LOWER(category) = ? AND month_key = ?
        ''', (str(userInfo[0]), category, month_key))
    res = float(cursor.fetchone()[0])
    return res - spentAmnt


def getBalDiffForInsurance(userInfo) -> float:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
          SELECT amount, description, category, created_at
          FROM expenses
          WHERE user_id = ? AND LOWER(category) = ?
          ORDER BY created_at DESC
          ''', (str(userInfo[0]), "savings"))
    expenses = cursor.fetchall()
    total = sum(expense[0] for expense in expenses)
    return total


def getInsuranceBudgetBalance(userInfo, category, month_key,
                              spentAmnt) -> float:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT budget_amount
        FROM budgets
        WHERE user_id = ? AND LOWER(category) = ? AND month_key = ?
        ''', (str(userInfo[0]), category, month_key))
    res = float(cursor.fetchone()[0])
    res += getBillsBudget(userInfo, month_key) + getInvestmentBudget(
        userInfo, month_key) + getSavingsBudget(userInfo, month_key)
    return res - spentAmnt


def getBillsBudget(userInfo, month_key) -> float:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT budget_amount
        FROM budgets
        WHERE user_id = ? AND LOWER(category) = ? AND month_key = ?
        ''', (str(userInfo[0]), "bills", month_key))
    res = float(cursor.fetchone()[0])
    return res if res else 0.0


def getInvestmentBudget(userInfo, month_key) -> float:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT budget_amount
        FROM budgets
        WHERE user_id = ? AND LOWER(category) = ? AND month_key = ?
        ''', (str(userInfo[0]), "investment", month_key))
    res = float(cursor.fetchone()[0])
    return res if res else 0.0


def getSavingsBudget(userInfo, month_key) -> float:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT budget_amount
        FROM budgets
        WHERE user_id = ? AND LOWER(category) = ? AND month_key = ?
        ''', (str(userInfo[0]), "savings", month_key))
    res = float(cursor.fetchone()[0])
    return res if res else 0.0


#Handles adding/updating of DB
def handleAddItemFunc(userInfo: Any, amount: float, category: str,
                      description: str, subcategory: str) -> str:
  month_key = get_current_month_key()
  try:
    with sqlite3.connect('expense.db') as conn:
      cursor = conn.cursor()
      cursor.execute(
          '''
      INSERT INTO expenses (user_id, month_key, category, amount, description, subcategory)
      VALUES (?, ?, ?, ?, ?, ?)
      ''', (str(userInfo[0]), month_key, category, amount, description,
            subcategory))
      conn.commit()
      return "✅ Successfully added!"
  except Exception as e:
    print("DB Error:", e)
    return "❌ Failed to add! Try again."


def checkIfBudgetExists(userInfo, category, month_key) -> bool:
  with sqlite3.connect('expense.db') as conn:
    cursor = conn.cursor()
    cursor.execute(
        '''
          SELECT EXISTS (
            SELECT 1
            FROM budgets
            WHERE user_id = ? AND LOWER(category) = ? AND month_key = ?
          )
        ''', (str(userInfo[0]), category, month_key))
    res = cursor.fetchone()
    if res is not None:
      return True
    else:
      return False


def insertBudgetFunc(userInfo, category, amount, month_key) -> str:
  try:
    with sqlite3.connect('expense.db') as conn:
      cursor = conn.cursor()
      cursor.execute(
          '''
            INSERT INTO budgets (user_id, month_key, category, budget_amount)
            VALUES (?, ?, ?, ?)
            WHERE user_id = ? AND month_key = ? AND category = ?
            ''', (str(userInfo[0]), month_key, category, amount))
      conn.commit()
    return "✅ Successful! As you have no record of this budget, it has been added in!"
  except Exception as e:
    print("DB Error:", e)
    return "❌ Failed to add! Try again."


def updateBudgetFunc(userInfo, category, amount, month_key) -> str:
  try:
    with sqlite3.connect('expense.db') as conn:
      cursor = conn.cursor()
      cursor.execute(
          '''
            UPDATE budgets
            SET budget_amount = ?
            WHERE user_id = ? AND month_key = ? AND category = ?
            ''', (amount, str(userInfo[0]), month_key, category))
      conn.commit()
    return "✅ Successful! Your budget has been updated!"
  except Exception as e:
    print("DB Error:", e)
    return "❌ Failed to add! Try again."
