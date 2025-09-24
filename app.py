from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

throw_count = 0
last_metrics = {
    "flight_time": 0.0,
    "range_cm": 0.0,
    "vx": 0.0,
    "vy": 0.0,
    "v": 0.0,
    "angle_deg": 0.0,
    "score": 0
}

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Medicine Ball Throw Metrics</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; color: #333; }
        .container { width: 600px; margin: auto; padding: 20px; background: white; border-radius: 12px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; }
        p { font-size: 18px; }
        span { font-weight: bold; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Medicine Ball Throw Metrics</h1>
        <p>Throw Count: <span id="count">{{ throw_count }}</span></p>
        <p>Flight Time: <span id="flight_time">{{ '{:.2f}'.format(last_metrics['flight_time']) }}</span> s</p>
        <p>Range: <span id="range">{{ '{:.2f}'.format(last_metrics['range_cm']) }}</span> cm</p>
        <p>Vx: <span id="vx">{{ '{:.2f}'.format(last_metrics['vx']) }}</span> cm/s</p>
        <p>Vy: <span id="vy">{{ '{:.2f}'.format(last_metrics['vy']) }}</span> cm/s</p>
        <p>Speed: <span id="v">{{ '{:.2f}'.format(last_metrics['v']) }}</span> cm/s</p>
        <p>Release Angle: <span id="angle">{{ '{:.2f}'.format(last_metrics['angle_deg']) }}</span> °</p>
        <p>Score: <span id="score">{{ last_metrics['score'] }}</span></p>
    </div>
    <script>
        setInterval(function() {
            fetch('/status').then(r => r.json()).then(data => {
                document.getElementById("count").textContent = data.throw_count;
                document.getElementById("flight_time").textContent = Number(data.last_metrics.flight_time).toFixed(2);
                document.getElementById("range").textContent = Number(data.last_metrics.range_cm).toFixed(2);
                document.getElementById("vx").textContent = Number(data.last_metrics.vx).toFixed(2);
                document.getElementById("vy").textContent = Number(data.last_metrics.vy).toFixed(2);
                document.getElementById("v").textContent = Number(data.last_metrics.v).toFixed(2);
                document.getElementById("angle").textContent = Number(data.last_metrics.angle_deg).toFixed(2);
                document.getElementById("score").textContent = data.last_metrics.score;
            });
        }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, throw_count=throw_count, last_metrics=last_metrics)

@app.route('/status')
def status():
    return jsonify(throw_count=throw_count, last_metrics=last_metrics)

@app.route('/increment', methods=['POST'])
def increment():
    global throw_count, last_metrics
    data = request.get_json()
    throw_count += 1
    if data:
        for key in last_metrics:
            if key in data:
                last_metrics[key] = data[key]
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)
