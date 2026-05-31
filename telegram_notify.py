import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

TELEGRAM_TOKEN   = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

SECTORS = [
    ('航太國防',     'Aerospace & Defense'),
    ('半導體',       'Semiconductors'),
    ('資訊科技服務', 'Information Technology Services'),
    ('其他金屬礦產', 'Other Metals/Minerals'),
    ('醫療專科',     'Medical Specialties'),
]

VALID_EXCHANGES = {'NYSE', 'NASDAQ', 'AMEX'}
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Origin': 'https://tw.tradingview.com',
           'Referer': 'https://tw.tradingview.com/'}

def fetch_top5(label, industry):
    try:
        r = requests.post(
            'https://scanner.tradingview.com/america/scan',
            json={
                'filter': [{'left': 'industry', 'operation': 'equal', 'right': industry}],
                'columns': ['description', 'close', 'change'],
                'sort': {'sortBy': 'change', 'sortOrder': 'desc'},
                'range': [0, 50],
            },
            headers=HEADERS,
            timeout=10,
        )
        raw = r.json().get('data') or []
        data = []
        for item in raw:
            exch, sym = item['s'].split(':', 1)
            close = item['d'][1] or 0
            if exch not in VALID_EXCHANGES or close < 1.0:
                continue
            data.append({
                'symbol': sym,
                'close': close,
                'changePct': round(item['d'][2] or 0, 2),
            })
        top5 = sorted(data, key=lambda x: x['changePct'], reverse=True)[:5]
        return label, top5
    except Exception:
        return label, []

def main():
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(lambda t: fetch_top5(*t), SECTORS))

    now_str = datetime.utcnow().strftime('%m/%d %H:%M') + ' UTC'
    lines = [f'美股開盤 — 各類股漲幅前 5 名  {now_str}', '']
    for label, top5 in results:
        lines.append(f'[ {label} ]')
        for i, s in enumerate(top5, 1):
            sign = '+' if s['changePct'] >= 0 else ''
            lines.append(f"{i}. {s['symbol']}  {sign}{s['changePct']:.2f}%  ${s['close']:.2f}")
        lines.append('')

    requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
        json={'chat_id': TELEGRAM_CHAT_ID, 'text': '\n'.join(lines)},
        timeout=10,
    )
    print('Telegram sent.')

if __name__ == '__main__':
    main()
