import os
import requests
import pandas as pd
import pandas_ta as ta
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# BOT_TOKEN tốt nhất nên đặt trong biến môi trường (khi deploy)
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8176067910:AAGayLlczUDjBVZ4hag7TyduWv3RcCf3qaU"

def fetch_vndirect_data(symbol):
    url = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?q=code:{symbol}&size=100&sort=date,desc"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    if "data" not in data or len(data["data"]) == 0:
        return None
    df = pd.DataFrame(data["data"])
    # Chuyển kiểu dữ liệu
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['open'] = pd.to_numeric(df['open'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    # volume đúng chuẩn, lấy volume chứ không phải average
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df = df.dropna(subset=['close'])  # loại bỏ dòng không có giá đóng cửa

    return df

def analyze_technical(df):
    try:
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.bbands(length=20, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.stoch(append=True)
        df.ta.adx(append=True)

        latest = df.iloc[-1]

        # Kiểm tra nếu các cột tồn tại và không null
        def get_val(key):
            return latest[key] if key in latest and pd.notnull(latest[key]) else None

        rsi = get_val('RSI_14')
        macd = get_val('MACD_12_26_9')
        bbu = get_val('BBU_20_2.0')
        bbm = get_val('BBM_20_2.0')
        bbl = get_val('BBL_20_2.0')
        sma20 = get_val('SMA_20')
        sma50 = get_val('SMA_50')
        stochk = get_val('STOCHk_14_3_3')
        adx = get_val('ADX_14')

        report = f"📅 Phân tích kỹ thuật ngày {latest['date'].date()}:\n"
        report += f"Giá đóng cửa: {latest['close']}\n"
        if rsi is not None:
            report += f"RSI(14): {rsi:.2f}\n"
        if macd is not None:
            report += f"MACD: {macd:.4f}\n"
        if bbu is not None and bbm is not None and bbl is not None:
            report += f"Bollinger Bands (Upper, Middle, Lower): {bbu:.2f}, {bbm:.2f}, {bbl:.2f}\n"
        if sma20 is not None:
            report += f"SMA(20): {sma20:.2f}\n"
        if sma50 is not None:
            report += f"SMA(50): {sma50:.2f}\n"
        if stochk is not None:
            report += f"Stochastic K: {stochk:.2f}\n"
        if adx is not None:
            report += f"ADX(14): {adx:.2f}\n"

        alerts = []
        if rsi is not None:
            if rsi > 70:
                alerts.append("⚠️ Cảnh báo: Quá mua (RSI > 70).")
            if rsi < 30:
                alerts.append("⚠️ Cảnh báo: Quá bán (RSI < 30).")

        if bbu is not None and latest['close'] > bbu:
            alerts.append("⚠️ Cảnh báo: Giá vượt trên dải Bollinger trên.")
        if bbl is not None and latest['close'] < bbl:
            alerts.append("⚠️ Cảnh báo: Giá dưới dải Bollinger dưới.")

        if alerts:
            report += "\n\n" + "\n".join(alerts)
        else:
            report += "\n\n✅ Không có cảnh báo đặc biệt."

        return report

    except Exception as e:
        return f"Lỗi khi phân tích kỹ thuật: {str(e)}"

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
    if df is None or df.empty:
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
