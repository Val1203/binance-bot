import time
import csv
import datetime
from binance.client import Client

# ========================
# 🔑 CONFIGURATION
# ========================
API_KEY = "sCc2rKfhnwuAriHcQNcshZHHXsEd66OmZHIqzTmyTvuHtrtDhhkCSbgtoJzminy5"
API_SECRET = "wMiT40ClmywltlLAYVyhALssCA8zzWUZGE2tXZYw3qROXokYYUVHJt8TPEKEm17s"
PAIR = "BTCUSDC"
TRADE_BUDGET = 50        # max 50 USDC par trade
PROFIT_TARGET = 0.005    # +0.5% par trade
BUY_DISCOUNT = 0.995     # acheter 0.5% sous le prix actuel

client = Client(API_KEY, API_SECRET)

# ========================
# 📌 RÉCUPÉRER LES CONTRAINTES BINANCE
# ========================
def get_symbol_rules(symbol):
    info = client.get_symbol_info(symbol)
    min_qty = step_size = min_notional = None
    for f in info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            step_size = float(f['stepSize'])
            min_qty = float(f['minQty'])
        if f['filterType'] == 'MIN_NOTIONAL':
            min_notional = float(f['minNotional'])
    return min_qty, step_size, min_notional

MIN_QTY, STEP_SIZE, MIN_NOTIONAL = get_symbol_rules(PAIR)
print(f"📜 Contraintes Binance : MIN_QTY={MIN_QTY}, STEP_SIZE={STEP_SIZE}, MIN_NOTIONAL={MIN_NOTIONAL}")

# ========================
# 💰 LOG DES PROFITS
# ========================
def log_profit(amount):
    today = datetime.date.today()
    with open("profits_log.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([today, amount])
    print(f"💰 Profit enregistré : {amount:.2f} USDC")

# ========================
# ✅ TRADE UNIQUE (1 achat + 1 vente)
# ========================
def trade_once():
    # Solde USDC disponible
    balance = float(client.get_asset_balance(asset='USDC')['free'])
    print(f"💵 Solde dispo : {balance:.2f} USDC")

    # Vérifier si assez pour trader
    if balance < TRADE_BUDGET:
        print("⛔ Pas assez de USDC pour trader.")
        return

    # Prix actuel BTC
    current_price = float(client.get_symbol_ticker(symbol=PAIR)['price'])
    print(f"📊 Prix actuel BTC/USDC : {current_price:.2f}")

    # Montant BTC à acheter
    qty_btc = TRADE_BUDGET / current_price
    qty_btc = round(qty_btc, 5)  # arrondi valide

    # Prix achat et vente
    buy_price = round(current_price * BUY_DISCOUNT, 2)
    sell_price = round(buy_price * (1 + PROFIT_TARGET), 2)

    # ✅ Vérifier MIN_NOTIONAL uniquement si disponible
    if MIN_NOTIONAL is not None and TRADE_BUDGET < MIN_NOTIONAL:
        print(f"⛔ Montant trop bas (<{MIN_NOTIONAL} USDC). Augmente TRADE_BUDGET.")
        return

    # ✅ Placement achat
    print(f"📉 Achat limite à {buy_price} pour {qty_btc} BTC (~{TRADE_BUDGET} USDC)")
    buy_order = client.order_limit_buy(
        symbol=PAIR,
        quantity=qty_btc,
        price=str(buy_price)
    )

    # ⏳ Attente exécution achat
    while True:
        order_status = client.get_order(symbol=PAIR, orderId=buy_order['orderId'])
        if order_status['status'] == 'FILLED':
            print("✅ Achat exécuté.")
            break
        print("⏳ En attente de l'achat...")
        time.sleep(5)

    # ✅ Placement vente après achat
    print(f"📈 Vente limite placée à {sell_price}")
    sell_order = client.order_limit_sell(
        symbol=PAIR,
        quantity=qty_btc,
        price=str(sell_price)
    )

    # ⏳ Attente vente exécutée
    while True:
        sell_status = client.get_order(symbol=PAIR, orderId=sell_order['orderId'])
        if sell_status['status'] == 'FILLED':
            print("✅ Vente exécutée.")
            profit = TRADE_BUDGET * PROFIT_TARGET
            log_profit(profit)
            break
        print("⏳ En attente de la vente...")
        time.sleep(5)


    # Vente après achat
    print(f"📈 Vente limite placée à {sell_price}")
    sell_order = client.order_limit_sell(
        symbol=PAIR,
        quantity=qty_btc,
        price=str(sell_price)
    )

    # Attente vente exécutée
    print("⏳ En attente d’exécution de la vente...")
    while True:
        sell_status = client.get_order(symbol=PAIR, orderId=sell_order['orderId'])
        if sell_status['status'] == 'FILLED':
            print("✅ Vente exécutée.")
            profit = TRADE_BUDGET * PROFIT_TARGET
            log_profit(profit)
            break
        time.sleep(5)

# ========================
# 🚀 LANCEMENT
# ========================
if __name__ == "__main__":
    print("🤖 BOT SIMPLE lancé (1 seul trade à la fois)")
    trade_once()
