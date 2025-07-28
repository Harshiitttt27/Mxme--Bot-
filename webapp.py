from flask import Flask, render_template, request
from app.backtester import run_backtest
from app.data_manager import load_data
from app.config import Config

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        symbols = request.form['symbols'].split(',')
        start = request.form['start_date']
        end = request.form['end_date']
        api_key = request.form['api_key']
        balance = float(request.form['starting_balance'])

        config = Config()
        config.POLYGON_API_KEY = api_key
        config.STARTING_BALANCE = balance

        data = load_data(symbols, start, end, api_key)
        results = run_backtest(data, config)

    return render_template('index.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)