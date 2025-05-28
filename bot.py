import requests
import pandas as pd
import pandas_ta as ta
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = "8176067910:AAGayLlczUDjBVZ4hag7TyduWv3RcCf3qaU"

def fetch_vndirect_data(symbol):
    url = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?q=code:{symbol}&size=100&sort=date,desc"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    if "data" not in data or len(data["data"]) == 0:
        return None
    df = pd.DataFrame(data["data"])
    # Convert to proper types
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['close'] = pd.to_numeric(df['close'])
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['volume'] = pd.to_numeric(df['average'])

    return df

def analyze_technical(df):
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)
    df.ta.bbands(length=20, append=True)
    df.ta.sma(length=20, append=True)
    df.ta.sma(length=50, append=True)
    df.ta.stoch(append=True)
    df.ta.adx(append=True)
    # Add more indicators as you want here

    latest = df.iloc[-1]
    report = f"Phân tích kỹ thuật ngày {latest['date'].date()}:\n"
    report += f"Giá đóng cửa: {latest['close']}\n"
    report += f"RSI(14): {latest['RSI_14']:.2f}\n"
    report += f"MACD: {latest['MACD_12_26_9']:.4f}\n"
    report += f"Bollinger Bands (Upper, Middle, Lower): {latest['BBU_20_2.0']:.2f}, {latest['BBM_20_2.0']:.2f}, {latest['BBL_20_2.0']:.2f}\n"
    report += f"SMA(20): {latest['SMA_20']:.2f}\n"
    report += f"SMA(50): {latest['SMA_50']:.2f}\n"
    report += f"Stochastic K: {latest['STOCHk_14_3_3']:.2f}\n"
    report += f"ADX(14): {latest['ADX_14']:.2f}\n"

    # Cảnh báo mẫu
    alerts = []
    if latest['RSI_14'] > 70:
        alerts.append("Cảnh báo: Quá mua (RSI > 70).")
    if latest['RSI_14'] < 30:
        alerts.append("Cảnh báo: Quá bán (RSI < 30).")
    if latest['close'] > latest['BBU_20_2.0']:
        alerts.append("Cảnh báo: Giá vượt trên dải Bollinger trên.")
    if latest['close'] < latest['BBL_20_2.0']:
        alerts.append("Cảnh báo: Giá dưới dải Bollinger dưới.")

    if alerts:
        report += "\n".join(alerts)
    else:
        report += "Không có cảnh báo đặc biệt."

    return report

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Chào bạn <b>{user.first_name}</b>!\n"
        "Gửi mã cổ phiếu để nhận phân tích kỹ thuật từ VNDIRECT (Ví dụ: VNM, MZG,...).",
        reply_markup=ForceReply(selective=True),
    )

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    symbol = update.message.text.strip().upper()
    await update.message.reply_text(f"Đang tải dữ liệu và phân tích {symbol}...")
    df = fetch_vndirect_data(symbol)
    if df is None:
        await update.message.reply_text("Không tìm thấy dữ liệu hoặc lỗi kết nối.")
        return
    report = analyze_technical(df)
    await update.message.reply_text(report)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))
    app.run_polling()

if __name__ == "__main__":
    main()
